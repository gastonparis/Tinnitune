"""
Prueba de calibración a 1000 Hz y transferencia automática a la audiometría.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.audiometry import calculate_estimated_hl, ISO_RETSPL_DIFF_1000HZ
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow


def test_iso_retspl_calculation():
    print("-> 1. Probando cálculo matemático de dB HL con compensación ISO 389...")
    
    # Supongamos que a 1000 Hz el umbral clínico del paciente es 15 dB HL
    # Y en la PC apenas lo oye a -45 dBFS
    known_hl_1k = 15.0
    calib_dbfs = -45.0
    
    # 1. En 1000 Hz al mismo nivel (-45 dBFS), debe dar exactamente 15 dB HL
    hl_1k = calculate_estimated_hl(1000, -45.0, calib_dbfs, known_hl_1k)
    assert hl_1k == 15.0, f"Error en 1000 Hz: {hl_1k} != 15.0"
    
    # 2. En 4000 Hz (sensibilidad natural similar o ligeramente mayor a 1k):
    # Si necesita subir 20 dB (de -45 a -25 dBFS) para escucharlo:
    # RetSPL diff a 4k es +2.5 dB
    # estimated = 15 + (-25 - (-45)) - 2.5 = 15 + 20 - 2.5 = 32.5 -> redondeado a 35 o 30 dB HL
    hl_4k = calculate_estimated_hl(4000, -25.0, calib_dbfs, known_hl_1k)
    assert hl_4k == 30.0 or hl_4k == 35.0, f"Error en 4000 Hz: {hl_4k}"
    
    # 3. En 125 Hz (el oído necesita naturalmente mucha más presión, +38 dB):
    # Si lo oye a -7 dBFS (subió 38 dB respecto a 1k):
    # estimated = 15 + (-7 - (-45)) - 38 = 15 + 38 - 38 = 15 dB HL
    hl_125 = calculate_estimated_hl(125, -7.0, calib_dbfs, known_hl_1k)
    assert hl_125 == 15.0, f"Error en 125 Hz: {hl_125} != 15.0"
    print("   [OK] Cálculo de dB HL y compensación ISO 389 verificado.")


def test_widget_transfer_to_audiogram():
    print("-> 2. Probando transferencia interactiva desde ToneTesterWidget a la tabla...")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance() or QApplication(sys.argv)
    
    win = MainWindow()
    win.show()
    app.processEvents()
    
    # Configurar calibración en el widget: Oído Izquierdo, 1000 Hz = 20 dB HL a -40 dBFS
    win.tester_widget.rb_calib_l.setChecked(True)
    win.tester_widget.spin_known_1k.setValue(20)
    win.tester_widget.slider_calib_1k.setValue(-40)
    win.tester_widget.set_calibration_reference()
    
    # Evaluar 6000 Hz en oído izquierdo a -10 dBFS
    # Buscar índice de 6000 Hz
    idx_6k = win.tester_widget.combo_freq.findData(6000)
    win.tester_widget.combo_freq.setCurrentIndex(idx_6k)
    win.tester_widget.rb_test_l.setChecked(True)
    win.tester_widget.slider_test_vol.setValue(-10)
    
    # Hacer clic en "Transferir Valor"
    win.tester_widget.transfer_value_to_table()
    app.processEvents()
    
    # Verificar que la tabla de audiometría y el modelo se hayan actualizado a 6000 Hz
    val_table = win.audiogram.get_threshold("left", 6000)
    spin_val = win.table_widget.spinboxes_left[6000].value()
    
    assert val_table == spin_val, f"Desajuste entre audiograma ({val_table}) y tabla ({spin_val})"
    print(f"   [OK] Valor transferido exitosamente a 6000 Hz Oído Izquierdo: {val_table} dB HL.")


if __name__ == "__main__":
    print("=== INICIANDO PRUEBAS DE CALIBRACIÓN Y TRASPASO AUTOMÁTICO ===")
    test_iso_retspl_calculation()
    test_widget_transfer_to_audiogram()
    print("=== TODAS LAS PRUEBAS DE CALIBRACIÓN FUERON SUPERADAS EXITOSAMENTE ===")
