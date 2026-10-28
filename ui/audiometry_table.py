"""
Widget de tabla interactiva para ingreso y edición de valores de audiometría.
Permite ingresar dB HL para cada una de las 11 frecuencias estándar y cargar perfiles rápidos.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QSpinBox, QPushButton, QGroupBox, QHeaderView
)
from core.audiometry import AudiogramData, STANDARD_FREQUENCIES


class AudiometryTableWidget(QWidget):
    # Señal emitida al cambiar cualquier umbral en la tabla
    audiogram_changed = Signal(AudiogramData)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.audiogram = AudiogramData()
        self.spinboxes_left = {}
        self.spinboxes_right = {}
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Grupo de Tabla
        table_group = QGroupBox("Valores de Audiometría (dB HL)")
        table_layout = QVBoxLayout(table_group)
        
        self.table = QTableWidget(len(STANDARD_FREQUENCIES), 3)
        self.table.setHorizontalHeaderLabels(["Frecuencia", "Oído Izq (L) [dB]", "Oído Der (R) [dB]"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        
        for row, f in enumerate(STANDARD_FREQUENCIES):
            # Columna 0: Frecuencia
            f_str = f"{f} Hz" if f < 1000 else f"{f/1000:g} kHz"
            f_item = QTableWidgetItem(f_str)
            f_item.setTextAlignment(0x0084)  # Centrado
            self.table.setItem(row, 0, f_item)
            
            # Columna 1: Oído Izquierdo (SpinBox)
            sb_l = QSpinBox()
            sb_l.setRange(-10, 110)
            sb_l.setSingleStep(5)
            sb_l.setValue(int(self.audiogram.get_threshold("left", f)))
            sb_l.setSuffix(" dB")
            sb_l.setStyleSheet("QSpinBox { color: #3498db; font-weight: bold; }")
            sb_l.valueChanged.connect(lambda val, freq=f: self.on_value_changed("left", freq, val))
            self.table.setCellWidget(row, 1, sb_l)
            self.spinboxes_left[f] = sb_l
            
            # Columna 2: Oído Derecho (SpinBox)
            sb_r = QSpinBox()
            sb_r.setRange(-10, 110)
            sb_r.setSingleStep(5)
            sb_r.setValue(int(self.audiogram.get_threshold("right", f)))
            sb_r.setSuffix(" dB")
            sb_r.setStyleSheet("QSpinBox { color: #e74c3c; font-weight: bold; }")
            sb_r.valueChanged.connect(lambda val, freq=f: self.on_value_changed("right", freq, val))
            self.table.setCellWidget(row, 2, sb_r)
            self.spinboxes_right[f] = sb_r
            
        table_layout.addWidget(self.table)
        main_layout.addWidget(table_group)
        
        # Grupo de Presets Rápidos
        preset_group = QGroupBox("Perfiles Audiométricos Rápidos")
        preset_layout = QHBoxLayout(preset_group)
        
        btn_normal = QPushButton("Normal (0 dB)")
        btn_normal.clicked.connect(self.load_preset_normal)
        preset_layout.addWidget(btn_normal)
        
        btn_high_loss = QPushButton("Caída en Agudos")
        btn_high_loss.clicked.connect(self.load_preset_high_freq_loss)
        preset_layout.addWidget(btn_high_loss)
        
        btn_presby = QPushButton("Presbiacusia")
        btn_presby.clicked.connect(self.load_preset_presbycusis)
        preset_layout.addWidget(btn_presby)
        
        main_layout.addWidget(preset_group)
        
    def on_value_changed(self, ear: str, freq: int, val: int):
        self.audiogram.set_threshold(ear, freq, float(val))
        self.audiogram_changed.emit(self.audiogram)
        
    def get_audiogram(self) -> AudiogramData:
        return self.audiogram
        
    def set_single_threshold(self, ear: str, freq: int, val: float):
        """Asigna un valor individual en la tabla y notifica el cambio."""
        ear_clean = "left" if ear.lower() in ("left", "l", "izq", "izquierdo") else "right"
        spinboxes = self.spinboxes_left if ear_clean == "left" else self.spinboxes_right
        
        int_val = int(round(val))
        if freq in spinboxes:
            spinbox = spinboxes[freq]
            spinbox.blockSignals(True)
            spinbox.setValue(int_val)
            spinbox.blockSignals(False)
            
        self.audiogram.set_threshold(ear_clean, freq, float(int_val))
        self.audiogram_changed.emit(self.audiogram)
        
    def set_audiogram_values(self, left_dict: dict, right_dict: dict):
        """Carga valores en la tabla actualizando los spinboxes."""
        self.blockSignals(True)
        for f in STANDARD_FREQUENCIES:
            val_l = int(left_dict.get(f, 0))
            val_r = int(right_dict.get(f, 0))
            if f in self.spinboxes_left:
                self.spinboxes_left[f].blockSignals(True)
                self.spinboxes_left[f].setValue(val_l)
                self.spinboxes_left[f].blockSignals(False)
            if f in self.spinboxes_right:
                self.spinboxes_right[f].blockSignals(True)
                self.spinboxes_right[f].setValue(val_r)
                self.spinboxes_right[f].blockSignals(False)
            self.audiogram.set_threshold("left", f, float(val_l))
            self.audiogram.set_threshold("right", f, float(val_r))
        self.blockSignals(False)
        self.audiogram_changed.emit(self.audiogram)
        
    def load_preset_normal(self):
        zeros = {f: 0 for f in STANDARD_FREQUENCIES}
        self.set_audiogram_values(zeros, zeros)
        
    def load_preset_high_freq_loss(self):
        # Típico trauma acústico / muesca en 4k - 6k con tinnitus frecuente
        profile = {
            125: 10, 250: 10, 500: 15, 750: 15, 1000: 15,
            1500: 20, 2000: 25, 3000: 45, 4000: 65, 6000: 60, 8000: 50
        }
        self.set_audiogram_values(profile, profile)
        
    def load_preset_presbycusis(self):
        # Pérdida progresiva en altas frecuencias
        profile = {
            125: 15, 250: 15, 500: 20, 750: 25, 1000: 30,
            1500: 35, 2000: 45, 3000: 55, 4000: 65, 6000: 75, 8000: 80
        }
        self.set_audiogram_values(profile, profile)
