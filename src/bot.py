import base64
import pathlib
import time

from playwright.sync_api import sync_playwright, Page, Browser

from src.config import USER_CMA, PASS_CMA, BASE_URL, OUTPUT_DIR, HEADLESS, SLOW_MO


# ---------------------------------------------------------------------------
# Helpers de navegación
# ---------------------------------------------------------------------------

def _cerrar_popup(page: Page) -> None:
    """Cierra ventanas emergentes promocionales si aparecen."""
    try:
        close_button = page.wait_for_selector(
            'img[alt="Close"], button.popup-close-button', timeout=4000
        )
        if close_button:
            print("  [popup] Ventana emergente detectada. Cerrando...")
            close_button.click()
    except Exception:
        pass


def _manejar_captcha(page: Page) -> None:
    """
    Si CMA-CGM muestra un captcha, pausa y le pide al usuario que lo resuelva
    manualmente. Continúa cuando el usuario presiona Enter.
    """
    for frame in page.frames:
        try:
            tiene_captcha = (
                frame.query_selector('text="Nos aseguramos de que nos dirigimos a usted"')
                or frame.query_selector('text="Desliza hacia la derecha"')
            )
            if tiene_captcha:
                print("\n" + "=" * 60)
                print("  [captcha] Se detectó un desafío de verificación.")
                print("  Por favor, resuélvelo MANUALMENTE en el navegador.")
                print("  Cuando termines, vuelve aquí y presiona ENTER.")
                print("=" * 60)
                input("  >> Presiona ENTER para continuar...")
                page.wait_for_timeout(2000)
                return
        except Exception:
            pass


def _hacer_login(page: Page) -> None:
    """Rellena y envía el formulario de login de CMA-CGM."""
    print("  [login] Detectamos la página de login. Ingresando credenciales...")

    if not USER_CMA or not PASS_CMA:
        raise ValueError(
            "Las credenciales están vacías. "
            "Asegúrate de tener USER_CMA y PASS_CMA definidos en tu archivo .env"
        )

    page.fill('input[name="pf.username"], input[id="login-email"]', USER_CMA)
    page.fill('input[name="pf.pass"], input[id="login-password"]', PASS_CMA)

    print("  [login] Haciendo click en el botón de login...")
    page.click('button:has-text("Log in"), button[type="submit"]')

    print("  [login] Esperando retorno al panel de documentos...")
    page.wait_for_selector(
        'input[placeholder*="referencia" i], '
        'input[placeholder*="reference" i], '
        'input[placeholder*="embarque" i], '
        'main input[type="text"]',
        timeout=45000,
    )


def _detectar_estado_pagina(page: Page) -> str:
    """
    Evalúa el estado de la página tras la carga inicial.
    Retorna: 'login' | 'buscador' | 'desconocido'
    """
    for _ in range(20):
        page.wait_for_timeout(2000)

        _manejar_captcha(page)

        if page.query_selector('input[name="pf.username"], input[id="login-email"]'):
            return "login"

        if page.query_selector(
            'input[placeholder*="referencia" i], '
            'input[placeholder*="reference" i], '
            'input[placeholder*="embarque" i]'
        ):
            return "buscador"

    return "desconocido"


def _obtener_input_busqueda(page: Page):
    """
    Localiza el campo de búsqueda correcto dentro del área principal,
    evitando el buscador global del header.
    """
    placeholders = [
        'input[placeholder*="referencia" i]',
        'input[placeholder*="reference" i]',
        'input[placeholder*="embarque" i]',
        'input[placeholder*="Booking" i]',
        'input[placeholder*="B/L" i]',
    ]

    for selector in placeholders:
        loc = page.locator(selector)
        if loc.count() > 0:
            for i in range(loc.count()):
                if loc.nth(i).is_visible():
                    return loc.nth(i)

    # Fallback: input genérico en el área principal (evita el header)
    print("  [búsqueda] Usando selector genérico de fallback...")
    fallback = page.locator('main input[type="text"], .l-zone__main input[type="text"]').first
    fallback.wait_for(state="visible", timeout=15000)
    return fallback


# ---------------------------------------------------------------------------
# Descarga del PDF
# ---------------------------------------------------------------------------

def _descargar_pdf(page: Page, booking: str) -> bool:
    """
    Busca el botón de descarga, abre el popup con el PDF y lo guarda en disco.
    Retorna True si tuvo éxito, False si no.
    """
    selectores_descarga = [
        'table img[alt*="download" i]',
        'table img[src*="download" i]',
        '.rt-table img[alt*="download" i]',
        'a[title*="Download" i]',
        'a:has-text("Descargar")',
        'table a:has-text("Download")',
        'i.icon-download',
    ]

    selector_encontrado = None
    for selector in selectores_descarga:
        if page.locator(selector).count() > 0 and page.locator(selector).first.is_visible():
            selector_encontrado = selector
            break

    try:
        if selector_encontrado:
            print(f"  [descarga] Botón encontrado con selector: '{selector_encontrado}'")
            page.locator(selector_encontrado).first.scroll_into_view_if_needed()
            page.wait_for_timeout(1000)

            with page.expect_popup(timeout=15000) as popup_info:
                page.locator(selector_encontrado).first.click()
        else:
            print("  [descarga] No se encontró botón conocido. Intentando con la primera fila...")
            with page.expect_popup(timeout=15000) as popup_info:
                page.locator('table tr:first-child, .rt-tr-group:first-child').click()

        popup = popup_info.value
        popup.wait_for_load_state()
        print(f"  [descarga] PDF abierto en nueva pestaña: {popup.url}")

        return _guardar_pdf_desde_popup(page, popup, booking)

    except Exception as e:
        print(f"  [descarga] Error al obtener el popup: {e}")
        return False


