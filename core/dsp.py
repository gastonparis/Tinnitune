"""
Motor DSP de generación y filtrado de señales de tratamiento para acúfenos.
Basado en:
- Cuesta, Garzón & Cobo (Brain Sci. 2022): Ruido de banda ancha coloreado por audiometría.
- Cobo, Cuesta & De la Colina (Acta Acustica 2021): Entorno Acústico Enriquecido (EAE)
  con secuencias de pulsos Burst, Pip y Gammatone.
"""

from typing import Callable, Optional, Tuple
import numpy as np
import scipy.signal as signal
from core.audiometry import AudiogramData, STANDARD_FREQUENCIES


def design_audiogram_fir_filter(
    audiogram: AudiogramData,
    ear: str,
    fs: int = 44100,
    num_taps: int = 2049
) -> np.ndarray:
    """
    Diseña un filtro FIR de fase lineal cuya respuesta en frecuencia modela
    la curva de pérdida auditiva (dB HL) del oído especificado.
    
    G(f) = 10^(HL(f) / 20)
    """
    if num_taps % 2 == 0:
        num_taps += 1  # Debe ser impar para Tipo I (fase lineal y paso en Nyquist)
        
    nyquist = fs / 2.0
    
    # Puntos de frecuencia para firwin2 (deben comenzar en 0 y terminar en Nyquist)
    freqs, hls = audiogram.get_arrays(ear)
    
    f_grid = [0.0]
    for f in freqs:
        if f < nyquist:
            f_grid.append(float(f))
    if nyquist not in f_grid:
        f_grid.append(nyquist)
        
    f_grid = np.array(f_grid, dtype=np.float64)
    
    # Interpolar HL en los puntos f_grid
    # Para 0 Hz usamos el valor de 125 Hz; para Nyquist usamos el de 8 kHz
    hl_interpolated = audiogram.interpolate_curve(ear, f_grid)
    
    # Convertir dB HL a ganancia de amplitud lineal: G = 10^(HL / 20)
    gains = 10.0 ** (hl_interpolated / 20.0)
    
    # Normalizar para que la ganancia máxima sea 1.0 (evita amplitudes desmesuradas)
    max_gain = np.max(gains)
    if max_gain > 0:
        gains = gains / max_gain
        
    # Diseñar filtro FIR de fase lineal mediante el método de ventana / muestreo espectral
    taps = signal.firwin2(
        num_taps,
        f_grid,
        gains,
        fs=fs,
        window="hann"
    )
    return taps


def apply_fade_in_out(
    audio: np.ndarray, 
    fs: int = 44100, 
    fade_duration_s: float = 5.0
) -> np.ndarray:
    """
    Aplica una rampa suave de desvanecimiento (Hann/Raised Cosine) al inicio
    y al final de la señal para evitar clics o sobresaltos al paciente.
    """
    num_samples = audio.shape[0]
    fade_samples = int(min(fade_duration_s * fs, num_samples / 4))
    
    if fade_samples <= 0:
        return audio
        
    # Ventana de Hann para fade-in (de 0 a 1) y fade-out (de 1 a 0)
    ramp = 0.5 * (1.0 - np.cos(np.pi * np.arange(fade_samples) / fade_samples))
    
    out = audio.copy()
    if audio.ndim == 1:
        out[:fade_samples] *= ramp
        out[-fade_samples:] *= ramp[::-1]
    else:
        out[:fade_samples, :] *= ramp[:, np.newaxis]
        out[-fade_samples:, :] *= ramp[::-1, np.newaxis]
        
    return out


def normalize_peak(
    audio: np.ndarray, 
    target_peak_dbfs: float = -1.0
) -> np.ndarray:
    """
    Normaliza el nivel pico estéreo a un valor seguro (por defecto -1.0 dBFS)
    garantizando margen contra inter-sample peaks y distorsión DAC en celulares.
    """
    target_amplitude = 10.0 ** (target_peak_dbfs / 20.0)
    max_val = np.max(np.abs(audio))
    if max_val > 1e-9:
        return audio * (target_amplitude / max_val)
    return audio


