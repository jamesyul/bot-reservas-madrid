# main.py
import os
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# --- CONFIGURACIÓN ---
# Intentamos cargar desde un archivo config.py local (para pruebas)
try:
    from config import USERNAME, PASSWORD
# Si no existe, lo cargamos desde las variables de entorno (para el despliegue en GitHub Actions)
except ImportError:
    USERNAME = os.environ.get('DEPORTES_USER')
    PASSWORD = os.environ.get('DEPORTES_PASS')

URL_LOGIN = "https://deportesweb.madrid.es/DeportesWeb/login"
URL_HOME = "https://deportesweb.madrid.es/DeportesWeb/Home"
TARGET_CENTER = "Faustina Valladolid"
TARGET_ACTIVITY = "Sala multitrabajo"
TARGET_TIME_SLOT = "12:00" # La hora de inicio que buscas

# --- LÓGICA DE FECHAS ---
# Días que queremos reservar: Lunes (0), Martes (1), Jueves (3), Viernes (4)
DIAS_RESERVA_OBJETIVO = [0, 1, 3, 4]

# La reserva se abre 49 horas antes.
# Para reservar Lunes -> El bot debe correr el Sábado anterior.
# Para reservar Martes -> El bot debe correr el Domingo anterior.
# Para reservar Jueves -> El bot debe correr el Martes anterior.
# Para reservar Viernes -> El bot debe correr el Miércoles anterior.
# Días en que el bot debe EJECUTARSE: Sábado(5), Domingo(6), Martes(1), Miércoles(2)
DIAS_DE_EJECUCION_BOT = [5, 6, 1, 2]

hoy_weekday = datetime.now().weekday()

if hoy_weekday not in DIAS_DE_EJECUCION_BOT:
    print(f"Hoy es {datetime.now().strftime('%A')}. No es un día para ejecutar el bot. Saliendo.")
    exit()

# Calculamos la fecha objetivo (la fecha para la que queremos la reserva)
# La web parece usar una lógica de 2 días de antelación
fecha_objetivo = datetime.now() + timedelta(days=2)
dia_objetivo_numero = str(fecha_objetivo.day)

print(f"✅ Bot iniciado. Hoy es {datetime.now().strftime('%A')}. Intentando reservar para el día {dia_objetivo_numero}.")

# --- EJECUCIÓN DEL BOT ---
# --- CONFIGURACIÓN DE CHROME PARA GITHUB ACTIONS (HEADLESS) ---
options = Options()
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080") # <-- AÑADE ESTA LÍNEA
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 15) # Aumentamos la espera a 15 segundos por si la web es lenta

