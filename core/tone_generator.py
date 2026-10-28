"""
Generador de tonos puros de prueba y evaluación para verificación de frecuencias.
Incluye envolvente suave anti-clic (20 ms) para evitar transitorios bruscos.
"""

from typing import Tuple
import numpy as np


def generate_evaluation_tone(
    frequency_hz: float,
    duration_s: float = 1.5,
    ear: str = "both",  # "left", "right", "both"
    level_db: float = 0.0,  # 0 dB = max, -20 dB, -40 dB, etc.
    fs: int = 44100
) -> np.ndarray:
    """
    Genera un tono senoidal puro para evaluar la audición en una frecuencia concreta.
    Retorna un array estéreo [num_samples, 2] con envolvente anti-clic.
    """
    num_samples = int(duration_s * fs)
    t = np.arange(num_samples) / fs
    
    # Amplitud lineal según atenuación en dB
    amplitude = 10.0 ** (level_db / 20.0)
    amplitude = min(1.0, max(0.0, amplitude))
    
    # Generar seno puro
    tone = amplitude * np.sin(2.0 * np.pi * frequency_hz * t)
    
    # Envolvente anti-clic (rampas de subida y bajada de 20 ms)
    ramp_len = int(0.02 * fs)
    if ramp_len > 0 and num_samples > 2 * ramp_len:
        ramp = 0.5 * (1.0 - np.cos(np.pi * np.arange(ramp_len) / ramp_len))
        tone[:ramp_len] *= ramp
        tone[-ramp_len:] *= ramp[::-1]
        
    left_channel = np.zeros(num_samples, dtype=np.float32)
    right_channel = np.zeros(num_samples, dtype=np.float32)
    
    ear_clean = ear.lower()
    if ear_clean in ("left", "l", "izq", "izquierdo"):
        left_channel = tone.astype(np.float32)
    elif ear_clean in ("right", "r", "der", "derecho"):
        right_channel = tone.astype(np.float32)
    else:  # both
        left_channel = tone.astype(np.float32)
        right_channel = tone.astype(np.float32)
        
    return np.column_stack((left_channel, right_channel))
