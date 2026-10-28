"""
Widget para evaluación de frecuencias con Calibración a 1000 Hz y Traspaso Automático a la Audiometría.
Calcula los dB HL estimados aplicando la corrección ISO 389-1 (RETSPL).
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QSlider, QGroupBox, QRadioButton, QButtonGroup,
    QSpinBox, QFrame
)
import numpy as np
from core.audiometry import (
    STANDARD_FREQUENCIES,
    ISO_RETSPL_DIFF_1000HZ,
    calculate_estimated_hl
)
from core.tone_generator import generate_evaluation_tone
from core.audio_player import AudioPlayer


class ToneTesterWidget(QWidget):
    # Emite: (oído: "left"/"right", frecuencia_hz: int, umbral_db_hl: float)
    threshold_assigned = Signal(str, int, float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Estado de calibración por oído
        self.calibrated = {
            "left": False,
            "right": False
        }
        self.calib_dbfs = {
            "left": -65.0,   # Nivel digital donde apenas oye 1000 Hz (ampliado hasta -100 dBFS)
            "right": -65.0
        }
        self.known_hl_1000 = {
            "left": 15.0,    # Valor clínico conocido en 1000 Hz
            "right": 15.0
        }
        
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(8)
        
        # ==============================================================
        # 1. GRUPO: CALIBRACIÓN CON AUDIOMETRÍA PREVIA (A 1000 HZ)
        # ==============================================================
        calib_group = QGroupBox("1. Calibración con Audiometría Previa (a 1000 Hz)")
        calib_layout = QVBoxLayout(calib_group)
        
        lbl_calib_desc = QLabel(
            "<small style='color: #bbb;'>Use el resultado de <b>1000 Hz</b> de su audiometría previa "
            "para calibrar la salida de sus auriculares en esta computadora:</small>"
        )
        lbl_calib_desc.setWordWrap(True)
        calib_layout.addWidget(lbl_calib_desc)
        
        # Selección de oído a calibrar
        ear_sel_layout = QHBoxLayout()
        ear_sel_layout.addWidget(QLabel("Oído a calibrar:"))
        self.rb_calib_l = QRadioButton("Izquierdo (L)")
        self.rb_calib_r = QRadioButton("Derecho (R)")
        self.rb_calib_l.setChecked(True)
        self.calib_ear_group = QButtonGroup(self)
        self.calib_ear_group.addButton(self.rb_calib_l)
        self.calib_ear_group.addButton(self.rb_calib_r)
        self.rb_calib_l.toggled.connect(self.on_calib_ear_changed)
        ear_sel_layout.addWidget(self.rb_calib_l)
        ear_sel_layout.addWidget(self.rb_calib_r)
        calib_layout.addLayout(ear_sel_layout)
        
        # Valor conocido de 1000 Hz de la audiometría
        hl_1k_layout = QHBoxLayout()
        hl_1k_layout.addWidget(QLabel("Mi umbral clínico a 1000 Hz:"))
        self.spin_known_1k = QSpinBox()
        self.spin_known_1k.setRange(-10, 100)
        self.spin_known_1k.setSingleStep(5)
        self.spin_known_1k.setValue(15)
        self.spin_known_1k.setSuffix(" dB HL")
        self.spin_known_1k.valueChanged.connect(self.on_known_1k_changed)
        hl_1k_layout.addWidget(self.spin_known_1k)
        calib_layout.addLayout(hl_1k_layout)
        
        # Slider y SpinBox para buscar el punto apenas audible en 1000 Hz
        slider_calib_layout = QHBoxLayout()
        slider_calib_layout.addWidget(QLabel("Volumen 1000 Hz:"))
        self.slider_calib_1k = QSlider(Qt.Horizontal)
        self.slider_calib_1k.setRange(-100, 0)
        self.slider_calib_1k.setValue(-65)
        self.spin_calib_dbfs = QSpinBox()
        self.spin_calib_dbfs.setRange(-100, 0)
        self.spin_calib_dbfs.setValue(-65)
        self.spin_calib_dbfs.setSuffix(" dBFS")
        self.spin_calib_dbfs.setFixedWidth(95)
        self.spin_calib_dbfs.setStyleSheet("font-weight: bold; color: #2ecc71;")
        
        self.slider_calib_1k.valueChanged.connect(self.on_calib_slider_changed)
        self.spin_calib_dbfs.valueChanged.connect(self.on_calib_spin_changed)
        
        slider_calib_layout.addWidget(self.slider_calib_1k)
        slider_calib_layout.addWidget(self.spin_calib_dbfs)
        calib_layout.addLayout(slider_calib_layout)
        
        # Botones de calibración
        btn_calib_layout = QHBoxLayout()
        self.btn_test_1k = QPushButton("▶ Probar 1000 Hz")
        self.btn_test_1k.setStyleSheet("QPushButton { font-weight: bold; background-color: #2980b9; color: white; }")
        self.btn_test_1k.clicked.connect(self.play_calib_1k)
        btn_calib_layout.addWidget(self.btn_test_1k)
        
        self.btn_set_calib = QPushButton("✓ Fijar Referencia (Apenas Oigo)")
        self.btn_set_calib.setStyleSheet("QPushButton { font-weight: bold; background-color: #27ae60; color: white; }")
        self.btn_set_calib.clicked.connect(self.set_calibration_reference)
        btn_calib_layout.addWidget(self.btn_set_calib)
        calib_layout.addLayout(btn_calib_layout)
        
        # Estado actual de calibración
        self.lbl_calib_status = QLabel("Estado L: Calibrado (-65 dBFS = 15 dB HL) | R: Calibrado (-65 dBFS = 15 dB HL)")
        self.lbl_calib_status.setStyleSheet("color: #2ecc71; font-weight: bold; font-size: 10px;")
        self.lbl_calib_status.setAlignment(Qt.AlignCenter)
        calib_layout.addWidget(self.lbl_calib_status)
        
        main_layout.addWidget(calib_group)
        
        # ==============================================================
        # 2. GRUPO: EVALUACIÓN Y TRASPASO DIRECTO A AUDIOMETRÍA
        # ==============================================================
        eval_group = QGroupBox("2. Evaluación de Frecuencia y Asignación Automática")
        eval_layout = QVBoxLayout(eval_group)
        
        # Selector de Frecuencia y Oído a Evaluar
        f_ear_layout = QHBoxLayout()
        f_ear_layout.addWidget(QLabel("Frecuencia:"))
        self.combo_freq = QComboBox()
        for f in STANDARD_FREQUENCIES:
            f_str = f"{f} Hz" if f < 1000 else f"{f/1000:g} kHz ({f} Hz)"
            self.combo_freq.addItem(f_str, f)
        self.combo_freq.setCurrentIndex(6)  # 2000 Hz
        self.combo_freq.currentIndexChanged.connect(self.update_estimated_hl_display)
        f_ear_layout.addWidget(self.combo_freq)
        
        f_ear_layout.addWidget(QLabel("Oído:"))
        self.rb_test_l = QRadioButton("Izq (L)")
        self.rb_test_r = QRadioButton("Der (R)")
        self.rb_test_l.setChecked(True)
        self.test_ear_group = QButtonGroup(self)
        self.test_ear_group.addButton(self.rb_test_l)
        self.test_ear_group.addButton(self.rb_test_r)
        self.rb_test_l.toggled.connect(self.update_estimated_hl_display)
        f_ear_layout.addWidget(self.rb_test_l)
        f_ear_layout.addWidget(self.rb_test_r)
        eval_layout.addLayout(f_ear_layout)
        
        # Slider y SpinBox de Nivel de Prueba (rango ampliado hasta -100 dBFS)
        vol_layout = QHBoxLayout()
        vol_layout.addWidget(QLabel("Intensidad de Prueba:"))
        self.slider_test_vol = QSlider(Qt.Horizontal)
        self.slider_test_vol.setRange(-100, 0)
        self.slider_test_vol.setValue(-50)
        self.spin_test_vol = QSpinBox()
        self.spin_test_vol.setRange(-100, 0)
        self.spin_test_vol.setValue(-50)
        self.spin_test_vol.setSuffix(" dBFS")
        self.spin_test_vol.setFixedWidth(95)
        self.spin_test_vol.setStyleSheet("font-weight: bold; color: #3498db;")
        
        self.slider_test_vol.valueChanged.connect(self.on_test_slider_changed)
        self.spin_test_vol.valueChanged.connect(self.on_test_spin_changed)
        
        vol_layout.addWidget(self.slider_test_vol)
        vol_layout.addWidget(self.spin_test_vol)
        eval_layout.addLayout(vol_layout)
        
        # Indicador Destacado de dB HL Calculado según ISO
        hl_display_layout = QHBoxLayout()
        hl_display_layout.addWidget(QLabel("Umbral Calculado (ISO 389):"))
        self.lbl_hl_calc = QLabel("25 dB HL")
        self.lbl_hl_calc.setStyleSheet(
            "QLabel { font-size: 14px; font-weight: bold; color: #3498db; background-color: #2c3e50; padding: 4px 10px; border-radius: 4px; }"
        )
        hl_display_layout.addWidget(self.lbl_hl_calc)
        hl_display_layout.addStretch()
        eval_layout.addLayout(hl_display_layout)
        
        # Botones de Acción: Probar y Transferir
        actions_layout = QHBoxLayout()
        self.btn_play_test = QPushButton("▶ Escuchar Tono (1.5s)")
        self.btn_play_test.setStyleSheet(
            "QPushButton { background-color: #34495e; color: white; font-weight: bold; padding: 6px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #4a6278; }"
        )
        self.btn_play_test.clicked.connect(self.play_test_tone)
        actions_layout.addWidget(self.btn_play_test)
        
        self.btn_transfer = QPushButton("📥 Pasar Valor a Tabla de Audiometría")
        self.btn_transfer.setStyleSheet(
            "QPushButton { background-color: #d35400; color: white; font-weight: bold; padding: 8px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #e67e22; }"
        )
        self.btn_transfer.clicked.connect(self.transfer_value_to_table)
        actions_layout.addWidget(self.btn_transfer)
        eval_layout.addLayout(actions_layout)
        
        main_layout.addWidget(eval_group)
        self.update_estimated_hl_display()
        
    def get_calib_ear(self) -> str:
        return "left" if self.rb_calib_l.isChecked() else "right"
        
    def get_test_ear(self) -> str:
        return "left" if self.rb_test_l.isChecked() else "right"
        
    def on_calib_ear_changed(self):
        ear = self.get_calib_ear()
        self.spin_known_1k.blockSignals(True)
        self.spin_known_1k.setValue(int(self.known_hl_1000[ear]))
        self.spin_known_1k.blockSignals(False)
        
        self.slider_calib_1k.blockSignals(True)
        self.slider_calib_1k.setValue(int(self.calib_dbfs[ear]))
        self.spin_calib_dbfs.blockSignals(True)
        self.spin_calib_dbfs.setValue(int(self.calib_dbfs[ear]))
        self.slider_calib_1k.blockSignals(False)
        self.spin_calib_dbfs.blockSignals(False)
        self.update_estimated_hl_display()
        
    def on_known_1k_changed(self, val: int):
        ear = self.get_calib_ear()
        self.known_hl_1000[ear] = float(val)
        self.update_estimated_hl_display()
        
    def on_calib_slider_changed(self, val: int):
        self.spin_calib_dbfs.blockSignals(True)
        self.spin_calib_dbfs.setValue(val)
        self.spin_calib_dbfs.blockSignals(False)
        
    def on_calib_spin_changed(self, val: int):
        self.slider_calib_1k.blockSignals(True)
        self.slider_calib_1k.setValue(val)
        self.slider_calib_1k.blockSignals(False)
        
    def play_calib_1k(self):
        ear = self.get_calib_ear()
        level_db = float(self.slider_calib_1k.value())
        audio = generate_evaluation_tone(
            frequency_hz=1000.0,
            duration_s=1.5,
            ear=ear,
            level_db=level_db,
            fs=44100
        )
        AudioPlayer.get_instance().play(audio, fs=44100, loop=False, volume=1.0)
        
    def set_calibration_reference(self):
        ear = self.get_calib_ear()
        dbfs_val = float(self.slider_calib_1k.value())
        hl_val = float(self.spin_known_1k.value())
        
        self.calib_dbfs[ear] = dbfs_val
        self.known_hl_1000[ear] = hl_val
        self.calibrated[ear] = True
        
        self.lbl_calib_status.setText(
            f"Calibrado Oído L: {int(self.calib_dbfs['left'])} dBFS = {int(self.known_hl_1000['left'])} dB HL | "
            f"Oído R: {int(self.calib_dbfs['right'])} dBFS = {int(self.known_hl_1000['right'])} dB HL"
        )
        self.update_estimated_hl_display()
        
    def on_test_slider_changed(self, val: int):
        self.spin_test_vol.blockSignals(True)
        self.spin_test_vol.setValue(val)
        self.spin_test_vol.blockSignals(False)
        self.update_estimated_hl_display()
        
    def on_test_spin_changed(self, val: int):
        self.slider_test_vol.blockSignals(True)
        self.slider_test_vol.setValue(val)
        self.slider_test_vol.blockSignals(False)
        self.update_estimated_hl_display()
        
    def update_estimated_hl_display(self):
        ear = self.get_test_ear()
        freq = self.combo_freq.currentData()
        test_dbfs = float(self.slider_test_vol.value())
        
        calib_dbfs = self.calib_dbfs[ear]
        known_hl = self.known_hl_1000[ear]
        
        est_hl = calculate_estimated_hl(
            test_freq=freq,
            test_level_dbfs=test_dbfs,
            calib_1000hz_dbfs=calib_dbfs,
            known_hl_1000hz=known_hl
        )
        
        color = "#3498db" if ear == "left" else "#e74c3c"
        self.lbl_hl_calc.setStyleSheet(
            f"QLabel {{ font-size: 14px; font-weight: bold; color: {color}; background-color: #2c3e50; padding: 4px 10px; border-radius: 4px; }}"
        )
        self.lbl_hl_calc.setText(f"{int(est_hl)} dB HL ({ear.upper()})")
        
    def play_test_tone(self):
        ear = self.get_test_ear()
        freq = float(self.combo_freq.currentData())
        level_db = float(self.slider_test_vol.value())
        
        audio = generate_evaluation_tone(
            frequency_hz=freq,
            duration_s=1.5,
            ear=ear,
            level_db=level_db,
            fs=44100
        )
        AudioPlayer.get_instance().play(audio, fs=44100, loop=False, volume=1.0)
        
    def transfer_value_to_table(self):
        """Transfiere el umbral calculado directamente a la tabla de audiometría."""
        ear = self.get_test_ear()
        freq = int(self.combo_freq.currentData())
        test_dbfs = float(self.slider_test_vol.value())
        
        est_hl = calculate_estimated_hl(
            test_freq=freq,
            test_level_dbfs=test_dbfs,
            calib_1000hz_dbfs=self.calib_dbfs[ear],
            known_hl_1000hz=self.known_hl_1000[ear]
        )
        
        # Emitir señal para que la tabla y el gráfico se actualicen inmediatamente
        self.threshold_assigned.emit(ear, freq, est_hl)
        
        # Efecto visual de confirmación en el botón
        orig_text = self.btn_transfer.text()
        self.btn_transfer.setText(f"✓ ¡Asignado {int(est_hl)} dB HL a {freq} Hz!")
        self.btn_transfer.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; }")
        
        # Avanzar al siguiente índice de frecuencia automáticamente si no es la última
        curr_idx = self.combo_freq.currentIndex()
        if curr_idx < self.combo_freq.count() - 1:
            self.combo_freq.setCurrentIndex(curr_idx + 1)
