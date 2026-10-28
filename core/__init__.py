"""
Paquete core del generador de sonido terapéutico para tinnitus.
"""

from core.audiometry import (
    AudiogramData,
    STANDARD_FREQUENCIES,
    ISO_RETSPL_DIFF_1000HZ,
    calculate_estimated_hl
)
from core.dsp import (
    design_audiogram_fir_filter,
    generate_continuous_broadband_noise,
    generate_sequential_eae,
    apply_fade_in_out,
    normalize_peak
)
from core.exporter import export_audio
from core.tone_generator import generate_evaluation_tone

__all__ = [
    "AudiogramData",
    "STANDARD_FREQUENCIES",
    "design_audiogram_fir_filter",
    "generate_continuous_broadband_noise",
    "generate_sequential_eae",
    "apply_fade_in_out",
    "normalize_peak",
    "export_audio",
    "generate_evaluation_tone"
]
