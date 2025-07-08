import pyautogui
import cv2
import numpy as np
import keyboard
import time
import os
import winsound
import threading
import pytesseract
import keyboard
from PIL import Image
# import easyocr
import re
import cv2
import numpy as np
import pyautogui
# from transformers import TrOCRProcessor, VisionEncoderDecoderModel
# import torch
# from collections import Counter
# import mss
import difflib
from difflib import SequenceMatcher


# Cargar modelo TrOCR base
# processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
# model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")

# reader = easyocr.Reader(['es'], gpu=False)  # usa solo CPU

# Configuración OCR
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# X=870, Y=63 Esquina superior izquierda
# X=870, Y=652 Esquina inferior izquierda
# X=1696, Y=652 Esquina inferior derecha
# X=1696, Y=63 Esquina superior derecha

# Región del juego
pantstart_x = 322
pantstart_y = 14
pantlimit_x = 1598
pantlimit_y = 914
ancho = pantlimit_x - pantstart_x  # 826
alto = pantlimit_y - pantstart_y  # 589
# Región de comparación visual: TODA la pantalla del juego
# zona_control = (pantstart_x, pantstart_y, ancho, alto)

# X=655, Y=97 Esquina superior izquierda
# X=657, Y=112 Esquina inferior izquierda
# X=694, Y=97 Esquina inferior derecha
# X=694, Y=116 Esquina superior derecha
# Ancho (zona_w) = X_derecha - X_izquierda
# → 694 - 655 = 39
# Alto (zona_h) = Y_inferior - Y_superior
# → 116 - 97 = 19

# Región de comparación visual (coordenadas absolutas)
zona_x = 0
zona_y = 67
zona_w = 84
zona_h = 32
zona_control = (zona_x, zona_y, zona_w, zona_h)


# Estados
buscando = False
programa_activo = True
intentos_fallidos = 0 # Contador para fallos consecutivos
imagen_referencia = None

# 🔁 Lista de zonas definidas por el usuario
# zonas_definidas = [
#     # (3, 11, -14),
#     # (3, 11, -13),
#     # (3, 11, -12),
#     # (3, 11, -11),
#     # (3, 10, -10),
#     # Solo las válidas para -9
#     # (3, 9, -9),    # por ejemplo, si solo existen 3 y 4
#     # Solo las válidas para -8
#     # (3, 3, -8),
#     (2, 3, -8),
#     (8, 9, -8)
# ]

# zonas_definidas = [
#     {"eje": "x", "desde": 3, "hasta": 4, "fijo": -14},  # Mover horizontalmente: (3, -14) → (4, -14)
#     {"eje": "y", "desde": -14, "hasta": -13, "fijo": 4},  # Mover verticalmente: (4, -14) → (4, -13)
#     {"eje": "x", "desde": 4, "hasta": 3, "fijo": -13},  # Mover horizontalmente en reversa: (4, -13) → (3, -13)
#     {"eje": "diagonal", "desde_x": -56, "hasta_x": -55, "desde_y": 5, "hasta_y": 6}
# ]

zonas_definidas = [
    # {"eje": "x", "desde": -56, "hasta": -55, "fijo": 4},  # Mover horizontalmente: (3, -14) → (4, -14)
    {"eje": "x", "desde": 2, "hasta": 3, "fijo": 7},  # Mover verticalmente: (4, -14) → (4, -13)
    {"eje": "x", "desde": 3, "hasta": 2, "fijo": 7},  # Mover verticalmente: (4, -14) → (4, -13)
    # {"eje": "x", "desde": -55, "hasta": -56, "fijo": 5},  # Mover horizontalmente en reversa: (4, -13) → (3, -13)
    # {"eje": "diagonal", "desde_x": 1, "hasta_x": 2, "desde_y": -17, "hasta_y": -18}
]

# 🔄 Ruta global y posición actual
ruta_completa = []
posicion_actual_index = -1
direccion = 1  # 1: adelante, -1: atrás

