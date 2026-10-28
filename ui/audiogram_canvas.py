"""
Widget de visualización del audiograma clínico en PySide6 usando Matplotlib.
Sigue las normas audiológicas internacionales:
- Oído Derecho: Color ROJO, marcador 'O', línea continua/discontinua.
- Oído Izquierdo: Color AZUL, marcador 'X', línea continua/discontinua.
- Eje Y invertido (-10 dB HL en la parte superior, 110 dB HL en la inferior).
- Eje X logarítmico con las frecuencias estándar (125 a 8000 Hz).
"""

import numpy as np
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtWidgets import QWidget, QVBoxLayout
from core.audiometry import AudiogramData, STANDARD_FREQUENCIES


class AudiogramCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Crear figura de matplotlib
        self.figure = Figure(figsize=(6, 4.5), dpi=100)
        self.figure.patch.set_facecolor("#2b2b2b")
        
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        
        self.setup_plot()
        
    def setup_plot(self):
        self.ax.clear()
        self.ax.set_facecolor("#1e1e1e")
        
        # Configurar colores de ejes y etiquetas
        self.ax.tick_params(colors="#d0d0d0", which="both")
        for spine in self.ax.spines.values():
            spine.set_color("#555555")
            
        self.ax.set_title("Audiometría Tonal Liminar (dB HL)", color="#ffffff", fontsize=11, fontweight="bold", pad=10)
        self.ax.set_xlabel("Frecuencia (Hz)", color="#d0d0d0", fontsize=9)
        self.ax.set_ylabel("Pérdida Auditiva (dB HL)", color="#d0d0d0", fontsize=9)
        
        # Eje X logarítmico con las frecuencias exactas
        self.ax.set_xscale("log")
        self.ax.set_xticks(STANDARD_FREQUENCIES)
        self.ax.set_xticklabels([str(f) if f < 1000 else f"{f//1000}k" if f % 1000 == 0 else f"{f/1000:g}k" for f in STANDARD_FREQUENCIES], fontsize=8)
        self.ax.set_xlim(100, 9500)
        
        # Eje Y invertido (estándar audiológico: mejor audición arriba, peor abajo)
        self.ax.set_ylim(110, -10)
        self.ax.set_yticks(np.arange(-10, 120, 10))
        
        # Rejilla médica
        self.ax.grid(True, which="major", color="#3a3a3a", linestyle="--", linewidth=0.7)
        self.ax.axhline(0, color="#666666", linestyle="-", linewidth=0.8)
        self.ax.axhline(25, color="#558855", linestyle=":", linewidth=0.9, label="Límite normal (25 dB)")
        
    def update_audiogram(self, audiogram: AudiogramData):
        """Actualiza el gráfico con las curvas de ambos oídos."""
        self.setup_plot()
        
        freqs = np.array(STANDARD_FREQUENCIES)
        f_dense = np.logspace(np.log10(125), np.log10(8000), 200)
        
        # Oído Izquierdo (Azul, 'X')
        _, hl_l = audiogram.get_arrays("left")
        curve_l = audiogram.interpolate_curve("left", f_dense)
        self.ax.plot(f_dense, curve_l, color="#3498db", linestyle="-", linewidth=1.8, alpha=0.85, label="Oído Izquierdo (L)")
        self.ax.plot(freqs, hl_l, color="#3498db", marker="x", markersize=9, markeredgewidth=2.2, linestyle="None")
        
        # Oído Derecho (Rojo, 'O')
        _, hl_r = audiogram.get_arrays("right")
        curve_r = audiogram.interpolate_curve("right", f_dense)
        self.ax.plot(f_dense, curve_r, color="#e74c3c", linestyle="-", linewidth=1.8, alpha=0.85, label="Oído Derecho (R)")
        self.ax.plot(freqs, hl_r, color="#e74c3c", marker="o", markersize=7, markerfacecolor="none", markeredgewidth=2.0, linestyle="None")
        
        legend = self.ax.legend(loc="lower right", facecolor="#2b2b2b", edgecolor="#555555", fontsize=8)
        for text in legend.get_texts():
            text.set_color("#e0e0e0")
            
        self.canvas.draw()
