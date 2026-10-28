#!/usr/bin/env bash
# Script lanzador para la aplicación de escritorio de tratamiento de tinnitus
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "Iniciando Generador de Sonido Terapéutico para Tinnitus..."
python3 main.py "$@"
