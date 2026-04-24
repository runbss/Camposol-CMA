import argparse
import json
from src.bot import ejecutar_bot

def main():
    parser = argparse.ArgumentParser(
        description="Bot de consulta y descarga de documentos CMA-CGM",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--booking",
        type=str,
        required=True,
        help="Número de booking o referencia a consultar (ej: CMAU1234567)",
    )
    parser.add_argument(
        "--oculto",
        action="store_true",
        help="Ejecutar el bot en modo headless (sin ventana visible)",
    )
    parser.add_argument(
        "--rapido",
        action="store_true",
        help="Ejecutar sin delays entre acciones (slow_mo=0)",
    )

    args = parser.parse_args()

    visible = not args.oculto
    slow_mo = 0 if args.rapido else 500

    resultado = ejecutar_bot(booking=args.booking, visible=visible, slow_mo=slow_mo)
    
    # Imprimir un JSON estructurado al final para Power Automate
    print("\n--- INICIO JSON ---")
    print(json.dumps(resultado, indent=4))
    print("--- FIN JSON ---")


if __name__ == "__main__":
    main()
