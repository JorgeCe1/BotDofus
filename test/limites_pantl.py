import keyboard
import pyautogui
import win32api
import win32con
import time
import sys # Importar sys para salir del programa

def get_mouse_coordinates():
    """
    Obtiene e imprime las coordenadas actuales del mouse en la pantalla.
    Presiona 'F6' para detener la detección.
    """
    print("\n--- Detección de Coordenadas ---")
    print("Mueve el mouse para ver las coordenadas. Presiona 'F6' para detener.")
    try:
        while True:
            x, y = pyautogui.position()
            print(f"Coordenadas actuales del mouse: X={x}, Y={y}", end='\r')
            time.sleep(0.05) # Pequeña pausa para no sobrecargar la CPU
            if keyboard.is_pressed('f6'):
                print("\nDeteniendo la detección de coordenadas.")
                break
    except KeyboardInterrupt:
        print("\nDeteniendo la detección de coordenadas.")

def set_screen_limits():
    """
    Permite al usuario definir límites de pantalla haciendo clic con el mouse.
    Se necesitan dos clics: uno para la esquina superior izquierda y otro para la inferior derecha.
    Presiona 'F6' en cualquier momento para cancelar.
    """
    print("\n--- Configuración de Límites de Pantalla ---")
    print("Haz clic en la esquina SUPERIOR IZQUIERDA del área de trabajo.")
    print("Espera 3 segundos para que puedas posicionar el mouse. Presiona 'F6' para cancelar.")
    time.sleep(3)

    if keyboard.is_pressed('f6'):
        print("\nConfiguración de límites cancelada.")
        return None

    # Espera un clic del botón izquierdo del mouse o la tecla F6
    while not win32api.GetAsyncKeyState(win32con.VK_LBUTTON) and not keyboard.is_pressed('f6'):
        pass
    if keyboard.is_pressed('f6'):
        print("\nConfiguración de límites cancelada.")
        return None
    x1, y1 = pyautogui.position()
    print(f"Esquina Superior Izquierda definida: X={x1}, Y={y1}")

    print("\nAhora haz clic en la esquina INFERIOR DERECHA del área de trabajo.")
    print("Espera 3 segundos para que puedas posicionar el mouse. Presiona 'F6' para cancelar.")
    time.sleep(3)

    if keyboard.is_pressed('f6'):
        print("\nConfiguración de límites cancelada.")
        return None

    # Espera un clic del botón izquierdo del mouse o la tecla F6
    while not win32api.GetAsyncKeyState(win32con.VK_LBUTTON) and not keyboard.is_pressed('f6'):
        pass
    if keyboard.is_pressed('f6'):
        print("\nConfiguración de límites cancelada.")
        return None
    x2, y2 = pyautogui.position()
    print(f"Esquina Inferior Derecha definida: X={x2}, Y={y2}")

    # Asegura que las coordenadas sean correctas para definir el área (min X, min Y, max X, max Y)
    min_x = min(x1, x2)
    min_y = min(y1, y2)
    max_x = max(x1, x2)
    max_y = max(y1, y2)

    width = max_x - min_x
    height = max_y - min_y

    print(f"\nLímites de pantalla definidos:")
    print(f"  Punto de inicio (superior izquierda): ({min_x}, {min_y})")
    print(f"  Punto final (inferior derecha): ({max_x}, {max_y})")
    print(f"  Ancho del área: {width}, Altura del área: {height}")

    return (min_x, min_y, width, height)

def main_menu():
    """Muestra el menú principal y espera la entrada del usuario."""
    print("\n--- Menú Principal ---")
    print("1. Detectar coordenadas del mouse en tiempo real.")
    print("2. Definir límites de pantalla con el mouse.")
    print("Presiona F5 para iniciar la función seleccionada.")
    print("Presiona F6 en cualquier momento para detener la función activa o salir del programa.")
    print("----------------------")

    choice = ""
    while choice not in ['1', '2']:
        choice = input("Ingresa tu elección (1 o 2): ")
        if choice not in ['1', '2']:
            print("Opción no válida. Por favor, elige 1 o 2.")
    return choice

if __name__ == "__main__":
    while True:
        # 1. Mostrar menú y obtener la elección
        selected_option = main_menu()

        # 2. Esperar F5 para iniciar la función seleccionada
        print(f"Has elegido la opción {selected_option}. Esperando que presiones F5 para iniciar...")
        keyboard.wait('f5')

        # 3. Ejecutar la función basada en la elección
        if selected_option == '1':
            get_mouse_coordinates()
        elif selected_option == '2':
            screen_limits = set_screen_limits()
            if screen_limits:
                print("\n¡Límites de pantalla establecidos! Puedes usar estas coordenadas para tus automatizaciones.")

        # 4. Ofrecer volver al menú o salir
        print("\nFunción terminada. Presiona F6 para salir del programa, o cualquier otra tecla para volver al menú principal.")
        if keyboard.read_key() == 'f6': # Usamos read_key() para una espera más explícita
            print("Saliendo del programa.")
            sys.exit() # Salir del programa limpiamente
        else:
            print("Volviendo al menú principal...")

# Límites de pantalla definidos:
  
#   Punto de inicio (superior izquierda): (324, 14)
#   Punto final (inferior derecha): (1585, 911)
#   Ancho del área: 1261, Altura del área: 897
  
# Límites de pantalla definidos:
#   Punto de inicio (superior izquierda): (323, 18)
#   Punto final (inferior derecha): (1594, 917)
#   Ancho del área: 1271, Altura del área: 899
  
# Límites de pantalla definidos:
#   Punto de inicio (superior izquierda): (322, 15)
#   Punto final (inferior derecha): (1595, 922)
#   Ancho del área: 1273, Altura del área: 907
  
# Límites de pantalla definidos:
#   Punto de inicio (superior izquierda): (322, 14)
#   Punto final (inferior derecha): (1598, 921)
#   Ancho del área: 1276, Altura del área: 907