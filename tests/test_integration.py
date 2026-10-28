"""
Prueba de integración de la interfaz gráfica y flujo completo de la aplicación.
Verifica:
1. Inicialización de widgets (tabla, canvas, tester, treatment panel).
2. Sincronización entre tabla de audiometría y gráfico.
3. Funcionamiento del worker de generación y exportación a MP3.
"""

import os
import sys
import tempfile
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication
from ui.main_window import MainWindow
from ui.treatment_panel import AudioGenerationWorker
from core.audiometry import AudiogramData
import soundfile as sf


def test_ui_and_worker_integration():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance() or QApplication(sys.argv)
    
    print("-> 1. Instanciando MainWindow...")
    win = MainWindow()
    win.show()
    app.processEvents()
    
    # 2. Modificar un valor en la tabla y verificar que la señal actualice el audiograma
    print("-> 2. Verificando sincronización de tabla y audiograma...")
    win.table_widget.on_value_changed("left", 4000, 75)
    app.processEvents()
    assert win.audiogram.get_threshold("left", 4000) == 75.0, "El audiograma no se actualizó al cambiar la tabla."
    
    # 3. Probar Worker de generación en segundo plano (1 minuto = 60 seg de prueba)
    print("-> 3. Verificando AudioGenerationWorker en segundo plano...")
    tmp_dir = tempfile.mkdtemp()
    out_mp3 = os.path.join(tmp_dir, "test_1min.mp3")
    
    worker = AudioGenerationWorker(
        audiogram=win.audiogram,
        stimulus_type="broadband",
        duration_minutes=1,  # 1 minuto
        output_filepath=out_mp3,
        format_type="mp3"
    )
    
    results = {"success": False, "path": "", "progress_vals": []}
    
    def on_prog(p):
        results["progress_vals"].append(p)
        
    def on_success(p):
        results["success"] = True
        results["path"] = p
        
    def on_error(err):
        print(f"Error en worker: {err}")
        
    worker.progress_changed.connect(on_prog)
    worker.finished_success.connect(on_success)
    worker.finished_error.connect(on_error)
    
    worker.start()
    
    # Esperar a que el worker termine procesando eventos de Qt
    start_t = time.time()
    while worker.isRunning() and (time.time() - start_t < 30):
        app.processEvents()
        time.sleep(0.05)
        
    worker.wait()
    app.processEvents()
    
    if not results["success"] and "error" in results:
        print("Error reportado:", results["error"])
        
    assert results["success"], "El worker no completó la generación con éxito."
    assert os.path.exists(out_mp3), f"El archivo MP3 no existe en {out_mp3}"
    assert len(results["progress_vals"]) > 0, "No se emitieron señales de progreso."
    
    file_size_kb = os.path.getsize(out_mp3) / 1024
    print(f"   [OK] Archivo MP3 de 1 minuto generado con éxito ({file_size_kb:.1f} KB).")
    print(f"   [OK] Señales de progreso recibidas: {len(results['progress_vals'])} eventos (último: {results['progress_vals'][-1]}%).")
    
    # Limpieza
    try:
        os.remove(out_mp3)
        os.rmdir(tmp_dir)
    except OSError:
        pass


if __name__ == "__main__":
    print("=== INICIANDO PRUEBAS DE INTEGRACIÓN (UI & DSP WORKER) ===")
    test_ui_and_worker_integration()
    print("=== TODAS LAS PRUEBAS DE INTEGRACIÓN FUERON EXITOSAS ===")
