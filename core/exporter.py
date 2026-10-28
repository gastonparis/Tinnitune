"""
Módulo para exportación de audio en formatos WAV y MP3 con metadatos.
Optimizado para transferencia a teléfonos móviles y reproductores portátiles.
"""

import os
import subprocess
import numpy as np
import soundfile as sf


def export_audio(
    audio_data: np.ndarray,
    output_path: str,
    fs: int = 44100,
    format_type: str = "mp3",  # "mp3" o "wav"
    mp3_bitrate: str = "320k",
    title: str = "Terapia Tinnitus EAE",
    artist: str = "Tinnitus Sound Generator (Cobo et al.)"
) -> str:
    """
    Exporta el buffer estéreo a un archivo WAV o MP3.
    Retorna la ruta absoluta del archivo generado.
    """
    output_path = os.path.abspath(output_path)
    base_dir = os.path.dirname(output_path)
    os.makedirs(base_dir, exist_ok=True)
    
    fmt = format_type.lower()
    if fmt == "wav":
        if not output_path.lower().endswith(".wav"):
            output_path += ".wav"
        # Exportar en PCM 16-bit estándar compatible con cualquier dispositivo
        sf.write(output_path, audio_data, fs, subtype="PCM_16")
        return output_path
        
    elif fmt == "mp3":
        if not output_path.lower().endswith(".mp3"):
            output_path += ".mp3"
            
        # Exportar primero a un archivo WAV temporal en la misma carpeta
        temp_wav = output_path + ".temp.wav"
        sf.write(temp_wav, audio_data, fs, subtype="PCM_16")
        
        try:
            # Codificar con ffmpeg en CBR de alta calidad con metadatos ID3
            cmd = [
                "ffmpeg",
                "-y",  # Sobrescribir sin preguntar
                "-i", temp_wav,
                "-codec:a", "libmp3lame",
                "-b:a", mp3_bitrate,
                "-metadata", f"title={title}",
                "-metadata", f"artist={artist}",
                "-metadata", "comment=Terapia de Entorno Acustico Enriquecido para Tinnitus",
                output_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return output_path
        finally:
            if os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except OSError:
                    pass
    else:
        raise ValueError(f"Formato no soportado: {format_type}. Use 'wav' o 'mp3'.")
