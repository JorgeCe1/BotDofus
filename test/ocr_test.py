import cv2
import pytesseract
from PIL import Image
import numpy as np
import re
import pyautogui

# Ruta Tesseract (si no está en PATH)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Región de comparación visual (coordenadas absolutas)
zona_x = 0
zona_y = 67
zona_w = 92
zona_h = 32
zona_control = (zona_x, zona_y, zona_w, zona_h)

def extraer_coordenadas(texto):
    texto = texto.strip().lower()
    texto = texto.replace("–", "-").replace("—", "-")
    texto = re.sub(r"[^\d\-,]", "", texto)  # deja solo números, comas y guiones

    print(f"📤 Texto limpiado (crudo): '{texto}'")

    # Intento de corrección para casos como -13-61 (sin coma)
    if re.fullmatch(r"-?\d+-\d+", texto):  # exactamente dos números seguidos por guión
        partes = texto.split("-")
        if len(partes) == 3:
            # Ej: "-13-61" → ["", "13", "61"]
            texto = f"-{partes[1]},-{partes[2]}"
        elif len(partes) == 2:
            # Ej: "13-61" → ["13", "61"]
            texto = f"{partes[0]},-{partes[1]}"
        print(f"📤 Texto corregido: '{texto}'")

    # Elimina signos extra al principio/final
    texto = re.sub(r"^-+|[-,]+$", "", texto)

    # Buscar patrón correcto
    match = re.search(r"-?\d+,-?\d+", texto)
    if match:
        try:
            x_str, y_str = match.group().split(",")
            return int(x_str), int(y_str)
        except ValueError:
            return None

    # Alternativa
    numeros = re.findall(r"-?\d+", texto)
    if len(numeros) >= 2:
        try:
            return int(numeros[0]), int(numeros[1])
        except:
            pass

    return None

def ocr_con_colores_originales(ruta_imagen):
    # img = cv2.imread(ruta_imagen)
    captura = pyautogui.screenshot(region=zona_control)
    img = np.array(captura)
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)  # <- conversión correcta
    cv2.imwrite("verificacion.png", img_bgr)

    if img is None:
        print("❌ No se pudo cargar la imagen.")
        return None

    # ⚠️ Ajuste más suave de nitidez y contraste
    # upscaled = cv2.resize(img, None, fx=4, fy=3, interpolation=cv2.INTER_CUBIC)
    upscaled = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    contraste = cv2.convertScaleAbs(upscaled, alpha=1.5, beta=10)
    filtered = cv2.bilateralFilter(contraste, 9, 75, 75)
    gray = cv2.cvtColor(filtered, cv2.COLOR_BGR2GRAY)
    binaria = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV, 15, 8
    )

    # cv2.imwrite("revision/binaria.png", binaria)  # Guardar para revisión
    # cv2.imwrite("revision/gray.png", gray)  # Guardar para revisión
    # cv2.imwrite("revision/filtered.png", filtered)  # Guardar para revisión
    # cv2.imwrite("revision/contraste.png", contraste)  # Guardar para revisión
    # cv2.imwrite("revision/upscaled.png", upscaled)  # Guardar para revisión

    # 🧠 OCR directo sin invertir colores
    pil_img = Image.fromarray(upscaled)

    # 📌 Usar whitelist pero con parámetros más seguros
    # config = "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789,-"
    config = "--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789,-"

    texto = pytesseract.image_to_string(pil_img, config=config)
    print(f"📝 Texto crudo: {texto}")

    coords = extraer_coordenadas(texto)
    print(f"📌 Coordenadas detectadas: {coords}")
    # custom_config = r'--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789,-'
    # texto = pytesseract.image_to_string(binaria, config=custom_config)
    # print(f"📝 Texto crudo binaria: {texto}")
    # coords = extraer_coordenadas(texto)
    # print(f"📌 Coordenadas detectadas binaria: {coords}")
    return coords

# Ejecutar
if __name__ == "__main__":
    ocr_con_colores_originales("imagen.png")  # Usa la imagen que desees
