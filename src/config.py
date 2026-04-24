import os
from dotenv import load_dotenv

load_dotenv()

# Credenciales CMA-CGM
USER_CMA = os.getenv("USER_CMA", "")
PASS_CMA = os.getenv("PASS_CMA", "")

# Configuración del navegador
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
SLOW_MO = int(os.getenv("SLOW_MO", "500"))

# URLs
BASE_URL = "https://www.cma-cgm.com/ebusiness/document"

# Rutas
OUTPUT_DIR = r"C:\DocumentosDescagadosTT"
