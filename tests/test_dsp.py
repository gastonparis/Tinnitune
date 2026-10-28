"""
Pruebas y verificación de control de calidad para la Etapa 1 (Motor DSP y Exportación).
Verifica:
1. Interpolación audiométrica y diseño de filtros FIR.
2. Concordancia espectral (PSD / FFT) entre la curva generada y la audiometría del paciente.
3. Ausencia de distorsión por saturación (True Peak < 0 dBFS).
4. Suavizado de fade-in y fade-out.
5. Exportación a archivos WAV y MP3 con metadatos válidos.
"""

import os
import sys
import shutil
import tempfile
import numpy as np

# Asegurar que el directorio raíz del proyecto esté en el path de importación
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import scipy.signal as signal
import soundfile as sf
from core.audiometry import AudiogramData, STANDARD_FREQUENCIES
from core.dsp import (
    design_audiogram_fir_filter,
    generate_continuous_broadband_noise,
    generate_sequential_eae,
    apply_fade_in_out,
    normalize_peak
)
from core.exporter import export_audio


def test_audiogram_interpolation():
    print("-> Ejecutando test_audiogram_interpolation...")
    audio_data = AudiogramData()
    
    # Simular una caída típica en agudos (presbiacusia / trauma acústico)
    # 125 a 1000 Hz: 10 dB HL, 2k: 25 dB, 4k: 50 dB, 8k: 65 dB
    test_values = {
        125: 10, 250: 10, 500: 10, 750: 10, 1000: 15,
        1500: 20, 2000: 30, 3000: 45, 4000: 55, 6000: 60, 8000: 70
    }
    for f, val in test_values.items():
        audio_data.set_threshold("left", f, val)
        audio_data.set_threshold("right", f, val - 5)
        
    freqs, hls = audio_data.get_arrays("left")
    assert np.allclose(freqs, STANDARD_FREQUENCIES), "Las frecuencias deben coincidir con las 11 estándar."
    assert hls[-1] == 70, "El valor a 8 kHz debe ser 70 dB HL."
    
    # Interpolar en un punto intermedio (ej. 3500 Hz)
    interp_val = audio_data.interpolate_curve("left", np.array([3500.0]))[0]
    assert 45.0 <= interp_val <= 55.0, f"Interpolación en 3500 Hz errónea: {interp_val}"
    print("   [OK] Interpolación audiométrica correcta.")


def test_fir_filter_linear_phase():
    print("-> Ejecutando test_fir_filter_linear_phase...")
    audio_data = AudiogramData()
    for f in STANDARD_FREQUENCIES:
        audio_data.set_threshold("left", f, 20.0 + (f / 8000.0) * 40.0)
        
    b = design_audiogram_fir_filter(audio_data, "left", fs=44100, num_taps=2049)
    assert len(b) == 2049, "El filtro debe tener el número especificado de taps."
    
    # Comprobar simetría exacta de Tipo I (garantiza fase perfectamente lineal)
    diff_symmetry = np.max(np.abs(b - b[::-1]))
    assert diff_symmetry < 1e-12, f"El filtro FIR debe ser perfectamente simétrico (fase lineal). Dif: {diff_symmetry}"
    print("   [OK] Filtro FIR de fase lineal verificado (sin distorsión de fase).")


def test_spectral_concordance_fft():
    print("-> Ejecutando test_spectral_concordance_fft...")
    audio_data = AudiogramData()
    # Caso asimétrico: izquierda agudos dañados, derecha graves dañados
    left_profile = {
        125: 10, 250: 10, 500: 10, 750: 15, 1000: 15,
        1500: 20, 2000: 30, 3000: 45, 4000: 60, 6000: 65, 8000: 70
    }
    for f, val in left_profile.items():
        audio_data.set_threshold("left", f, val)
        audio_data.set_threshold("right", f, 20)  # Derecho plano
        
    # Generar 15 segundos para estimación espectral precisa (Welch PSD)
    fs = 44100
    audio = generate_continuous_broadband_noise(audio_data, duration_sec=15.0, fs=fs)
    
    # Calcular Densidad Espectral de Potencia (PSD) para el canal izquierdo
    f_psd, pxx_l = signal.welch(audio[:, 0], fs=fs, nperseg=8192)
    
    # Convertir a dB relativos
    pxx_db = 10 * np.log10(pxx_l + 1e-12)
    
    # Comprobar que a 4000 Hz haya sustancialmente más energía que a 250 Hz
    idx_250 = np.argmin(np.abs(f_psd - 250))
    idx_4000 = np.argmin(np.abs(f_psd - 4000))
    
    # En la audiometría: 4000 Hz tiene 60 dB vs 250 Hz con 10 dB (+50 dB de diferencia)
    diff_spectral = pxx_db[idx_4000] - pxx_db[idx_250]
    assert diff_spectral > 25.0, f"La compensación espectral a 4 kHz ({diff_spectral:.1f} dB) no refleja la pérdida auditiva."
    print(f"   [OK] Concordancia espectral validada: diferencia medida 4kHz vs 250Hz = +{diff_spectral:.1f} dB.")