try:
    # 1. IR DIRECTAMENTE A LA PÁGINA DE LOGIN
    print("Navegando a la página de login...")
    driver.get(URL_LOGIN)

    # 2. GESTIONAR EL BANNER DE COOKIES (SI APARECE)
    # Usamos un try/except porque el banner puede no aparecer en todas las ejecuciones.
    try:
        # Esperamos un máximo de 5 segundos a que el botón de cookies sea clickeable
        cookie_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Acepto')]"))
        )
        cookie_button.click()
        print("Banner de cookies aceptado.")
    except Exception as e:
        print("No se encontró el banner de cookies o ya estaba aceptado. Continuando...")

    # 3. SELECCIONAR EL MÉTODO DE LOGIN "CORREO Y CONTRASEÑA"
    print("Seleccionando método de login 'Correo y contraseña'...")
    # Buscamos el contenedor que tiene el texto "Correo y contraseña" y le hacemos clic
    login_method_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Correo y contraseña')]"))
    )
    login_method_button.click()

    # 4. AHORA SÍ, RELLENAR EL FORMULARIO DE LOGIN
    print("Rellenando formulario de login...")

    # --- Rellenar Correo electrónico con el ID correcto ---
    wait.until(EC.presence_of_element_located((By.ID, "ContentFixedSection_uLogin_txtIdentificador"))).send_keys(USERNAME)

    # --- Rellenar Contraseña con el ID correcto ---
    wait.until(EC.presence_of_element_located((By.ID, "ContentFixedSection_uLogin_txtContrasena"))).send_keys(PASSWORD)

    # --- GESTIONAR EL CHECKBOX "NO CERRAR SESIÓN" ---
    print("Verificando el checkbox 'No cerrar sesión'...")
    # Primero, localizamos el checkbox por su ID
    checkbox_no_cerrar_sesion = wait.until(EC.presence_of_element_located((By.ID, "ContentFixedSection_uLogin_chkNoCerrarSesion")))

    # Comprobamos si ya está seleccionado
    if not checkbox_no_cerrar_sesion.is_selected():
        # Si no está seleccionado, le hacemos clic
        print("El checkbox no estaba marcado. Marcándolo ahora.")
        checkbox_no_cerrar_sesion.click()
    else:
        # Si ya estaba seleccionado, lo informamos y no hacemos nada
        print("El checkbox ya estaba marcado. No se realiza ninguna acción.")

    # --- HACER CLIC EN EL BOTÓN "INICIAR SESIÓN" CON EL ID CORRECTO ---
    print("Haciendo clic en 'Iniciar sesión'...")
    wait.until(EC.element_to_be_clickable((By.ID, "ContentFixedSection_uLogin_btnLogin"))).click()

    print("✅ Login completado con éxito.")

    # 5. IR A LA PÁGINA PRINCIPAL PARA EMPEZAR LA RESERVA
    # Una vez logueados, nos aseguramos de estar en la home para seguir los pasos.
    driver.get(URL_HOME)
    print("Navegando a la página principal post-login...")

    # --- NUEVO PASO DE ESPERA INTELIGENTE ---
    # Esperamos a que un elemento clave de la home (el título de noticias) sea visible.
    # Esto asegura que la página está completamente cargada antes de buscar el centro.
    wait.until(EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Noticias y eventos deportivos')]")))
    print("Página principal cargada y lista.")

    # 6. SELECCIONAR CENTRO DEPORTIVO
    print(f"Buscando el centro: {TARGET_CENTER}")
    centro_elem = wait.until(EC.element_to_be_clickable((By.XPATH, f"//article[contains(., '{TARGET_CENTER}')]")))
    centro_elem.click()
    print("Centro seleccionado.")

    # --- NUEVO PASO DE ESPERA INTELIGENTE ---
    # Antes de buscar la actividad, esperamos a que un elemento clave de la nueva página aparezca.
    # Esto confirma que la página ha cargado por completo después del clic anterior.
    # Un buen "landmark" es el título de la sección.
    print("Esperando a que cargue la página del centro...")
    wait.until(EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Reserva de clases abiertas')]")))
    print("Página del centro cargada.")
    
    # 7. SELECCIONAR "SALA MULTITRABAJO" (VERSIÓN ANTI-STALE)
    print(f"Buscando la actividad: {TARGET_ACTIVITY}")

    # PASO 1: Guardamos la "dirección" (XPath) del elemento, no el elemento en sí.
    xpath_actividad = f"//article[contains(., '{TARGET_ACTIVITY}')]"

    # PASO 2: Localizamos el elemento la primera vez, SOLO para poder hacer scroll hacia él.
    elemento_para_scroll = wait.until(EC.presence_of_element_located((By.XPATH, xpath_actividad)))
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento_para_scroll)
    print("Haciendo scroll hasta la actividad...")
    time.sleep(0.5) # Pequeña pausa para que el DOM se estabilice tras el scroll.

    # PASO 3 (LA CLAVE): Volvemos a buscar el elemento desde cero usando su "dirección"
    # y hacemos clic en la referencia "fresca". Esto evita el error "stale".
    print("Haciendo clic en la actividad ahora que es visible...")
    wait.until(EC.element_to_be_clickable((By.XPATH, xpath_actividad))).click()
    print("Actividad seleccionada.")
    
    # 8. SELECCIONAR DÍA EN EL CALENDARIO
    print(f"Buscando el día {dia_objetivo_numero} en el calendario.")
    dia_elem = wait.until(EC.element_to_be_clickable((By.XPATH, f"//td[text()='{dia_objetivo_numero}' and not(contains(@class, 'disabled'))]")))
    dia_elem.click()
    print(f"Día {dia_objetivo_numero} seleccionado.")
    
    # 9. SELECCIONAR LA HORA
    print(f"Buscando la hora {TARGET_TIME_SLOT}.")

    # PASO 1: Localizamos el contenedor del horario (el <li>) con el nuevo XPath.
    # Este XPath busca un <li> que en su interior (.//) tenga un <h4> con el texto de nuestra hora.
    hora_xpath = f"//li[.//h4[text()='{TARGET_TIME_SLOT}']] | //li[.//h4[starts-with(text(),'{TARGET_TIME_SLOT}')]]"
    hora_elem = wait.until(EC.presence_of_element_located((By.XPATH, hora_xpath)))

    # PASO 2: Hacemos scroll hasta que el elemento sea visible.
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", hora_elem)
    print("Haciendo scroll hasta el horario...")
    time.sleep(0.5)  # Pequeña pausa para que el scroll se asiente.

    # PASO 3: Ahora que es visible, esperamos a que sea clickeable y hacemos clic.
    wait.until(EC.element_to_be_clickable(hora_elem)).click()
    print("Hora seleccionada.")
    
    # 10. CONFIRMAR LA COMPRA (CARRITO)
    print("Buscando el botón 'Confirmar la compra'...")

    # PASO 1: Localizamos el botón por su ID exacto.
    confirmar_btn = wait.until(EC.presence_of_element_located((By.ID, "ContentFixedSection_uCarritoConfirmar_btnConfirmCart")))

    # PASO 2: Hacemos scroll hasta que el botón sea visible.
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", confirmar_btn)
    print("Haciendo scroll hasta el botón de confirmación...")
    time.sleep(0.5)

    # PASO 3: Ahora que es visible, esperamos a que sea clickeable y hacemos clic.
    wait.until(EC.element_to_be_clickable(confirmar_btn)).click()
    print("Compra confirmada.")
    
    # 11. SALIR DE LA PÁGINA DE CONFIRMACIÓN FINAL
    salir_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Salir')]")))
    print("🎉 ¡RESERVA COMPLETADA CON ÉXITO!")
    salir_btn.click()
    
except Exception as e:
    print(f"❌ Ha ocurrido un error: {e}")
    driver.save_screenshot('error_screenshot.png')
    print("Se ha guardado una captura de pantalla del error: 'error_screenshot.png'")

finally:
    print("El bot ha finalizado. El navegador se cerrará en 10 segundos.")
    time.sleep(10)
    driver.quit()