# Cargar nombres válidos
try:
    with open("nombres_monstruos.txt", "r", encoding="utf-8") as f:
        nombres_validos = [line.strip().lower() for line in f if line.strip()]
except FileNotFoundError:
    print("⚠️ Archivo 'nombres_monstruos.txt' no encontrado.")
    nombres_validos = []

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
    coincidencias = difflib.get_close_matches(texto_normalizado, nombres_validos, n=1, cutoff=0.6)
    return coincidencias[0] if coincidencias else None

# Limpiar texto OCR
def limpiar_linea_para_busqueda(linea):
    linea = linea.lower()
    linea = re.sub(r"\(\d+\)", "", linea)  # Elimina números entre paréntesis
    linea = re.sub(r"[^a-záéíóúñ\s]", "", linea)  # Quita símbolos
    linea = re.sub(r"\s{2,}", " ", linea)  # Reemplaza múltiples espacios por uno solo
    return linea.strip()

def linea_es_ruido(linea):
    letras = re.findall(r"[a-záéíóúñ]", linea.lower())
    proporcion_letras = len(letras) / max(1, len(linea))
    return proporcion_letras < 0.6

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
    punto_final = None

    for zona in zonas_definidas:
        eje = zona["eje"]
        if eje in ["x", "y"]:
            desde = zona["desde"]
            hasta = zona["hasta"]
            fijo = zona["fijo"]

        # Determinar el orden
        orden_directo = True
        if punto_final:
            if eje == "x":
                orden_directo = punto_final[0] <= desde
            else:
                orden_directo = punto_final[1] <= desde

        # Recorrido eje X
        if eje == "x":
            recorrido = range(min(desde, hasta), max(desde, hasta) + 1)
            if not orden_directo:
                recorrido = reversed(recorrido)

            for x in recorrido:
                punto = (x, fijo)
                if punto in ruta_completa:
                    continue  # omite si ya es el último punto
                ruta_completa.append(punto)
            punto_final = (hasta, fijo)

        # Recorrido eje Y
        elif eje == "y":
            recorrido = range(min(desde, hasta), max(desde, hasta) + 1)
            if not orden_directo:
                recorrido = reversed(recorrido)

            for y in recorrido:
                punto = (fijo, y)
                if punto in ruta_completa:
                    continue
                ruta_completa.append(punto)
            punto_final = (fijo, hasta)
        elif eje == "diagonal":
            dx1, dx2 = zona["desde_x"], zona["hasta_x"]
            dy1, dy2 = zona["desde_y"], zona["hasta_y"]

            pasos = max(abs(dx2 - dx1), abs(dy2 - dy1)) + 1
            dx_step = 1 if dx2 > dx1 else -1
            dy_step = 1 if dy2 > dy1 else -1

            for i in range(pasos):
                punto = (dx1 + i * dx_step, dy1 + i * dy_step)
                if punto in ruta_completa:
                    continue
                ruta_completa.append(punto)
            punto_final = (dx2, dy2)


# 🚶 Construcción y movimiento a la siguiente posición
def recorrer_zonas_definidas():
    global ruta_completa, posicion_actual_index, direccion

    if not ruta_completa:
        construir_ruta()

    siguiente_index = posicion_actual_index + direccion

    if siguiente_index >= len(ruta_completa):
        print("✅ Se completó todo el recorrido de zonas. ↩️ Regresando en reversa.")
        direccion = -1
        siguiente_index = len(ruta_completa) - 2  # empieza justo antes del último
    elif siguiente_index < 0:
        print("✅ Se completó el regreso. 🔁 Volviendo a avanzar.")
        direccion = 1
        siguiente_index = 1  # empieza justo después del primero

    posicion_actual_index = siguiente_index
    x, y = ruta_completa[posicion_actual_index]
    print(f"📍 Viajando a coordenada: {x}, {y}")

    # 1. Hacer clic en el chat
    pyautogui.click(215, 1064)
    time.sleep(0.3)
    # 2. Escribir el comando
    pyautogui.write(f"/travel {x} {y}", interval=0.05)
    keyboard.press_and_release("enter")
    time.sleep(0.3)
    # 3. Hacer clic en el botón de confirmar
    pyautogui.click(873, 594)
    print("🧭 Comando /travel enviado y confirmado.")
    time.sleep(2.5)