def test_anti_clipping_and_fades():
    print("-> Ejecutando test_anti_clipping_and_fades...")
    audio_data = AudiogramData()
    for f in STANDARD_FREQUENCIES:
        audio_data.set_threshold("left", f, 80.0)
        audio_data.set_threshold("right", f, 80.0)
        
    fs = 44100
    audio = generate_continuous_broadband_noise(audio_data, duration_sec=12.0, fs=fs)
    
    # Verificar pico máximo <= 1.0 (debe estar en torno a -1.0 dBFS = 0.891)
    max_peak = np.max(np.abs(audio))
    max_peak_dbfs = 20 * np.log10(max_peak)
    assert max_peak <= 0.95, f"Pico máximo demasiado alto: {max_peak} ({max_peak_dbfs:.2f} dBFS)"
    assert max_peak >= 0.85, f"Pico máximo demasiado bajo: {max_peak}"
    
    # Verificar fade-in en el inicio: primer milisegundo debe ser prácticamente 0
    start_amplitude = np.mean(np.abs(audio[:100, :]))
    assert start_amplitude < 0.05, f"El fade-in no comenzó en silencio: {start_amplitude}"
    
    # Verificar fade-out al final
    end_amplitude = np.mean(np.abs(audio[-100:, :]))
    assert end_amplitude < 0.05, f"El fade-out no terminó en silencio: {end_amplitude}"
    print(f"   [OK] Protección anti-clipping y desvanecimientos validados (Pico: {max_peak_dbfs:.2f} dBFS).")


def test_sequential_eae_modes():
    print("-> Ejecutando test_sequential_eae_modes...")
    audio_data = AudiogramData()
    for f in STANDARD_FREQUENCIES:
        audio_data.set_threshold("left", f, 30.0)
        audio_data.set_threshold("right", f, 30.0)
        
    for mode in ["burst", "pip", "gamma"]:
        audio = generate_sequential_eae(audio_data, duration_sec=6.0, stimulus_type=mode, fs=44100)
        assert audio.shape == (int(6.0 * 44100), 2), f"Formato incorrecto en modo {mode}"
        assert np.max(np.abs(audio)) <= 0.95, f"Saturación en modo {mode}"
    print("   [OK] Modos secuenciales EAE (burst, pip, gamma) generados correctamente.")


def test_audio_exporter_wav_and_mp3():
    print("-> Ejecutando test_audio_exporter_wav_and_mp3...")
    audio_data = AudiogramData()
    fs = 44100
    audio = generate_continuous_broadband_noise(audio_data, duration_sec=3.0, fs=fs)
    
    tmp_dir = tempfile.mkdtemp()
    try:
        # 1. Exportar WAV
        wav_path = os.path.join(tmp_dir, "test_output.wav")
        res_wav = export_audio(audio, wav_path, fs=fs, format_type="wav")
        assert os.path.exists(res_wav), "El archivo WAV no fue creado."
        wav_info = sf.info(res_wav)
        assert wav_info.samplerate == fs, "Samplerate incorrecto en WAV."
        assert wav_info.channels == 2, "Canales incorrectos en WAV."
        assert abs(wav_info.duration - 3.0) < 0.05, "Duración de WAV incorrecta."
        
        # 2. Exportar MP3
        mp3_path = os.path.join(tmp_dir, "test_output.mp3")
        res_mp3 = export_audio(audio, mp3_path, fs=fs, format_type="mp3", mp3_bitrate="320k")
        assert os.path.exists(res_mp3), "El archivo MP3 no fue creado."
        mp3_size = os.path.getsize(res_mp3)
        assert mp3_size > 10000, f"El archivo MP3 es sospechosamente pequeño: {mp3_size} bytes."
        print(f"   [OK] Exportación validada: WAV ({wav_info.duration:.1f}s) y MP3 ({mp3_size / 1024:.1f} KB).")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    print("=== INICIANDO CONTROL DE CALIDAD - ETAPA 1 (DSP Y EXPORTADOR) ===")
    test_audiogram_interpolation()
    test_fir_filter_linear_phase()
    test_spectral_concordance_fft()
    test_anti_clipping_and_fades()
    test_sequential_eae_modes()
    test_audio_exporter_wav_and_mp3()
    print("=== TODOS LOS CHEQUEOS DE LA ETAPA 1 FUERON SUPERADOS EXITOSAMENTE ===")
