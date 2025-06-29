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
# from PIL import Image
# import easyocr
# import re
import cv2
import numpy as np
import pyautogui
# from transformers import TrOCRProcessor, VisionEncoderDecoderModel
# import torch
# from collections import Counter
import mss


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
    {"eje": "y", "desde": -13, "hasta": -13, "fijo": 5},  # Mover verticalmente: (4, -14) → (4, -13)
    {"eje": "y", "desde": -13, "hasta": -13, "fijo": 6},  # Mover verticalmente: (4, -14) → (4, -13)
    # {"eje": "x", "desde": -55, "hasta": -56, "fijo": 5},  # Mover horizontalmente en reversa: (4, -13) → (3, -13)
    # {"eje": "diagonal", "desde_x": 1, "hasta_x": 2, "desde_y": -17, "hasta_y": -18}
]

# 🔄 Ruta global y posición actual
ruta_completa = []
posicion_actual_index = -1
direccion = 1  # 1: adelante, -1: atrás


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

    screenshot = pyautogui.screenshot(region=(pantstart_x, pantstart_y, ancho, alto))
    img_rgb = np.array(screenshot)
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    
    # Preprocesamiento mejorado
    img_gray = cv2.GaussianBlur(img_gray, (5, 5), 0)
    img_gray = cv2.equalizeHist(img_gray)
    
    # Variables para seguimiento
    mejor_max_val = 0
    mejor_pos = None
    mejor_nombre = ""
    mejor_template_size = (0, 0)
    detecciones_validas = []

    for nombre, template in plantillas:
        # Manejo de plantillas con/sin transparencia
        if len(template.shape) == 3 and template.shape[2] == 4:
            alpha = template[:, :, 3]
            template_gray = cv2.cvtColor(template[:, :, :3], cv2.COLOR_BGR2GRAY)
            mask = cv2.threshold(alpha, 50, 255, cv2.THRESH_BINARY)[1]
            res = cv2.matchTemplate(img_gray, template_gray, cv2.TM_CCOEFF_NORMED, mask=mask)
        else:
            if len(template.shape) == 3:
                template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            else:
                template_gray = template
            res = cv2.matchTemplate(img_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        w, h = template_gray.shape[::-1]
        
        print(f"🔍 {nombre} - Min: {min_val:.4f}, Max: {max_val:.4f}, MaxLoc: {max_loc}")

        # Umbral dinámico basado en características de la imagen
        brightness = np.mean(img_gray)/255
        dynamic_threshold = 0.45 + (brightness * 0.2)  # Rango 0.45-0.65
        
        if max_val >= dynamic_threshold:
            detecciones_validas.append({
                'nombre': nombre,
                'max_val': max_val,
                'pos': max_loc,
                'size': (w, h)
            })

    # Procesar detecciones válidas
    if detecciones_validas:
        # Ordenar por score de coincidencia
        detecciones_validas.sort(key=lambda x: x['max_val'], reverse=True)
        
        # Seleccionar la mejor detección
        mejor_deteccion = detecciones_validas[0]
        mejor_max_val = mejor_deteccion['max_val']
        mejor_pos = mejor_deteccion['pos']
        mejor_nombre = mejor_deteccion['nombre']
        mejor_template_size = mejor_deteccion['size']
        
        # Verificación adicional de calidad
        x, y = mejor_pos
        w, h = mejor_template_size
        roi = img_gray[y:y+h, x:x+w]
        
        # Calcular métricas de calidad
        contrast = np.std(roi)
        brightness_roi = np.mean(roi)
        
        # Si pasa todas las verificaciones
        if contrast > 20 and 30 < brightness_roi < 220:
            print(f"🔥 Fuego detectado con '{mejor_nombre}' (score: {mejor_max_val:.2f}, thr: {dynamic_threshold:.2f})")
            pos_x = mejor_pos[0] + pantstart_x
            pos_y = mejor_pos[1] + pantstart_y
            mover_x = pos_x + 15
            mover_y = pos_y + 50
            pyautogui.moveTo(mover_x, mover_y)
            reproducir_sonido()
            buscando = False
            intentos_fallidos = 0
            return
    
    # Si no hay detecciones válidas
    print(f"❌ Ninguna coincidencia superó el umbral. Mejor: {mejor_max_val:.2f}")
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