# 🛠️ Acción al fallar 3 veces
def al_fallar_3_veces():
    global imagen_referencia, buscando, programa_activo

    # Verificamos si está pausado antes de continuar
    if not buscando or not programa_activo:
        print("⏸️ Escaneo pausado. No se valida zona visual.")
        return

    recorrer_zonas_definidas()
    print("⚠️ Se falló 3 veces. Verificando cambio visual en zona...")

    while buscando and programa_activo:
        nueva_captura = pyautogui.screenshot(region=zona_control)
        nueva_np = np.array(nueva_captura)
        nueva_gray = cv2.cvtColor(nueva_np, cv2.COLOR_RGB2GRAY)

        if imagen_referencia is None:
            imagen_referencia = nueva_gray
            print("📌 Imagen de referencia almacenada.")
            break

        diferencia = cv2.absdiff(imagen_referencia, nueva_gray)
        _, thresh = cv2.threshold(diferencia, 25, 255, cv2.THRESH_BINARY)
        cambio = np.sum(thresh)

        if cambio > 100:
            print("🔄 Zona cambió, reiniciando escaneo.")
            imagen_referencia = nueva_gray
            time.sleep(2)  # Espera antes de reanudar escaneo
            break
        else:
            print("⏳ Zona sin cambio. Reintentando en 1.5 segundos...")
            time.sleep(1.5)

