import pyautogui
import pytesseract
import keyboard
import time
import cv2
import numpy as np
import difflib
import re
import winsound
from difflib import SequenceMatcher

# Configuración OCR
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Área de escaneo del juego
pantstart_x = 322
pantstart_y = 14
pantlimit_x = 1598
pantlimit_y = 914

# Tamaño del cuadro de información
cuadro_ancho = 360
cuadro_alto = 300
desplazar_izquierda = 40

# Cargar nombres válidos
try:
    with open("nombres_monstruos.txt", "r", encoding="utf-8") as f:
        nombres_validos = [line.strip().lower() for line in f if line.strip()]
except FileNotFoundError:
    print("⚠️ Archivo 'nombres_monstruos.txt' no encontrado.")
    nombres_validos = []

# Reproducir sonido
def reproducir_sonido_exito():
    winsound.PlaySound("encontre.wav", winsound.SND_FILENAME | winsound.SND_ASYNC)

# Comparación aproximada
def encontrar_similar(texto_ocr, nombres_validos, umbral=0.75):
    texto_ocr = texto_ocr.lower()
    mejores = []
    for nombre in nombres_validos:
        ratio = SequenceMatcher(None, texto_ocr, nombre).ratio()
        if ratio >= umbral:
            mejores.append((nombre, round(ratio, 2)))
    return sorted(mejores, key=lambda x: x[1], reverse=True)

# Validación exacta o aproximada
def es_texto_valido(texto):
    texto_normalizado = texto.lower().strip()
    if texto_normalizado in nombres_validos:
        return texto_normalizado
    coincidencias = difflib.get_close_matches(texto_normalizado, nombres_validos, n=1, cutoff=0.85)
    return coincidencias[0] if coincidencias else None

# Limpiar texto OCR
def limpiar_linea_para_busqueda(linea):
    linea = linea.lower()
    linea = re.sub(r"\(\d+\)", "", linea)  # Elimina (22), (30)
    linea = re.sub(r"[^a-záéíóúñ\s]", "", linea)  # Quita símbolos
    return linea.strip()

def linea_es_ruido(linea):
    letras = re.findall(r"[a-záéíóúñ]", linea.lower())
    proporcion_letras = len(letras) / max(1, len(linea))
    return proporcion_letras < 0.6  # si menos del 60% son letras, se descarta

# Estado de control
buscando = False
programa_activo = True

# Escaneo por bloques 5x5
def escanear_por_bloques():
    global buscando, programa_activo

    print("🎯 Presiona F5 para iniciar escaneo 15x15, F6 para pausar, F7 para salir.")

    cols = 15
    rows = 15
    bloque_ancho = (pantlimit_x - pantstart_x) // cols
    bloque_alto = (pantlimit_y - pantstart_y) // rows

    bloque_i = 0
    bloque_j = 0

    while programa_activo:
        if buscando:
            centro_x = pantstart_x + bloque_i * bloque_ancho + bloque_ancho // 2
            centro_y = pantstart_y + bloque_j * bloque_alto + bloque_alto // 2

            pyautogui.moveTo(centro_x, centro_y)
            time.sleep(0.2)

            captura_x = centro_x - cuadro_ancho // 3 + desplazar_izquierda
            captura_y = centro_y - cuadro_alto + 10
            if captura_y < 0:
                captura_y = 0

            captura = pyautogui.screenshot(region=(captura_x, captura_y, cuadro_ancho, cuadro_alto))
            img_np = np.array(captura)
            img_gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

            # 🧠 Tu OCR preferido sin restricciones
            texto_crudo = pytesseract.image_to_string(img_gray, lang="spa", config='--psm 6')

            lineas = [line.strip() for line in texto_crudo.splitlines() if line.strip()]
            texto_encontrado = None

            for linea in lineas:
                if linea_es_ruido(linea):
                    continue

                linea_limpia = limpiar_linea_para_busqueda(linea)
                if len(linea_limpia) < 6:
                    continue

                coincidencia = es_texto_valido(linea_limpia)
                if coincidencia:
                    texto_encontrado = (linea, coincidencia)
                    break

            if texto_encontrado:
                linea_ocr, nombre_valido = texto_encontrado
                print(f"\n✅ ¡Monstruo detectado en bloque {bloque_i+1},{bloque_j+1}! → '{nombre_valido}'")
                print(f"🔤 OCR: '{linea_ocr}'")
                reproducir_sonido_exito()

                # 🚨 Detener programa completamente
                buscando = False
                print("⏸️ Escaneo pausado tras detección.")
                time.sleep(1.5)  # tiempo para permitir que el sonido suene bien
                return

            # Avanzar al siguiente bloque
            bloque_j += 1
            if bloque_j >= rows:
                bloque_j = 0
                bloque_i += 1
                if bloque_i >= cols:
                    bloque_i = 0
                    print("🔁 Escaneo completo. Reiniciando desde el inicio.")

        else:
            time.sleep(0.1)

# Teclas de control
def controlar_teclas():
    global buscando, programa_activo
    while programa_activo:
        if keyboard.is_pressed("f5"):
            if not buscando:
                buscando = True
                print("▶️ Escaneo por bloques iniciado.")
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

# Iniciar hilo
import threading
threading.Thread(target=escanear_por_bloques, daemon=True).start()
controlar_teclas()