def _guardar_pdf_desde_popup(page: Page, popup, booking: str) -> bool:
    """
    Usa fetch() desde la página principal (con sesión activa) para descargar
    los bytes del PDF que está abierto en el popup y los guarda en disco.
    """
    output_dir = pathlib.Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    download_path = output_dir / f"BillOfLading-{booking}.pdf"

    js_code = f"""
    async () => {{
        const resp = await fetch("{popup.url}");
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        const buffer = await resp.arrayBuffer();
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {{
            binary += String.fromCharCode(bytes[i]);
        }}
        return btoa(binary);
    }}
    """

    try:
        base64_pdf = page.evaluate(js_code)
        pdf_bytes = base64.b64decode(base64_pdf)

        with open(download_path, "wb") as f:
            f.write(pdf_bytes)

        print(f"  [descarga] ✅ Archivo guardado en: {download_path}")
        popup.close()
        return True

    except Exception as e:
        print(f"  [descarga] ❌ No se pudo capturar el PDF mediante JS: {e}")
        print("  [descarga] Dejando la pestaña abierta para inspección manual.")
        return False


# ---------------------------------------------------------------------------
# Verificación de resultados
# ---------------------------------------------------------------------------

def _verificar_y_descargar(page: Page, booking: str) -> None:
    """Lee la tabla de resultados y descarga el PDF si el estado es 'Disponible'."""
    print("  [resultado] Verificando estado del documento en la tabla...")

    try:
        page.wait_for_selector('table, div.table, .rt-table', timeout=20000)
    except Exception:
        print("  [resultado] ❌ No se cargó ninguna tabla de resultados.")
        print("RESULTADO: NO SE ENCONTRO ADJUNTO")
        return

    elementos = page.query_selector_all('td, span, div')
    disponible = any(
        ("Disponible" in (el.inner_text() or "") or "Available" in (el.inner_text() or ""))
        for el in elementos
    )

    if disponible:
        print("  [resultado] Estado 'Disponible' detectado. Preparando descarga...")
        exito = _descargar_pdf(page, booking)
        print("RESULTADO: OK (Status 200)" if exito else "RESULTADO: NO SE PUDO DESCARGAR")
    else:
        print("  [resultado] Documento no disponible o en estado 'A revisar'.")
        print("RESULTADO: NO SE ENCONTRO ADJUNTO (Status 404/503)")


# ---------------------------------------------------------------------------
# Función principal del bot
# ---------------------------------------------------------------------------

def ejecutar_bot(booking: str, visible: bool = True, slow_mo: int = SLOW_MO) -> None:
    """
    Punto de entrada del bot. Orquesta todo el flujo:
    navegación → login → búsqueda → descarga.
    """
    print(f"\n{'='*60}")
    print(f"  CMA-CGM Bot - Booking: {booking}")
    print(f"{'='*60}\n")

    headless_mode = not visible

    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(
            channel="msedge",
            headless=headless_mode,
            slow_mo=slow_mo,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context()
        page = context.new_page()

        try:
            # 1. Navegar al portal de documentos
            print("[1/5] Navegando al portal de documentación de CMA-CGM...")
            page.goto(BASE_URL, timeout=60000)

            # 2. Detectar estado (login / buscador / desconocido)
            print("[2/5] Detectando estado de la página...")
            estado = _detectar_estado_pagina(page)

            if estado == "login":
                _hacer_login(page)
            elif estado == "buscador":
                print("  [sesión] Sesión activa detectada. El buscador está listo.")
            else:
                print("  [advertencia] Estado no reconocido. Intentando continuar...")

            # 3. Cerrar popups
            _cerrar_popup(page)

            # 4. Asegurar que estamos en el panel correcto
            if "document" not in page.url:
                print("[3/5] Redirigiendo al panel de documentación...")
                page.goto(BASE_URL, timeout=60000)
            else:
                print("[3/5] Ya estamos en el panel de documentación.")

            # 5. Buscar el booking
            print(f"[4/5] Buscando booking: {booking}...")
            page.wait_for_load_state("networkidle")

            search_input = _obtener_input_busqueda(page)
            search_input.fill(booking)
            search_input.press("Enter")

            page.wait_for_load_state("networkidle")
            time.sleep(3)

            # 6. Verificar resultado y descargar
            print("[5/5] Verificando resultados...")
            _verificar_y_descargar(page, booking)

            page.wait_for_timeout(5000)

        except Exception as e:
            print(f"\n  [error crítico] {e}")

        finally:
            print("\nCerrando navegador...")
            browser.close()
