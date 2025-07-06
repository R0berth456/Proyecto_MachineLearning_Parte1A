import os
from ProyectoMachin import transcribir_audio_a_html, detectar_ipus, process_textgrid  # Reutilizamos funciones previas

# 📁 Ruta a los audios descargados del dataset
carpeta_audios = "Audios/wav"
carpeta_resultados = "Resultados"

# 🔁 Procesamiento en lote
for nombre_archivo in os.listdir(carpeta_audios):
    if nombre_archivo.endswith(".wav"):
        print(f"\n🔊 Procesando: {nombre_archivo}")

        ruta_audio = os.path.join(carpeta_audios, nombre_archivo)
        nombre_base = os.path.splitext(nombre_archivo)[0]

        ruta_html = os.path.join(carpeta_resultados, f"{nombre_base}.html")
        ruta_textgrid = os.path.join(carpeta_resultados, f"{nombre_base}.TextGrid")
        ruta_textgrid_procesado = os.path.join(carpeta_resultados, f"{nombre_base}_procesado.TextGrid")

        try:
            # Paso 1: Transcripción
            transcribir_audio_a_html(ruta_audio, ruta_html)

            # Paso 2: Detección de IPUs
            detectar_ipus(ruta_audio, ruta_textgrid)

            # Paso 3: Alineación y errores
            process_textgrid(ruta_textgrid, ruta_html, ruta_textgrid_procesado)

        except Exception as e:
            print(f"❌ Error procesando {nombre_archivo}: {e}")
