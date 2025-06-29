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
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
import torch


# Cargar modelo TrOCR base
processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")

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
zonas_definidas = [
    # (3, 11, -14),
    # (3, 11, -13),
    # (3, 11, -12),
    # (3, 11, -11),
    # (3, 10, -10),
    # Solo las válidas para -9
    # (3, 9, -9),    # por ejemplo, si solo existen 3 y 4
    # Solo las válidas para -8
    # (3, 3, -8),
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

    punto_final_x = None  # Para rastrear de dónde venimos

    for x1, x2, y in zonas_definidas:
        if punto_final_x is None:
            # Primera fila, usar orden natural
            x_inicio, x_fin = x1, x2
        else:
            # Si venimos de la izquierda, vamos a la derecha, y viceversa
            if punto_final_x <= x1:
                x_inicio, x_fin = x1, x2
            else:
                x_inicio, x_fin = x2, x1

        # Generar la fila con dirección adaptativa
        if x_inicio <= x_fin:
            for x in range(x_inicio, x_fin + 1):
                ruta_completa.append((x, y))
            punto_final_x = x_fin
        else:
            for x in range(x_inicio, x_fin - 1, -1):
                ruta_completa.append((x, y))
            punto_final_x = x_fin

def extraer_coordenadas(texto):
    # Limpiar texto
    texto = texto.strip().replace(" ", ",").replace("–", "-").replace("—", "-")

    # Intentar emparejar coordenadas tipo: 56,-4 o 56,- 4 o -12,3
    match = re.search(r"-?\d+\s*[, ]\s*-?\d+", texto)
    if match:
        partes = re.split(r"[, ]", match.group())
        try:
            x = int(partes[0])
            y = int(partes[1])
            return x, y
        except:
            return None
    return None

def ocr_dual(gray):
    # Usar TrOCR como OCR principal
    try:
        # Convertir la imagen a formato PIL
        img_pil = Image.fromarray(gray).convert("RGB")
        
        # Preprocesar con TrOCR
        inputs = processor(images=img_pil, return_tensors="pt")
        outputs = model.generate(**inputs)
        texto_trocr = processor.batch_decode(outputs, skip_special_tokens=True)[0].strip()

        print(f"🧠 TrOCR resultado: '{texto_trocr}'")

        match = re.search(r"-?\d+,-?\d+", texto_trocr)
        if match:
            x_str, y_str = match.group().split(",")
            return int(x_str), int(y_str)

    except Exception as e:
        print(f"❌ TrOCR falló: {e}")

    # === TESSERACT (respaldo) ===
    print("🔁 TrOCR falló. Probando con Tesseract...")

    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    t_gray = cv2.convertScaleAbs(blur, alpha=1.5, beta=10)
    t_thresh = cv2.adaptiveThreshold(t_gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 13, 5)

    texto_tess = pytesseract.image_to_string(t_thresh, config='--psm 7').strip()
    print(f"📝 Tesseract resultado: '{texto_tess}'")

    match = re.search(r"-?\d+\s*[,.-]\s*-?\d+", texto_tess)
    if match:
        coord_text = match.group().replace(" ", "").replace(".", ",").replace("-", ",-") if match.group().count("-") == 1 else match.group()
        partes = re.split(r"[,.-]", coord_text)
        if len(partes) == 2:
            try:
                return int(partes[0]), int(partes[1])
            except:
                pass

    print("❌ Ningún OCR pudo extraer coordenadas.")
    return None


# Lee coordenadas de pantalla
def obtener_coordenadas_actuales():
    if not buscando:
        return None

    # Captura de pantalla de la región de control
    captura = pyautogui.screenshot(region=zona_control)
    img = np.array(captura)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Escalar para mejorar resolución (beneficia a TrOCR y Tesseract)
    upscale = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    # Filtro suave para eliminar ruido sin dañar caracteres
    filtrado = cv2.bilateralFilter(upscale, 9, 75, 75)
    ajustado = cv2.convertScaleAbs(filtrado, alpha=1.3, beta=5)

    # Guardar imagen para depuración
    cv2.imwrite("ocr_final_input.png", ajustado)

    # Pasar la imagen a la función de OCR
    return ocr_dual(ajustado)

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

    # Click en el chat (X=801, Y=744)
    pyautogui.click(x=730, y=739)
    time.sleep(0.3)

    # Escribir comando
    pyautogui.write(f"/travel {x} {y}", interval=0.05)
    keyboard.press_and_release("enter")
    time.sleep(0.3)

    # Click en el botón de confirmación (X=1227, Y=440)
    pyautogui.click(x=1223, y=436)
    print("🧭 Comando /travel enviado y confirmado.")
    time.sleep(2.5)  # Espera a que se mueva el personaje

# 🛠️ Acción al fallar 3 veces
def al_fallar_3_veces():
    global imagen_referencia, buscando, programa_activo

    # Verificamos si está pausado antes de continuar
    if not buscando or not programa_activo:
        print("⏸️ Escaneo pausado. No se valida zona visual.")
        return

    # recorrer_zonas_definidas()
    print("⚠️ Se falló 3 veces. Verificando cambio visual en zona...")

    coord = obtener_coordenadas_actuales()
    print(coord)

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
