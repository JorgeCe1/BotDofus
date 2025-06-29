import pyautogui
import cv2
import numpy as np
import keyboard
import time
import os
import winsound
import threading
import pytesseract

# Región del juego
pantstart_x = 322
pantstart_y = 14
pantlimit_x = 1598
pantlimit_y = 914
ancho = pantlimit_x - pantstart_x
alto = pantlimit_y - pantstart_y

# Región de comparación visual (coordenadas absolutas)
zona_x = pantstart_x + 2
zona_y = pantstart_y + 67
zona_w = 66
zona_h = 24
zona_control = (zona_x, zona_y, zona_w, zona_h)

# Estados
buscando = False
programa_activo = True
intentos_fallidos = 0 # Contador para fallos consecutivos
imagen_referencia = None

# 🔁 Lista de zonas definidas por el usuario
zonas_definidas = [
    (3, 11, -14),
    (3, 11, -13),
    (3, 11, -12),
    (3, 11, -11),
    (3, 10, -11),
    (3, 9, -11),
    (2, 3, -8),
    (8, 9, -8)
]

# 🔄 Ruta global y posición actual
ruta_completa = []
zonas_visitadas = set()
posicion_actual_index = -1

# 🔊 Reproducir sonido
def reproducir_sonido():
    if os.path.exists("encontre.wav"):
        winsound.PlaySound("encontre.wav", winsound.SND_FILENAME | winsound.SND_ASYNC)
    else:
        print("⚠️ Sonido 'encontre.wav' no encontrado.")

# 🔥 Cargar plantillas fuego*.png
def cargar_plantillas():
    plantillas = []
    for nombre in os.listdir():
        if nombre.lower().startswith("fuego") and nombre.lower().endswith(".png"):
            plantilla = cv2.imread(nombre, cv2.IMREAD_GRAYSCALE)
            if plantilla is not None:
                plantillas.append((nombre, plantilla))
    return plantillas

# Construye ruta completa
def construir_ruta():
    global ruta_completa
    ruta_completa = []

    for i, (x_inicio, x_fin, y) in enumerate(zonas_definidas):
        if i % 2 == 0:
            for x in range(x_inicio, x_fin + 1):
                ruta_completa.append((x, y))
        else:
            for x in range(x_fin, x_inicio - 1, -1):
                ruta_completa.append((x, y))

# Lee coordenadas de pantalla
def obtener_coordenadas_actuales():
    captura = pyautogui.screenshot(region=zona_control)
    np_img = np.array(captura)
    gray = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)

    texto = pytesseract.image_to_string(gray, config='--psm 7').strip()
    import re
    match = re.search(r"-?\d+\s*,\s*-?\d+", texto)
    if match:
        x_str, y_str = match.group().replace(" ", "").split(",")
        return int(x_str), int(y_str)
    return None

# 🚶 Construcción y movimiento a la siguiente posición
def recorrer_zonas_definidas():
    global ruta_completa, posicion_actual_index

    if not ruta_completa:
        construir_ruta()

    posicion_actual_index += 1
    if posicion_actual_index >= len(ruta_completa):
        print("✅ Se completó todo el recorrido de zonas.")
        posicion_actual_index = 0

    siguiente_pos = ruta_completa[posicion_actual_index]
    x, y = siguiente_pos
    print(f"📍 Viajando a coordenada: {x}, {y}")
    zonas_visitadas.add(siguiente_pos)

    # 1. Hacer clic en el chat
    pyautogui.click(215, 1064)
    time.sleep(0.2)

    # 2. Escribir el comando
    pyautogui.typewrite(f"/travel {x} {y}", interval=0.05)
    time.sleep(0.2)

    # 3. Hacer clic en el botón de confirmar
    pyautogui.click(873, 594)
    time.sleep(2.5)

# 🛠️ Acción al fallar 3 veces
def al_fallar_3_veces():
    global imagen_referencia

    recorrer_zonas_definidas()
    print("⚠️ Se falló 3 veces. Verificando cambio visual en zona...")

    while True:
        nueva_captura = pyautogui.screenshot(region=zona_control)
        nueva_np = np.array(nueva_captura)
        nueva_gray = cv2.cvtColor(nueva_np, cv2.COLOR_RGB2GRAY)

        coords = obtener_coordenadas_actuales()
        if coords:
            if coords in ruta_completa and coords not in zonas_visitadas:
                diferencia = cv2.absdiff(imagen_referencia, nueva_gray)
                _, thresh = cv2.threshold(diferencia, 25, 255, cv2.THRESH_BINARY)
                cambio = np.sum(thresh)

                if cambio > 100:
                    print(f"🔄 Cambio válido en zona {coords}. Reanudando escaneo.")
                    imagen_referencia = nueva_gray
                    break
                else:
                    print(f"⏳ Zona {coords} sin cambio visual. Reintentando...")
            else:
                print(f"🕓 Zona {coords} ya recorrida o inválida. Esperando nuevo cambio...")
        else:
            print("⚠️ No se pudieron leer coordenadas.")

        time.sleep(1.5)

