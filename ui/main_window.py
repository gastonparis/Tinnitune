"""
Ventana Principal de la Aplicación de Escritorio para Tratamiento de Tinnitus.
Integra evaluación audiométrica, visualización clínica, preescucha y exportación móvil.
"""

import json
import os
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QFileDialog, QMessageBox, QTabWidget, QLabel, QComboBox
)
from PySide6.QtMultimedia import QMediaDevices
from core.audiometry import AudiogramData, STANDARD_FREQUENCIES
from core.audio_player import AudioPlayer
from ui.audiometry_table import AudiometryTableWidget
from ui.audiogram_canvas import AudiogramCanvas
from ui.tone_tester_widget import ToneTesterWidget
from ui.treatment_panel import TreatmentPanelWidget


DARK_THEME_QSS = """
QMainWindow {
    background-color: #1e1e1e;
    color: #f0f0f0;
}
QWidget {
    background-color: #1e1e1e;
    color: #f0f0f0;
    font-family: 'Segoe UI', 'Ubuntu', 'Helvetica Neue', sans-serif;
    font-size: 11px;
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #3d3d3d;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #3498db;
}
QTableWidget {
    background-color: #252525;
    alternate-background-color: #2c2c2c;
    gridline-color: #3d3d3d;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
}
QHeaderView::section {
    background-color: #333333;
    color: #ffffff;
    font-weight: bold;
    padding: 4px;
    border: 1px solid #3d3d3d;
}
QSpinBox, QComboBox {
    background-color: #2b2b2b;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    padding: 3px;
    color: #ffffff;
}
QSpinBox:focus, QComboBox:focus {
    border: 1px solid #3498db;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #3a3a3a;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #3498db;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    width: 14px;
    margin-top: -4px;
    margin-bottom: -4px;
    border-radius: 7px;
}
QProgressBar {
    border: 1px solid #444444;
    border-radius: 4px;
    text-align: center;
    background-color: #2a2a2a;
}
QProgressBar::chunk {
    background-color: #8e44ad;
}
QPushButton {
    background-color: #3a3a3a;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 5px 10px;
    color: #f0f0f0;
}
QPushButton:hover {
    background-color: #4a4a4a;
}
QMenuBar {
    background-color: #2b2b2b;
    border-bottom: 1px solid #3d3d3d;
}
QMenuBar::item:selected {
    background-color: #3d3d3d;
}
QMenu {
    background-color: #2b2b2b;
    border: 1px solid #444444;
}
QMenu::item:selected {
    background-color: #3498db;
}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Generador de Sonido Terapéutico para Tinnitus (Protocolo CSIC / Cobo et al.)")
        self.resize(1150, 750)
        self.setStyleSheet(DARK_THEME_QSS)
        
        self.audiogram = AudiogramData()
        self.init_ui()
        self.create_menu()
        
    def init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        splitter = QSplitter(Qt.Horizontal)
        
        # --- PANEL IZQUIERDO: Entrada de Audiometría y Prueba de Tonos ---
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.table_widget = AudiometryTableWidget()
        self.table_widget.audiogram_changed.connect(self.on_audiogram_updated)
        left_layout.addWidget(self.table_widget)
        
        self.tester_widget = ToneTesterWidget()
        self.tester_widget.threshold_assigned.connect(self.table_widget.set_single_threshold)
        left_layout.addWidget(self.tester_widget)
        
        splitter.addWidget(left_container)
        
        # --- PANEL DERECHO: Visualización del Audiograma y Generador Terapéutico ---
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.canvas = AudiogramCanvas()
        right_layout.addWidget(self.canvas, stretch=3)
        
        self.treatment_panel = TreatmentPanelWidget()
        right_layout.addWidget(self.treatment_panel, stretch=4)
        
        splitter.addWidget(right_container)
        splitter.setSizes([480, 670])
        
        main_layout.addWidget(splitter)
        
        # Cargar valores iniciales
        self.table_widget.load_preset_high_freq_loss()
        
        # Configurar barra de estado con selector de dispositivo de audio
        self.setup_audio_device_bar()
        
    def setup_audio_device_bar(self):
        status_bar = self.statusBar()
        lbl_icon = QLabel("🔊 <b>Salida de Audio:</b>")
        lbl_icon.setStyleSheet("color: #3498db; margin-left: 5px;")
        status_bar.addWidget(lbl_icon)
        
        self.combo_audio_dev = QComboBox()
        self.combo_audio_dev.setMinimumWidth(320)
        self.combo_audio_dev.setStyleSheet("QComboBox { padding: 2px 8px; font-weight: bold; }")
        
        devices = AudioPlayer.get_available_devices()
        default_dev = QMediaDevices.defaultAudioOutput()
        
        for i, d in enumerate(devices):
            desc = d.description()
            if d.id() == default_dev.id():
                desc += " [Predeterminado del Sistema]"
            self.combo_audio_dev.addItem(desc, d)
            if d.id() == default_dev.id():
                self.combo_audio_dev.setCurrentIndex(i)
                
        self.combo_audio_dev.currentIndexChanged.connect(self.on_audio_device_changed)
        status_bar.addPermanentWidget(self.combo_audio_dev)
        
    def on_audio_device_changed(self, idx: int):
        dev = self.combo_audio_dev.currentData()
        if dev:
            AudioPlayer.get_instance().set_output_device(dev)
        
    def on_audiogram_updated(self, audiogram: AudiogramData):
        self.audiogram = audiogram
        self.canvas.update_audiogram(audiogram)
        self.treatment_panel.set_audiogram(audiogram)
        
    def create_menu(self):
        menubar = self.menuBar()
        
        # Menú Archivo
        file_menu = menubar.addMenu("&Archivo")
        
        act_load = QAction("Cargar Audiometría (JSON)...", self)
        act_load.triggered.connect(self.load_audiogram_file)
        file_menu.addAction(act_load)
        
        act_save = QAction("Guardar Audiometría (JSON)...", self)
        act_save.triggered.connect(self.save_audiogram_file)
        file_menu.addAction(act_save)
        
        file_menu.addSeparator()
        
        act_exit = QAction("&Salir", self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)
        
        # Menú Ayuda
        help_menu = menubar.addMenu("A&yuda")
        
        act_info = QAction("Sobre el Tratamiento (Cobo et al. 2022)", self)
        act_info.triggered.connect(self.show_treatment_info)
        help_menu.addAction(act_info)
        
    def load_audiogram_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Cargar Audiometría",
            "",
            "Archivos JSON (*.json)"
        )
        if not filepath:
            return
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            left_dict = {int(k): float(v) for k, v in data.get("left", {}).items()}
            right_dict = {int(k): float(v) for k, v in data.get("right", {}).items()}
            self.table_widget.set_audiogram_values(left_dict, right_dict)
            QMessageBox.information(self, "Audiometría Cargada", f"Se cargaron los datos de:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error al Cargar", f"No se pudo leer el archivo:\n{e}")
            
    def save_audiogram_file(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Audiometría",
            "audiometria_paciente.json",
            "Archivos JSON (*.json)"
        )
        if not filepath:
            return
            
        try:
            data = {
                "left": self.audiogram.left_ear,
                "right": self.audiogram.right_ear
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            QMessageBox.information(self, "Guardado Exitoso", f"Audiometría guardada en:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error al Guardar", f"No se pudo guardar el archivo:\n{e}")
            
    def show_treatment_info(self):
        info_text = (
            "<h3>Protocolo Clínico de Terapia Sonora (Cobo, Cuesta et al., CSIC)</h3>"
            "<p><b>Artículo de Referencia:</b><br>"
            "<i>Efficacy of Sound Therapy for Tinnitus Using an Enriched Acoustic Environment "
            "with Hearing-Loss Matched Broadband Noise</i> (Brain Sci. 2022, 12, 82).</p>"
            "<p><b>Pautas de Uso:</b></p>"
            "<ul>"
            "<li><b>Dosis diaria:</b> Escuchar el archivo de audio generado durante <b>1 hora al día</b> de forma continua o en dos sesiones de 30 minutos.</li>"
            "<li><b>Duración recomendada:</b> Mantener la terapia durante al menos <b>4 meses</b> continuos para inducir habituación y reorganización tonotópica cortical.</li>"
            "<li><b>Calibración de volumen (Punto de Mezcla):</b> Escuchar con auriculares de diadema estéreo de buena calidad. "
            "Ajustar el volumen de modo que el ruido empiece a mezclarse con su acúfeno, pero <i>sin taparlo ni enmascararlo por completo</i>.</li>"
            "</ul>"
        )
        QMessageBox.about(self, "Información Médica del Tratamiento", info_text)
