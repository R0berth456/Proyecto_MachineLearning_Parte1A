import os
import subprocess

carpeta_audios = "../Audios/mp3"
carpeta_salida_audios = "../Audios/wav"

for archivo in os.listdir(carpeta_audios):
    if archivo.endswith(".mp3"):
        mp3_path = os.path.join(carpeta_audios, archivo)
        nombre_base = os.path.splitext(archivo)[0]
        wav_path = os.path.join(carpeta_salida_audios, f"{nombre_base}.wav")

        # ffmpeg -i input.mp3 -ar 16000 -ac 1 output.wav
        comando = f'ffmpeg -y -i "{mp3_path}" -ar 16000 -ac 1 "{wav_path}"'
        try:
            subprocess.run(comando, shell=True, check=True)
            print(f"[✓] Convertido: {archivo} → {nombre_base}.wav")
        except subprocess.CalledProcessError as e:
            print(f"[✗] Error al convertir {archivo}: {e}")
