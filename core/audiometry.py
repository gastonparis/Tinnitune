"""
Módulo de manejo e interpolación de audiometrías para tratamiento de tinnitus.
Basado en el protocolo de Cuesta, Garzón y Cobo (Brain Sci. 2022, 12, 82).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import numpy as np
from scipy.interpolate import pchip_interpolate, interp1d

# Las 11 frecuencias estándar analizadas en el paper de Cobo et al.
STANDARD_FREQUENCIES: List[int] = [
    125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000
]

# Diferencia de umbral de presión sonora RETSPL (ISO 389-1) relativa a 1000 Hz
# Modela la curva de sensibilidad natural del oído humano sano a cada frecuencia
ISO_RETSPL_DIFF_1000HZ: Dict[int, float] = {
    125: 38.0,
    250: 18.5,
    500: 4.5,
    750: 0.5,
    1000: 0.0,    # Frecuencia de anclaje (referencia)
    1500: -0.5,
    2000: 2.0,
    3000: 3.0,
    4000: 2.5,
    6000: 8.5,
    8000: 6.0
}

MIN_HL_DB: float = -10.0
MAX_HL_DB: float = 120.0


def calculate_estimated_hl(
    test_freq: int,
    test_level_dbfs: float,
    calib_1000hz_dbfs: float,
    known_hl_1000hz: float
) -> float:
    """
    Calcula el umbral estimado en dB HL a partir de la calibración a 1000 Hz y la norma ISO 389.
    
    estimated_hl = known_hl_1000 + (test_dbfs - calib_dbfs) - ISO_RETSPL_DIFF
    Redondeado al múltiplo de 5 dB más cercano (estándar audiológico).
    """
    diff_retspl = ISO_RETSPL_DIFF_1000HZ.get(test_freq, 0.0)
    raw_hl = known_hl_1000hz + (test_level_dbfs - calib_1000hz_dbfs) - diff_retspl
    
    # Limitar a rango clínico razonable
    clamped = max(MIN_HL_DB, min(MAX_HL_DB, raw_hl))
    # Redondeo audiológico a pasos de 5 dB
    rounded = round(clamped / 5.0) * 5.0
    return float(rounded)


@dataclass
class AudiogramData:
    """
    Representa la audiometría tonal liminar para ambos oídos en dB HL.
    """
    left_ear: Dict[int, float] = field(default_factory=dict)
    right_ear: Dict[int, float] = field(default_factory=dict)

    def __post_init__(self):
        # Si no se proveen valores, inicializar con audición normal (0 dB HL)
        for freq in STANDARD_FREQUENCIES:
            if freq not in self.left_ear:
                self.left_ear[freq] = 0.0
            if freq not in self.right_ear:
                self.right_ear[freq] = 0.0

    def set_threshold(self, ear: str, freq: int, hl_db: float) -> None:
        """Asigna el umbral de pérdida auditiva (dB HL) a una frecuencia dada."""
        if freq not in STANDARD_FREQUENCIES:
            raise ValueError(f"Frecuencia {freq} no es una de las 11 frecuencias estándar.")
        clamped_val = max(MIN_HL_DB, min(MAX_HL_DB, float(hl_db)))
        if ear.lower() in ("left", "l", "izq", "izquierdo"):
            self.left_ear[freq] = clamped_val
        elif ear.lower() in ("right", "r", "der", "derecho"):
            self.right_ear[freq] = clamped_val
        else:
            raise ValueError(f"Oído desconocido: {ear}. Use 'left' o 'right'.")

    def get_threshold(self, ear: str, freq: int) -> float:
        """Obtiene el umbral en dB HL para un oído y frecuencia."""
        if ear.lower() in ("left", "l", "izq", "izquierdo"):
            return self.left_ear.get(freq, 0.0)
        return self.right_ear.get(freq, 0.0)

    def get_arrays(self, ear: str) -> Tuple[np.ndarray, np.ndarray]:
        """Retorna tupla de (frecuencias, dB_HL) ordenados."""
        data = self.left_ear if ear.lower() in ("left", "l", "izq", "izquierdo") else self.right_ear
        freqs = np.array(STANDARD_FREQUENCIES, dtype=np.float64)
        hls = np.array([data[f] for f in STANDARD_FREQUENCIES], dtype=np.float64)
        return freqs, hls

    def interpolate_curve(
        self, 
        ear: str, 
        target_freqs: np.ndarray,
        method: str = "pchip"
    ) -> np.ndarray:
        """
        Interpola la curva de pérdida auditiva de forma suave en un vector continuo de frecuencias.
        Utiliza escala logarítmica de frecuencias para alineación perceptual (octavas).
        """
        freqs, hls = self.get_arrays(ear)
        
        # Trabajamos en escala logarítmica de frecuencia
        log_freqs = np.log10(freqs)
        
        # Evitar log(0) si target_freqs incluye 0 Hz
        valid_mask = target_freqs > 0
        log_targets = np.zeros_like(target_freqs, dtype=np.float64)
        log_targets[valid_mask] = np.log10(target_freqs[valid_mask])
        
        # PCHIP (Piecewise Cubic Hermite Interpolating Polynomial) preserva la monotonicidad
        # y no produce sobreoscilaciones espurias como un spline natural.
        if method == "pchip":
            interpolated = pchip_interpolate(log_freqs, hls, log_targets)
        else:
            f_interp = interp1d(log_freqs, hls, kind="linear", fill_value="extrapolate")
            interpolated = f_interp(log_targets)
            
        # Para frecuencias inferiores a 125 Hz o superiores a 8000 Hz, mantener los extremos
        interpolated[target_freqs < freqs[0]] = hls[0]
        interpolated[target_freqs > freqs[-1]] = hls[-1]
        
        return np.clip(interpolated, MIN_HL_DB, MAX_HL_DB)