# 🔍 Buscar fuego en pantalla
def buscar_fuegos(plantillas):
    global buscando, intentos_fallidos

    # 1. Búsqueda de texto con W presionada (usando tu método exacto)
    try:
        keyboard.press('w')
        time.sleep(0.15)  # Tiempo para que aparezcan los cuadros
        
        # Captura completa del área del juego usando tus coordenadas
        captura = pyautogui.screenshot(region=(
            pantstart_x,
            pantstart_y,
            ancho,
            alto
        ))
        keyboard.release('w')
        
        # Tu lógica exacta de procesamiento OCR
        img_np = np.array(captura)
        img_gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        # cv2.imwrite("verificacion.png", img_gray)
        
        texto_crudo = pytesseract.image_to_string(img_gray, lang="spa", config='--psm 6')
        lineas = [line.strip() for line in texto_crudo.splitlines() if line.strip()]
        texto_encontrado = None
        print(texto_crudo)
        
        for linea in lineas:
            print(f"📝 OCR bruta: '{linea}'")
            
            if linea_es_ruido(linea):
                print("⛔ Línea descartada como ruido")
                continue

            linea_limpia = limpiar_linea_para_busqueda(linea)
            print(f"✅ Línea limpia: '{linea_limpia}'")

            if len(linea_limpia) < 4:
                print("⛔ Demasiado corta")
                continue

            coincidencia = es_texto_valido(linea_limpia)
            print(f"🎯 Coincidencia: {coincidencia}")

            if coincidencia:
                texto_encontrado = (linea, coincidencia)
                break

        if texto_encontrado:
            linea_ocr, nombre_valido = texto_encontrado
            print(f"\n✅ ¡Monstruo detectado! → '{nombre_valido}'")
            print(f"🔤 OCR: '{linea_ocr}'")
            reproducir_sonido()
            buscando = False
            intentos_fallidos = 0
            return

    except Exception as e:
        print(f"⚠️ Error al buscar texto: {str(e)}")
        keyboard.release('w')  # Asegurar liberación de tecla

    # 2. Búsqueda de fuegos con dos métodos de comparación
    screenshot = pyautogui.screenshot(region=(pantstart_x, pantstart_y, ancho, alto))
    img_rgb = np.array(screenshot)

    # Versión 1: Solo escalado (método rápido)
    img_upscaled = cv2.resize(img_rgb, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    img_gray_simple = cv2.cvtColor(img_upscaled, cv2.COLOR_RGB2GRAY)

    # Versión 2: Preprocesamiento completo (método preciso)
    img_gray_enhanced = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    img_gray_enhanced = cv2.GaussianBlur(img_gray_enhanced, (5,5), 0)
    img_gray_enhanced = cv2.equalizeHist(img_gray_enhanced)
    img_gray_enhanced = cv2.resize(img_gray_enhanced, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    mejor_coincidencia = {'nombre': None, 'max_val': 0, 'pos': None, 'metodo': None}

    for nombre, template in plantillas:
        # Preparar plantilla según su tipo
        if len(template.shape) == 3:
            if template.shape[2] == 4:  # Plantilla con alpha channel
                alpha = template[:,:,3]
                template_gray = cv2.cvtColor(template[:,:,:3], cv2.COLOR_BGR2GRAY)
                mask = cv2.threshold(alpha, 50, 255, cv2.THRESH_BINARY)[1]
            else:
                template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                mask = None
        else:
            template_gray = template
            mask = None
        
        # Escalar plantilla para coincidir con la imagen upscaled
        template_scaled = cv2.resize(template_gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        if mask is not None:
            mask = cv2.resize(mask, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)

        # Método 1: Comparación simple (rápida)
        res_simple = cv2.matchTemplate(img_gray_simple, template_scaled, cv2.TM_CCOEFF_NORMED, mask=mask)
        _, max_val_simple, _, max_loc_simple = cv2.minMaxLoc(res_simple)
        
        # Método 2: Comparación con preprocesamiento (precisa)
        res_enhanced = cv2.matchTemplate(img_gray_enhanced, template_scaled, cv2.TM_CCOEFF_NORMED, mask=mask)
        _, max_val_enhanced, _, max_loc_enhanced = cv2.minMaxLoc(res_enhanced)
        
        # Seleccionar el mejor resultado entre ambos métodos
        if max_val_enhanced > max_val_simple:
            current_max = max_val_enhanced
            current_loc = max_loc_enhanced
            metodo = 'preciso'
        else:
            current_max = max_val_simple
            current_loc = max_loc_simple
            metodo = 'rápido'
        
        # Umbral dinámico
        brightness = np.mean(img_gray_simple)/255
        threshold = max(0.45, 0.4 + brightness * 0.25)
        
        if current_max > threshold and current_max > mejor_coincidencia['max_val']:
            # Verificación adicional de calidad
            x, y = current_loc
            w, h = template_scaled.shape[::-1]
            roi = img_gray_simple[y:y+h, x:x+w] if metodo == 'rápido' else img_gray_enhanced[y:y+h, x:x+w]
            
            if np.std(roi) > 15 and 25 < np.mean(roi) < 230:
                mejor_coincidencia = {
                    'nombre': nombre,
                    'max_val': current_max,
                    'pos': (x//2, y//2),  # Ajustar coordenadas al tamaño original
                    'metodo': metodo
                }

    # Procesar mejor coincidencia encontrada
    if mejor_coincidencia['nombre']:
        nombre = mejor_coincidencia['nombre']
        x, y = mejor_coincidencia['pos']
        print(f"🔥 Detección ({mejor_coincidencia['metodo']}): {nombre} (score: {mejor_coincidencia['max_val']:.2f})")
        pyautogui.moveTo(x + pantstart_x + 15, y + pantstart_y + 50)
        reproducir_sonido()
        buscando = False
        intentos_fallidos = 0
        return

    # Si no hay coincidencias
    print("❌ No se encontraron coincidencias válidas")
    intentos_fallidos += 1
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
                cv2.imwrite("imagen_referencia.png", imagen_referencia)  # Guardar para revisión
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
