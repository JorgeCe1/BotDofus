import keyboard
import pyautogui
import time
import sys
import win32api
import win32con

# Variable global para controlar el estado de seguimiento de clicks
tracking_clicks = False
# Lista para almacenar las posiciones de los clicks
click_positions = []
# Tiempo en segundos para ignorar clicks justo después de cambiar el estado
COOLDOWN_TIME = 0.15  # 150 milisegundos
# Variable para registrar el último momento en que se cambió el estado de tracking
last_state_change_time = 0

# Estado del botón izquierdo del mouse
mouse_pressed_last = False

def al_presionar_f5():
    global tracking_clicks, last_state_change_time
    if not tracking_clicks:
        print("F5 presionado: Iniciando el seguimiento de clicks...")
        tracking_clicks = True
        last_state_change_time = time.time()
    else:
        print("F5 presionado: El seguimiento de clicks ya está activo.")

def al_presionar_f6():
    global tracking_clicks, click_positions, last_state_change_time
    if tracking_clicks:
        print("F6 presionado: Pausando el seguimiento de clicks...")
        tracking_clicks = False
        last_state_change_time = time.time()

        if click_positions:
            print("\n--- Posiciones de Clicks Recolectadas ---")
            for i, pos in enumerate(click_positions):
                print(f"Click {i+1}: X={pos[0]}, Y={pos[1]}")
            print("------------------------------------------")
            click_positions = []  # Limpiar lista después de mostrar
            print("Historial de clicks limpiado.")
        else:
            print("No se recolectaron clicks durante este periodo de seguimiento.")
    else:
        print("F6 presionado: El seguimiento de clicks ya está pausado. Presiona F5 para iniciar.")
        if click_positions:
            print("\n--- Posiciones de Clicks Recolectadas ---")
            for i, pos in enumerate(click_positions):
                print(f"Click {i+1}: X={pos[0]}, Y={pos[1]}")
            print("------------------------------------------")
        else:
            print("No hay clicks recolectados para mostrar.")

def salir():
    print("\nSaliendo del programa.")
    sys.exit()

def main():
    global mouse_pressed_last

    print("Presiona F5 para iniciar el seguimiento de clicks.")
    print("Presiona F6 para pausar el seguimiento de clicks y ver los clicks recolectados.")
    print("Presiona F7 para salir del programa.")

    keyboard.add_hotkey('f5', al_presionar_f5)
    keyboard.add_hotkey('f6', al_presionar_f6)
    keyboard.add_hotkey('f7', salir)

    while True:
        if tracking_clicks:
            if time.time() - last_state_change_time > COOLDOWN_TIME:
                # Detectar si el botón izquierdo está presionado ahora
                mouse_pressed_now = win32api.GetAsyncKeyState(win32con.VK_LBUTTON) < 0

                # Si antes no estaba presionado y ahora sí, es un nuevo click
                if mouse_pressed_now and not mouse_pressed_last:
                    x, y = pyautogui.position()
                    click_positions.append((x, y))
                    print(f"Click detectado y guardado en: X={x}, Y={y}")

                mouse_pressed_last = mouse_pressed_now
            else:
                mouse_pressed_last = win32api.GetAsyncKeyState(win32con.VK_LBUTTON) < 0

        time.sleep(0.01)  # Evitar uso excesivo de CPU

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        pass
    except Exception as e:
        print(f"Ocurrió un error: {e}")
