import os
import re
import subprocess
import whisper
import wave
import webrtcvad
from praatio import textgrid

# ------------------------------
# Paso 1: Transcripción (HTML)
# ------------------------------
def transcribir_audio_a_html(audio_path, output_path):
    model = whisper.load_model("base")  # Puedes usar "tiny" si necesitas velocidad
    result = model.transcribe(audio_path, language="es")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("<html><body><p>")
        f.write(result["text"])
        f.write("</p></body></html>")

    print(f"[✓] Transcripción guardada en: {output_path}")

# ------------------------------
# Paso 2: IPUs con WebRTC VAD
# ------------------------------
def detectar_ipus(audio_path, output_textgrid):
    vad = webrtcvad.Vad(2)

    with wave.open(audio_path, 'rb') as wf:
        sample_rate = wf.getframerate()
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        assert sample_rate == 16000, "El audio debe estar a 16kHz"
        assert channels == 1, "El audio debe ser mono"

        frame_duration = 30  # ms
        frame_bytes = int(sample_rate * frame_duration / 1000) * width
        frames = []
        while True:
            frame = wf.readframes(frame_bytes // width)
            if len(frame) < frame_bytes:
                break
            frames.append(frame)

        timestamps = []
        for i, frame in enumerate(frames):
            is_speech = vad.is_speech(frame, sample_rate)
            if is_speech:
                start = (i * frame_duration) / 1000.0
                end = ((i + 1) * frame_duration) / 1000.0
                timestamps.append((start, end))

    # Agrupar segmentos contiguos
    grouped = []
    if timestamps:
        cur_start, cur_end = timestamps[0]
        for start, end in timestamps[1:]:
            if start - cur_end <= 0.3:
                cur_end = end
            else:
                grouped.append((cur_start, cur_end))
                cur_start, cur_end = start, end
        grouped.append((cur_start, cur_end))

    entries = [(start, end, "") for start, end in grouped]
    tg = textgrid.Textgrid()
    tg.minTimestamp = 0
    tg.maxTimestamp = grouped[-1][1] if grouped else 1
    tg.addTier(textgrid.IntervalTier("IPU", entries, tg.minTimestamp, tg.maxTimestamp))

    tg.save(output_textgrid, format="short_textgrid", includeBlankSpaces=True)
    print(f"[✓] TextGrid IPU guardado en: {output_textgrid}")

# ------------------------------
# Paso 3: Alineación y evaluación
# ------------------------------

def extract_text_with_regex(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
        paragraphs = re.findall(r'<p>(.*?)</p>', content, re.DOTALL)
        text = ' '.join(paragraphs)
        return re.sub(r'\s+', ' ', text).strip()

def align_transcription_to_ipu(ipu_intervals, transcription):
    words = transcription.split()
    idx = 0
    aligned = []

    for start, end, _ in ipu_intervals:
        segment_words = []
        while idx < len(words) and len(' '.join(segment_words)) < (end - start) * 15:  # estimación
            segment_words.append(words[idx])
            idx += 1
        aligned.append((start, end, ' '.join(segment_words)))
    
    return aligned

def get_phonemes_espeak(text):
    try:
        cmd = f'espeak-ng -q -v es -x "{text}"'
        result = subprocess.check_output(cmd, shell=True, encoding='utf-8')
        return result.strip()
    except subprocess.CalledProcessError:
        return ""

def find_transcription_errors(ipu_intervals, transc_intervals):
    errors = []
    for ipu, transc in zip(ipu_intervals, transc_intervals):
        ipu_text = ipu[2].strip()
        transc_text = transc[2].strip()

        if not ipu_text or not transc_text:
            continue

        phon_ipu = get_phonemes_espeak(ipu_text)
        phon_transc = get_phonemes_espeak(transc_text)

        if phon_ipu != phon_transc:
            errors.append((ipu[0], ipu[1], f"Desajuste fonético"))
    return errors

def export_errors_to_txt(errors, path_txt):
    with open(path_txt, 'w', encoding='utf-8') as f:
        f.write("Inicio\tFin\tDescripción\n")
        for start, end, desc in errors:
            f.write(f"{start:.2f}\t{end:.2f}\t{desc}\n")
    print(f"[✓] Errores exportados a: {path_txt}")

def process_textgrid(ipu_textgrid_path, html_path, output_path):
    tg = textgrid.openTextgrid(ipu_textgrid_path, includeEmptyIntervals=True)
    ipu_tier = tg.getTier("IPU")
    ipu_intervals = ipu_tier.entries

    transcription = extract_text_with_regex(html_path)
    transc_entries = align_transcription_to_ipu(ipu_intervals, transcription)
    transc_tier = textgrid.IntervalTier("Transc", transc_entries, tg.minTimestamp, tg.maxTimestamp)

    error_entries = find_transcription_errors(ipu_intervals, transc_entries)
    errors_tier = textgrid.IntervalTier("TranscErrors", error_entries, tg.minTimestamp, tg.maxTimestamp)

    tg.addTier(transc_tier)
    tg.addTier(errors_tier)

    tg.save(output_path, format="short_textgrid", includeBlankSpaces=True)
    print(f"[✓] TextGrid completo guardado en: {output_path}")

    export_errors_to_txt(error_entries, output_path.replace(".TextGrid", "_errores.txt"))
