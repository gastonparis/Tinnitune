#!/usr/bin/env python3
"""
Punto de entrada de la aplicación de escritorio para tratamiento de tinnitus.
"""

import sys
import os

# Asegurar importación de módulos locales
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Tinnitus Sound Generator")
    app.setOrganizationName("CSIC Sound Therapy")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
