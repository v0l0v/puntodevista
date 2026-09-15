import os
import subprocess
import soundfile as sf
import numpy as np
from kokoro_onnx import Kokoro

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(DIR, 'tmp_audio')
os.makedirs(TMP, exist_ok=True)

kokoro = Kokoro(
    os.path.join(DIR, 'kokoro_models/kokoro-v1.0.onnx'),
    os.path.join(DIR, 'kokoro_models/voices-v1.0.bin')
)

script = [
    ("ROBERTO", "em_alex", "es-ES-AlvaroNeural", "¡Hola, muy buenas! Bienvenidos a Punto de Vista, tu dosis diaria de cultura fotográfica. Hoy tenemos un programa apasionante con análisis de archivo, debate y taller práctico. Para profundizar en el proyecto protagonista de hoy, os dejo con Beatriz. ¡Hola Beatriz!"),
    ("BEATRIZ", "ef_dora", "es-ES-ElviraNeural", "¡Hola Roberto y muy buenas a todos! Es un placer compartir este espacio. Hoy nos adentramos en la sutileza de la luz natural y cómo los grandes maestros del siglo veinte utilizaban la penumbra para evocar el paso del tiempo. Pero la fotografía también es salir a la calle a equivocarse y aprender, así que doy paso a Nicolás con el reto de hoy."),
    ("NICOLAS", "em_santa", "es-US-AlonsoNeural", "¡Qué tal gente! Dejémonos de tanta teoría de museo y pasemos a la acción. El reto de hoy es directo: sal a la calle con una sola óptica fija y busca reflejos imposibles en charcos o escaparates. ¡A quemar suela y buenas fotos!")
]

# 1. Generación Kokoro
print("🎙️ Generando versión Kokoro en lamaquina...")
kokoro_parts = []
sr_target = 24000
silence = np.zeros(int(sr_target * 0.7), dtype=np.float32)

for spk, k_voice, _, text in script:
    print(f"  Synthesizing Kokoro: {spk} ({k_voice})...")
    samples, sr = kokoro.create(text, voice=k_voice, speed=1.0, lang="es")
    kokoro_parts.append(samples)
    kokoro_parts.append(silence)

kokoro_all = np.concatenate(kokoro_parts)
kokoro_wav = os.path.join(DIR, 'podcast', 'demo_trio_kokoro.wav')
kokoro_mp3 = os.path.join(DIR, 'podcast', 'demo_trio_kokoro.mp3')
os.makedirs(os.path.join(DIR, 'podcast'), exist_ok=True)
sf.write(kokoro_wav, kokoro_all, sr_target)
subprocess.run(['ffmpeg', '-y', '-i', kokoro_wav, '-codec:a', 'libmp3lame', '-b:a', '192k', kokoro_mp3], check=True, capture_output=True)
print(f"✅ Kokoro guardado en {kokoro_mp3}")

# 2. Generación Edge-TTS
print("\n🎙️ Generando versión Edge-TTS en lamaquina...")
edge_files = []
edge_bin = os.path.join(DIR, 'venv/bin/edge-tts')
if not os.path.exists(edge_bin):
    edge_bin = 'edge-tts'

for idx, (spk, _, e_voice, text) in enumerate(script):
    part_mp3 = os.path.join(TMP, f"edge_{idx}.mp3")
    print(f"  Synthesizing Edge-TTS: {spk} ({e_voice})...")
    subprocess.run([edge_bin, '--voice', e_voice, '--rate=-3%', '--text', text, '--write-media', part_mp3], check=True, capture_output=True)
    edge_files.append(part_mp3)

edge_mp3 = os.path.join(DIR, 'podcast', 'demo_trio_edgetts.mp3')
concat_filter = ''.join([f"[{i}:a]" for i in range(len(edge_files))]) + f"concat=n={len(edge_files)}:v=0:a=1[out]"
cmd = ['ffmpeg', '-y']
for ef in edge_files:
    cmd.extend(['-i', ef])
cmd.extend(['-filter_complex', concat_filter, '-map', '[out]', '-codec:a', 'libmp3lame', '-b:a', '192k', edge_mp3])
subprocess.run(cmd, check=True, capture_output=True)
print(f"✅ Edge-TTS guardado en {edge_mp3}")
