#!/bin/bash
# Activar entorno virtual
source .venv/Scripts/activate

# Ejecutar el bot con el argumento ingresado
if [ -z "$1" ]; then
    echo "Por favor, ingresa el número de booking."
    echo "Uso: ./run.sh [NUMERO_DE_BOOKING] [--oculto] [--rapido]"
    echo "Ejemplo: ./run.sh LMM0563939"
    exit 1
fi

python main.py --booking "$@"