# 🔍 Buscar fuego en pantalla
def buscar_fuegos(plantillas):
    global buscando, intentos_fallidos

    screenshot = pyautogui.screenshot(region=(pantstart_x, pantstart_y, ancho, alto))
    img_rgb = np.array(screenshot)
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)

    primer_fuego_pos = None

    for nombre, template in plantillas:
        w, h = template.shape[::-1]
        res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        threshold = 0.7
        loc = np.where(res >= threshold)

        if len(loc[0]) > 0:
            print(f"✅ Coincidencias con '{nombre}': {len(loc[0])}")
            for pt in zip(*loc[::-1]):
                pos_x = pt[0] + pantstart_x
                pos_y = pt[1] + pantstart_y
                print(f" → {nombre}: posición ({pos_x}, {pos_y})")
                if primer_fuego_pos is None:
                    primer_fuego_pos = (pos_x, pos_y)
                    cv2.rectangle(img_rgb, pt, (pt[0] + w, pt[1] + h), (0, 255, 0), 2)
        else:
            print(f"❌ No se encontró '{nombre}'.")

    if primer_fuego_pos:
        intentos_fallidos = 0
        fuego_x, fuego_y = primer_fuego_pos
        mover_x = fuego_x + 15
        mover_y = fuego_y + 50
        pyautogui.moveTo(mover_x, mover_y)
        print(f"🖱️ Mouse movido a ({mover_x}, {mover_y}) justo debajo del fuego.")
        reproducir_sonido()
        cv2.imshow("🔥 Detección", cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))
        cv2.waitKey(1500)
        cv2.destroyAllWindows()
        buscando = False
        print("⏸️ Escaneo pausado automáticamente.")
    else:
        intentos_fallidos += 1
        print(f"❌ No se detectó fuego. Intentos fallidos: {intentos_fallidos}/3")
        if intentos_fallidos >= 3:
            al_fallar_3_veces()
            intentos_fallidos = 0

# 📸 Captura manual del fuego
def capturar_fuego_manual():
    x, y = pyautogui.position()
    region = (x - 20, y - 20, 40, 40)
    img = pyautogui.screenshot(region=region)
    i = 1
    while os.path.exists(f"fuego{i}.png"):
        i += 1
    img.save(f"fuego{i}.png")
    print(f"📸 Plantilla '{f"fuego{i}.png"}' guardada.")

# 🧠 Escaneo en hilo
def ejecutar_escaneo():
    global buscando, programa_activo
    while programa_activo:
        if buscando:
            plantillas = cargar_plantillas()
            if not plantillas:
                print("⚠️ No hay plantillas fuego*.png.")
            else:
                buscar_fuegos(plantillas)
            time.sleep(1.5)
        else:
            time.sleep(0.1)

# 🎮 Control de teclas
def manejar_teclas():
    global buscando, programa_activo, imagen_referencia
    print("🟢 F4: capturar fuego  |  F5: iniciar  |  F6: pausar  |  F7: salir")

    while programa_activo:
        if keyboard.is_pressed("f4"):
            capturar_fuego_manual()
            time.sleep(0.5)
        elif keyboard.is_pressed("f5"):
            if not buscando:
                captura = pyautogui.screenshot(region=zona_control)
                img_np = np.array(captura)
                imagen_referencia = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                print("▶️ Escaneo iniciado. Imagen de referencia almacenada.")
                buscando = True
            time.sleep(0.5)
        elif keyboard.is_pressed("f6"):
            if buscando:
                buscando = False
                print("⏸️ Escaneo pausado.")
            time.sleep(0.5)
        elif keyboard.is_pressed("f7"):
            print("🛑 Programa finalizado.")
            buscando = False
            programa_activo = False
            break
        time.sleep(0.1)

# 🧵 Iniciar hilo de escaneo
threading.Thread(target=ejecutar_escaneo, daemon=True).start()
manejar_teclas()