def generate_continuous_broadband_noise(
    audiogram: AudiogramData,
    duration_sec: float,
    fs: int = 44100,
    chunk_sec: float = 30.0,
    progress_callback: Optional[Callable[[float], None]] = None
) -> np.ndarray:
    """
    Genera el estímulo principal del estudio (Cobo et al. 2022):
    Ruido de banda ancha estéreo continuo, filtrado independientemente en cada oído
    según la curva audiométrica del paciente.
    
    Procesa en bloques (chunks) para permitir duraciones de hasta 60 minutos sin
    agotar la memoria RAM y reportar progreso fluido.
    """
    total_samples = int(duration_sec * fs)
    b_left = design_audiogram_fir_filter(audiogram, "left", fs=fs)
    b_right = design_audiogram_fir_filter(audiogram, "right", fs=fs)
    
    filter_delay = (len(b_left) - 1) // 2
    chunk_samples = int(chunk_sec * fs)
    
    left_channel = np.empty(total_samples, dtype=np.float32)
    right_channel = np.empty(total_samples, dtype=np.float32)
    
    # Generar y filtrar por chunks
    processed_samples = 0
    zi_l = np.zeros(len(b_left) - 1, dtype=np.float64)
    zi_r = np.zeros(len(b_right) - 1, dtype=np.float64)
    
    while processed_samples < total_samples:
        current_chunk_size = min(chunk_samples, total_samples - processed_samples)
        
        # Ruido blanco gaussiano no correlacionado entre canales
        w_l = np.random.normal(0.0, 1.0, current_chunk_size)
        w_r = np.random.normal(0.0, 1.0, current_chunk_size)
        
        # Filtrado lineal con estado persistente para evitar discontinuidades entre bloques
        f_l, zi_l = signal.lfilter(b_left, 1.0, w_l, zi=zi_l)
        f_r, zi_r = signal.lfilter(b_right, 1.0, w_r, zi=zi_r)
        
        left_channel[processed_samples:processed_samples + current_chunk_size] = f_l.astype(np.float32)
        right_channel[processed_samples:processed_samples + current_chunk_size] = f_r.astype(np.float32)
        
        processed_samples += current_chunk_size
        if progress_callback:
            progress_callback(processed_samples / total_samples)
            
    # Unir en señal estéreo
    stereo = np.column_stack((left_channel, right_channel))
    
    # Aplicar fade in/out
    stereo = apply_fade_in_out(stereo, fs=fs, fade_duration_s=5.0)
    
    # Normalizar pico a -1.0 dBFS
    stereo = normalize_peak(stereo, target_peak_dbfs=-1.0)
    
    return stereo


def generate_sequential_eae(
    audiogram: AudiogramData,
    duration_sec: float,
    stimulus_type: str = "burst",  # "burst", "pip", "gamma"
    rate_per_sec: float = 4.0,     # Tasa de pulsos por segundo
    pulse_length_s: float = 0.15,  # Duración de cada pulso
    fs: int = 44100,
    progress_callback: Optional[Callable[[float], None]] = None
) -> np.ndarray:
    """
    Genera el estímulo del Entorno Acústico Enriquecido (EAE) en modo secuencial
    (Cobo et al. 2021, Acta Acustica).
    
    s(t) = sum_n A_n(f_n) * W(t - s_n) * cos(2*pi*f_n*(t - s_n))
    """
    total_samples = int(duration_sec * fs)
    left_channel = np.zeros(total_samples, dtype=np.float32)
    right_channel = np.zeros(total_samples, dtype=np.float32)
    
    pulse_samples = int(pulse_length_s * fs)
    t_pulse = np.arange(pulse_samples, dtype=np.float64) / fs
    
    # Construir la ventana W(t) según el tipo de estímulo
    if stimulus_type.lower() == "pip":
        # Tone-pip: Asimétrica, subida rápida y decaimiento exponencial (alpha ~ 50)
        alpha = 40.0
        w = (t_pulse / (pulse_length_s * 0.1 + 1e-9)) * np.exp(-alpha * t_pulse)
        w = w / (np.max(w) + 1e-9)
    elif stimulus_type.lower() == "gamma":
        # Gammatone window de orden n=3
        b = 200.0  # Ancho de banda de atenuación
        w = (t_pulse ** 2) * np.exp(-2 * np.pi * b * t_pulse)
        w = w / (np.max(w) + 1e-9)
    else:  # "burst"
        # Tone-burst: Ventana simétrica de Hann
        w = signal.windows.hann(pulse_samples)
        
    # Calcular número de eventos
    num_pulses = int(duration_sec * rate_per_sec)
    inter_pulse_interval = fs / rate_per_sec
    
    # Para cada oído de forma dicótica (secuencias independientes)
    for ear_idx, ear_name in enumerate(["left", "right"]):
        channel = left_channel if ear_idx == 0 else right_channel
        
        # Tiempos de inicio con pequeña fluctuación aleatoria (jitter de +/- 10%)
        for i in range(num_pulses):
            center_sample = int(i * inter_pulse_interval + np.random.uniform(-0.1, 0.1) * inter_pulse_interval)
            start_sample = center_sample
            end_sample = start_sample + pulse_samples
            
            if start_sample < 0 or end_sample > total_samples:
                continue
                
            # Seleccionar frecuencia aleatoria en escala logarítmica (125 a 8000 Hz)
            f_log = np.random.uniform(np.log10(125.0), np.log10(8000.0))
            fn = 10.0 ** f_log
            
            # Obtener ganancia audiométrica interpolada
            hl_val = audiogram.interpolate_curve(ear_name, np.array([fn]))[0]
            amplitude = 10.0 ** (hl_val / 20.0)
            
            # Sintetizar el pulso tonal modulado
            phase = np.random.uniform(0, 2 * np.pi)
            tone = np.cos(2.0 * np.pi * fn * t_pulse + phase)
            pulse = amplitude * w * tone
            
            channel[start_sample:end_sample] += pulse.astype(np.float32)
            
            if progress_callback and ear_idx == 1 and i % 50 == 0:
                progress_callback(i / num_pulses)
                
    stereo = np.column_stack((left_channel, right_channel))
    stereo = apply_fade_in_out(stereo, fs=fs, fade_duration_s=5.0)
    stereo = normalize_peak(stereo, target_peak_dbfs=-1.0)
    return stereo
