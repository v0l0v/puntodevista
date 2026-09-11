import os
import sys

# Forzar phonemizer a usar la librería del sistema en lugar del wheel espeakng-loader temporal
os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = "/usr/lib/x86_64-linux-gnu/libespeak-ng.so.1"
os.environ["PHONEMIZER_ESPEAK_PATH"] = "/usr/bin"

import soundfile as sf
from kokoro_onnx import Kokoro

onnx_path = "kokoro_models/kokoro-v1.0.onnx"
voices_path = "kokoro_models/voices-v1.0.bin"

kokoro = Kokoro(onnx_path, voices_path)

with open("test_text.txt", "r", encoding="utf-8") as f:
    text = f.read()

for voice in ['em_alex', 'em_santa', 'ef_dora']:
    try:
        print(f"Generando con Kokoro voz: {voice}...")
        samples, sample_rate = kokoro.create(text, voice=voice, speed=1.0, lang="es")
        out_wav = f"tts_comparison/3_kokoro_{voice}.wav"
        sf.write(out_wav, samples, sample_rate)
        print(f"✅ Guardado con éxito: {out_wav}")
        break
    except Exception as e:
        print(f"⚠️ Error con {voice}: {e}")
