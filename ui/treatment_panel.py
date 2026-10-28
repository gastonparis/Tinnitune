"""
Panel de configuración del tratamiento, preescucha del Mixing Point y exportación móvil.
Ejecuta la síntesis de audios largos en segundo plano mediante un QThread para evitar bloqueos.
"""

import os
import subprocess
import numpy as np
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QSlider, QGroupBox, QRadioButton, QButtonGroup,
    QProgressBar, QFileDialog, QMessageBox
)
from core.audiometry import AudiogramData
from core.dsp import (
    generate_continuous_broadband_noise,
    generate_sequential_eae
)
from core.exporter import export_audio
from core.audio_player import AudioPlayer


class AudioGenerationWorker(QThread):
    progress_changed = Signal(int)
    finished_success = Signal(str)
    finished_error = Signal(str)
    
    def __init__(
        self,
        audiogram: AudiogramData,
        stimulus_type: str,
        duration_minutes: int,
        output_filepath: str,
        format_type: str,
        parent=None
    ):
        super().__init__(parent)
        self.audiogram = audiogram
        self.stimulus_type = stimulus_type
        self.duration_sec = duration_minutes * 60
        self.output_filepath = output_filepath
        self.format_type = format_type
        
    def run(self):
        try:
            def on_progress(frac: float):
                percent = int(frac * 85)  # 0 a 85% síntesis
                self.progress_changed.emit(percent)
                
            # 1. Generación DSP
            if self.stimulus_type == "broadband":
                audio = generate_continuous_broadband_noise(
                    self.audiogram,
                    duration_sec=self.duration_sec,
                    fs=44100,
                    progress_callback=on_progress
                )
            else:
                mode = self.stimulus_type.replace("eae_", "")
                audio = generate_sequential_eae(
                    self.audiogram,
                    duration_sec=self.duration_sec,
                    stimulus_type=mode,
                    fs=44100,
                    progress_callback=on_progress
                )
                
            self.progress_changed.emit(90)  # 90% codificación
            
            # 2. Exportación a archivo
            final_path = export_audio(
                audio_data=audio,
                output_path=self.output_filepath,
                fs=44100,
                format_type=self.format_type,
                mp3_bitrate="320k",
                title="Terapia Tinnitus EAE",
                artist="Tinnitus Sound Generator (CSIC Protocol)"
            )
            
            self.progress_changed.emit(100)
            self.finished_success.emit(final_path)
        except Exception as e:
            self.finished_error.emit(str(e))


class TreatmentPanelWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.audiogram = AudiogramData()
        self.preview_audio = None
        self.is_previewing = False
        self.worker = None
        self.init_ui()
        
    def set_audiogram(self, audiogram: AudiogramData):
        self.audiogram = audiogram
        # Si estaba en preescucha, regenerar el buffer de preescucha
        if self.is_previewing:
            self.start_preview()
            
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 1. Configuración del Estímulo
        config_group = QGroupBox("1. Configuración del Estímulo Terapéutico")
        cfg_layout = QVBoxLayout(config_group)
        
        # Tipo de sonido
        t_layout = QHBoxLayout()
        t_layout.addWidget(QLabel("Tipo de Ruido:"))
        self.combo_type = QComboBox()
        self.combo_type.addItem("Ruido de Banda Ancha Coloreado (Principal estudio)", "broadband")
        self.combo_type.addItem("Secuencial EAE - Tone Burst (Suave / Hiperacusia)", "eae_burst")
        self.combo_type.addItem("Secuencial EAE - Tone Pip (Reorganización tonotópica)", "eae_pip")
        self.combo_type.addItem("Secuencial EAE - Gammatone (Filtro coclear)", "eae_gamma")
        t_layout.addWidget(self.combo_type)
        cfg_layout.addLayout(t_layout)
        
        # Duración de la sesión diaria
        dur_layout = QHBoxLayout()
        dur_layout.addWidget(QLabel("Duración:"))
        self.combo_dur = QComboBox()
        self.combo_dur.addItem("60 minutos (Dosis estándar del estudio: 1h/día)", 60)
        self.combo_dur.addItem("30 minutos", 30)
        self.combo_dur.addItem("15 minutos", 15)
        self.combo_dur.addItem("1 minuto (Prueba rápida)", 1)
        dur_layout.addWidget(self.combo_dur)
        cfg_layout.addLayout(dur_layout)
        
        main_layout.addWidget(config_group)
        
        # 2. Preescucha y Calibración del Punto de Mezcla (Mixing Point)
        preview_group = QGroupBox("2. Preescucha y Calibración del 'Mixing Point'")
        prev_layout = QVBoxLayout(preview_group)
        
        lbl_info = QLabel(
            "<b>Instrucción del Dr. Jastreboff / CSIC:</b><br>"
            "Póngase los auriculares estéreo y ajuste el volumen de modo que el ruido "
            "empiece a mezclarse con su tinnitus <i>sin taparlo por completo</i> (punto de mezcla)."
        )
        lbl_info.setStyleSheet("color: #ecf0f1; background-color: #34495e; padding: 8px; border-radius: 4px;")
        lbl_info.setWordWrap(True)
        prev_layout.addWidget(lbl_info)
        
        # Controles de preescucha
        btn_prev_layout = QHBoxLayout()
        self.btn_preview = QPushButton("▶ Iniciar Preescucha en Auriculares")
        self.btn_preview.setStyleSheet(
            "QPushButton { background-color: #2980b9; color: white; font-weight: bold; padding: 7px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #3498db; }"
        )
        self.btn_preview.clicked.connect(self.toggle_preview)
        btn_prev_layout.addWidget(self.btn_preview)
        prev_layout.addLayout(btn_prev_layout)
        
        vol_layout = QHBoxLayout()
        vol_layout.addWidget(QLabel("Volumen Master:"))
        self.slider_vol = QSlider(Qt.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(65)
        self.lbl_vol_val = QLabel("65%")
        self.slider_vol.valueChanged.connect(self.on_volume_changed)
        vol_layout.addWidget(self.slider_vol)
        vol_layout.addWidget(self.lbl_vol_val)
        prev_layout.addLayout(vol_layout)
        
        main_layout.addWidget(preview_group)
        
        # 3. Exportación para Teléfono Celular
        export_group = QGroupBox("3. Grabar y Exportar para Celular")
        exp_layout = QVBoxLayout(export_group)
        
        fmt_layout = QHBoxLayout()
        fmt_layout.addWidget(QLabel("Formato:"))
        self.rb_mp3 = QRadioButton("MP3 (320 kbps - Recomendado para celular)")
        self.rb_wav = QRadioButton("WAV (Calidad estudio sin compresión)")
        self.rb_mp3.setChecked(True)
        
        self.fmt_group = QButtonGroup(self)
        self.fmt_group.addButton(self.rb_mp3)
        self.fmt_group.addButton(self.rb_wav)
        
        fmt_layout.addWidget(self.rb_mp3)
        fmt_layout.addWidget(self.rb_wav)
        exp_layout.addLayout(fmt_layout)
        
        self.btn_export = QPushButton("💾 Generar y Guardar Archivo de Audio")
        self.btn_export.setStyleSheet(
            "QPushButton { background-color: #8e44ad; color: white; font-size: 13px; font-weight: bold; padding: 10px; border-radius: 5px; }"
            "QPushButton:hover { background-color: #9b59b6; }"
        )
        self.btn_export.clicked.connect(self.start_export)
        exp_layout.addWidget(self.btn_export)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        exp_layout.addWidget(self.progress_bar)
        
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        exp_layout.addWidget(self.lbl_status)
        
        main_layout.addWidget(export_group)
        main_layout.addStretch()
        
    def on_volume_changed(self, val: int):
        self.lbl_vol_val.setText(f"{val}%")
        AudioPlayer.get_instance().set_volume(val / 100.0)
        
    def toggle_preview(self):
        if self.is_previewing:
            self.stop_preview()
        else:
            self.start_preview()
            
    def start_preview(self):
        self.stop_preview()
        stim_type = self.combo_type.currentData()
        vol_factor = float(self.slider_vol.value()) / 100.0
        
        # Generar un buffer de preescucha de 10 segundos
        if stim_type == "broadband":
            audio = generate_continuous_broadband_noise(self.audiogram, duration_sec=10.0, fs=44100)
        else:
            mode = stim_type.replace("eae_", "")
            audio = generate_sequential_eae(self.audiogram, duration_sec=10.0, stimulus_type=mode, fs=44100)
            
        self.preview_audio = audio
        AudioPlayer.get_instance().play(self.preview_audio, fs=44100, loop=True, volume=vol_factor)
        self.is_previewing = True
        self.btn_preview.setText("⏹ Detener Preescucha")
        self.btn_preview.setStyleSheet(
            "QPushButton { background-color: #c0392b; color: white; font-weight: bold; padding: 7px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #e74c3c; }"
        )
        
    def stop_preview(self):
        AudioPlayer.get_instance().stop()
        self.is_previewing = False
        self.btn_preview.setText("▶ Iniciar Preescucha en Auriculares")
        self.btn_preview.setStyleSheet(
            "QPushButton { background-color: #2980b9; color: white; font-weight: bold; padding: 7px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #3498db; }"
        )
        
    def start_export(self):
        self.stop_preview()
        
        dur_min = self.combo_dur.currentData()
        stim_type = self.combo_type.currentData()
        fmt = "mp3" if self.rb_mp3.isChecked() else "wav"
        
        default_filename = f"Tratamiento_Tinnitus_{stim_type}_{dur_min}min.{fmt}"
        default_dir = os.path.expanduser("~/Music")
        if not os.path.exists(default_dir):
            default_dir = os.path.expanduser("~")
            
        default_path = os.path.join(default_dir, default_filename)
        
        file_filter = "Archivos MP3 (*.mp3)" if fmt == "mp3" else "Archivos WAV (*.wav)"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Archivo de Audio Terapéutico",
            default_path,
            file_filter
        )
        
        if not save_path:
            return
            
        # Preparar UI para exportación
        self.btn_export.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText(f"Sintetizando {dur_min} minutos de tratamiento...")
        
        # Lanzar proceso en hilo secundario
        self.worker = AudioGenerationWorker(
            audiogram=self.audiogram,
            stimulus_type=stim_type,
            duration_minutes=dur_min,
            output_filepath=save_path,
            format_type=fmt
        )
        self.worker.progress_changed.connect(self.progress_bar.setValue)
        self.worker.finished_success.connect(self.on_export_success)
        self.worker.finished_error.connect(self.on_export_error)
        self.worker.start()
        
    def on_export_success(self, filepath: str):
        self.btn_export.setEnabled(True)
        self.progress_bar.setValue(100)
        self.lbl_status.setText("¡Archivo generado con éxito!")
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Generación Completada")
        msg.setText(f"El archivo terapéutico se guardó exitosamente:\n\n{filepath}")
        msg.setInformativeText("Ya puede transferirlo a su teléfono celular o reproductor portátil.")
        
        btn_open_folder = msg.addButton("Abrir Carpeta Contenedora", QMessageBox.ActionRole)
        msg.addButton(QMessageBox.Ok)
        msg.exec()
        
        if msg.clickedButton() == btn_open_folder:
            folder = os.path.dirname(filepath)
            # Abrir administrador de archivos según OS
            try:
                subprocess.run(["xdg-open", folder])
            except Exception:
                pass
                
    def on_export_error(self, err_msg: str):
        self.btn_export.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.lbl_status.setText("Error en la generación.")
        QMessageBox.critical(self, "Error al Exportar", f"Ocurrió un error al generar el archivo:\n\n{err_msg}")
