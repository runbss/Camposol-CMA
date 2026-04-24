# CMA

Bot de automatización para consultar y descargar documentos de embarque (Bill of Lading) desde el portal de CMA-CGM.

---

## Estructura del proyecto

```
cma-bot/
├── src/
│   ├── bot.py        # Lógica del bot (navegación, login, búsqueda, descarga)
│   └── config.py     # Configuración centralizada (credenciales, URLs, rutas)
├── .env.example      # Plantilla de credenciales (copiar a .env)
├── .gitignore
├── main.py           # Punto de entrada
├── README.md
└── requirements.txt
```

---

## Requisitos

- Python 3.9+
- Google Chrome / Chromium instalado

---

## Instalación

**1. Clonar el repositorio**
```bash
git clone https://github.com/tu-usuario/cma-bot.git
cd cma-bot
```

**2. Crear entorno virtual e instalar dependencias**
```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux / Mac

pip install -r requirements.txt
playwright install chromium
```

**3. Configurar credenciales**
```bash
copy .env.example .env       # Windows
# cp .env.example .env       # Linux / Mac
```

Editar `.env` con tus credenciales reales:
```env
USER_CMA=tu_usuario@empresa.com
PASS_CMA=tu_contraseña
```

> ⚠️ El archivo `.env` está en `.gitignore` y **nunca se sube al repositorio**.

---

## Uso

```bash
# Consulta básica (con ventana visible)
python main.py --booking CMAU1234567

# Modo silencioso (sin ventana)
python main.py --booking CMAU1234567 --oculto

# Modo rápido (sin delays)
python main.py --booking CMAU1234567 --rapido

# Combinado
python main.py --booking CMAU1234567 --oculto --rapido
```

---

## Flujo del bot

```
Inicio
  │
  ▼
Navegar a cma-cgm.com/ebusiness/document
  │
  ├─► ¿Captcha?       → Pausa para resolución manual
  ├─► ¿Login?         → Ingresa credenciales automáticamente
  └─► ¿Sesión activa? → Continúa directamente
  │
  ▼
Buscar número de booking en el panel
  │
  ▼
¿Estado "Disponible"?
  ├─► SÍ → Descarga el PDF en C:\DocumentosDescagadosTT\
  └─► NO → Informa que el documento no está listo
```

---

## Resultados posibles

| Mensaje en consola | Significado |
|---|---|
| `RESULTADO: OK (Status 200)` | PDF descargado exitosamente |
| `RESULTADO: NO SE PUDO DESCARGAR` | Se encontró el doc pero falló la descarga |
| `RESULTADO: NO SE ENCONTRO ADJUNTO (Status 404/503)` | Doc no disponible o en revisión |

---

## Notas

- Los PDFs se guardan en `C:\DocumentosDescagadosTT\` con el nombre `BillOfLading-{booking}.pdf`.
- Si aparece un captcha, el bot pausa y te pide resolverlo manualmente en el navegador.
- Las credenciales se leen desde el archivo `.env` usando `python-dotenv`.
