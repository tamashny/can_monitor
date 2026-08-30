# test_port.py
import serial
import serial.tools.list_ports
import time

PORT_TO_TEST = "COM10"  # или "CNCA2"

print(f"Проверка порта {PORT_TO_TEST}...")

# Сначала проверим, существует ли порт
ports = serial.tools.list_ports.comports()
port_exists = False
for port in ports:
    if port.device == PORT_TO_TEST:
        port_exists = True
        print(f"✅ Порт {PORT_TO_TEST} существует")
        break

if not port_exists:
    print(f"❌ Порт {PORT_TO_TEST} НЕ СУЩЕСТВУЕТ!")
    print("Проверьте настройки com0com")
    input("Нажмите Enter...")
    exit()

# Попытка открыть порт
try:
    ser = serial.Serial(
        port=PORT_TO_TEST,
        baudrate=115200,
        timeout=1,
        write_timeout=1
    )
    print(f"✅ Порт {PORT_TO_TEST} успешно открыт!")
    
    # Проверка чтения/записи
    ser.write(b"test\r")
    time.sleep(0.1)
    
    ser.close()
    print("✅ Порт закрыт")
    
except serial.SerialException as e:
    print(f"❌ Ошибка открытия порта {PORT_TO_TEST}:")
    print(f"   {e}")
    print("\nВозможные причины:")
    print("1. Порт занят другим приложением (терминал, другой симулятор)")
    print("2. Нет прав доступа (запустите от администратора)")
    print("3. Порт не существует или отключен")
    
except Exception as e:
    print(f"❌ Другая ошибка: {e}")

input("\nНажмите Enter для выхода...")