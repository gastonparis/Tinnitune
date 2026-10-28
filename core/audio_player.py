"""
Módulo de reproducción de audio nativo mediante PySide6 QtMultimedia (QAudioSink).
Conecta directamente con el servidor de sonido del sistema (PipeWire / PulseAudio en Linux,
WASAPI en Windows, CoreAudio en macOS) garantizando salida inmediata a los auriculares analógicos.
"""

from typing import List, Optional
import numpy as np
from PySide6.QtCore import QIODevice
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices, QAudioDevice


class AudioStreamDevice(QIODevice):
    """
    Dispositivo QIODevice en memoria para streaming continuo y en bucle hacia QAudioSink.
    """
    def __init__(self, audio_data: np.ndarray, loop: bool = False, parent=None):
        super().__init__(parent)
        self.loop = loop
        self.position = 0
        
        # Asegurar formato estéreo float32
        if audio_data.ndim == 1:
            audio_data = np.column_stack((audio_data, audio_data))
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
            
        # Convertir a float32 estéreo para rango dinámico completo (>150 dB sin distorsión a -100 dBFS)
        scaled = np.clip(audio_data, -1.0, 1.0)
        self.raw_bytes = scaled.astype(np.float32).tobytes()
        self.open(QIODevice.ReadOnly)

    def readData(self, maxlen: int) -> bytes:
        if not self.raw_bytes:
            return b""
            
        total_len = len(self.raw_bytes)
        if self.position >= total_len:
            if self.loop:
                self.position = 0
            else:
                return b""
                
        chunk = self.raw_bytes[self.position:self.position + maxlen]
        self.position += len(chunk)
        
        # Si estamos en bucle y el chunk no llenó el buffer, envolver al inicio
        if len(chunk) < maxlen and self.loop:
            needed = maxlen - len(chunk)
            wrap_chunk = self.raw_bytes[:needed]
            self.position = len(wrap_chunk)
            chunk += wrap_chunk
            
        return bytes(chunk)

    def isSequential(self) -> bool:
        return True

    def bytesAvailable(self) -> int:
        if self.loop:
            return 65536
        if not self.raw_bytes:
            return 0
        return max(0, len(self.raw_bytes) - self.position)


class AudioPlayer:
    """
    Controlador singleton de reproducción de audio nativo con QAudioSink.
    """
    _instance: Optional["AudioPlayer"] = None
    
    def __init__(self):
        self.sink: Optional[QAudioSink] = None
        self.device: Optional[AudioStreamDevice] = None
        self.current_volume: float = 1.0
        self.selected_device: Optional[QAudioDevice] = None

    @classmethod
    def get_instance(cls) -> "AudioPlayer":
        if cls._instance is None:
            cls._instance = AudioPlayer()
        return cls._instance

    @staticmethod
    def get_available_devices() -> List[QAudioDevice]:
        """Retorna la lista de dispositivos de salida de audio del sistema."""
        return QMediaDevices.audioOutputs()

    def set_output_device(self, device: QAudioDevice) -> None:
        """Permite seleccionar manualmente el dispositivo de audio (auriculares/parlantes)."""
        self.selected_device = device
        if self.is_playing():
            # Si estaba reproduciendo, reiniciar con el nuevo dispositivo
            pass

    def play(
        self, 
        audio_data: np.ndarray, 
        fs: int = 44100, 
        loop: bool = False, 
        volume: float = 1.0
    ) -> None:
        """
        Inicia la reproducción de un array de audio con volumen y modo bucle.
        """
        self.stop()
        
        self.current_volume = max(0.0, min(1.0, volume))
        
        # Configurar formato de audio estándar de 32-bit Float
        fmt = QAudioFormat()
        fmt.setSampleRate(fs)
        fmt.setChannelCount(2)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Float)
        
        output_dev = self.selected_device or QMediaDevices.defaultAudioOutput()
        
        self.device = AudioStreamDevice(audio_data, loop=loop)
        self.sink = QAudioSink(output_dev, fmt)
        self.sink.setVolume(self.current_volume)
        self.sink.start(self.device)

    def set_volume(self, volume: float) -> None:
        """Ajusta el volumen en tiempo real (0.0 a 1.0)."""
        self.current_volume = max(0.0, min(1.0, volume))
        if self.sink is not None:
            self.sink.setVolume(self.current_volume)

    def is_playing(self) -> bool:
        """Indica si hay una reproducción activa."""
        if self.sink is not None:
            from PySide6.QtMultimedia import QAudio
            return self.sink.state() in (QAudio.State.ActiveState, QAudio.State.IdleState)
        return False

    def stop(self) -> None:
        """Detiene cualquier reproducción activa inmediatamente."""
        if self.sink is not None:
            try:
                self.sink.stop()
            except Exception:
                pass
            self.sink = None
            
        if self.device is not None:
            try:
                self.device.close()
            except Exception:
                pass
            self.device = None
