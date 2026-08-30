import serial
import time
import threading
import struct
import random

class SLCANSimulator:
    def __init__(self, port, baudrate=115200):
        """
        Инициализация симулятора SLCAN.
        :param port: Имя COM-порта для отправки данных (например, 'COM8')
        :param baudrate: Скорость порта (должна совпадать с config.json)
        """
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.running = False
        self.sim_thread = None

    def start(self):
        """Запускает симулятор и начинает отправку кадров."""
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=0.1)
            self.running = True
            print(f"[SIMULATOR] Запущен на порту {self.port} со скоростью {self.baudrate}")

            # Запускаем поток для отправки кадров
            self.sim_thread = threading.Thread(target=self._send_loop, daemon=True)
            self.sim_thread.start()
        except Exception as e:
            print(f"[SIMULATOR] Ошибка запуска: {e}")

    def stop(self):
        """Останавливает симулятор."""
        self.running = False
        if self.serial:
            self.serial.close()
            print("[SIMULATOR] Остановлен.")

    def _send_slcan_command(self, cmd: str):
        """
        Отправляет SLCAN-команду в порт.
        Все команды должны заканчиваться на '\r' [citation:6][citation:10].
        """
        if not self.serial or not self.serial.is_open:
            return
        try:
            # Добавляем '\r', если его нет
            if not cmd.endswith('\r'):
                cmd += '\r'
            self.serial.write(cmd.encode('ascii'))
            # Небольшая задержка, чтобы не переполнять буфер
            time.sleep(0.001)
        except Exception as e:
            print(f"[SIMULATOR] Ошибка отправки команды '{cmd}': {e}")

    def _send_can_frame(self, can_id: int, data: bytes, is_extended: bool = False):
        """
        Формирует и отправляет CAN-кадр в формате SLCAN [citation:6][citation:10].
        Пример для стандартного ID: t123D112233\r
        """
        # Определяем первый символ команды [citation:10]
        cmd_type = 'T' if is_extended else 't'
        # ID в HEX (3 символа для стандартного, 8 для расширенного)
        id_str = f"{can_id:08X}" if is_extended else f"{can_id:03X}"
        # DLC в HEX (1 символ)
        dlc_str = f"{len(data):X}"
        # Данные в HEX
        data_str = ''.join(f"{b:02X}" for b in data)

        command = f"{cmd_type}{id_str}{dlc_str}{data_str}"
        self._send_slcan_command(command)

    def _send_loop(self):
        """Основной цикл генерации и отправки CAN-кадров."""
        # Инициализация переменных для динамических данных
        voltage = 600.0
        current = 0.0
        ne_status = 0
        imd_status = 0
        cc_status = 0
        dc_status = 0
        so_status = 0
        counter = 0

        print("[SIMULATOR] Начинаю генерацию кадров...")

        while self.running:
            try:
                # --- Генерация кадра 0x217 (Напряжение и Ток) ---
                # Имитация изменения параметров
                voltage += random.uniform(-1.0, 1.0)
                current += random.uniform(-2.0, 2.0)
                voltage = max(550, min(650, voltage))
                current = max(-100, min(100, current))

                voltage_raw = int(voltage * 10)  # 0.1В/бит
                current_raw = int(current * 10)  # 0.1А/бит
                data_217 = struct.pack('<HH', voltage_raw, current_raw)
                self._send_can_frame(0x217, data_217)
                # print(f"[SIMULATOR] Отправлен кадр 0x217: {data_217.hex()}")

                # --- Генерация кадра 0x187 (Состояния систем) ---
                if random.random() < 0.01:  # 1% шанс изменения состояния
                    ne_status = random.randint(0, 2)
                    imd_status = random.randint(0, 2)
                    cc_status = random.randint(0, 2)
                    dc_status = random.randint(0, 2)
                    so_status = random.randint(0, 2)
                data_187 = bytes([
                    ne_status,  # НЭ
                    imd_status,          # Изоляция 
                    cc_status,          # Контроллер ячеек
                    dc_status,          # Преобразователь 
                    so_status           # Охлаждение 
                ])
                self._send_can_frame(0x187, data_187)

                # --- Генерация дополнительных кадров для демонстрации ---
                # Кадр 0x197 (Контроллер конденсаторов)
                if counter % 2 == 0:  # Отправляем с вдвое меньшей частотой (50ms)
                    status = 1  # OK
                    error_bits = 0
                    if random.random() < 0.005:
                        error_bits = 1 << random.randint(0, 6)
                    data_197 = bytes([status, error_bits])
                    self._send_can_frame(0x197, data_197)

                # Кадр 0x198 (Преобразователь)
                if counter % 5 == 0:
                    state = random.choices([2, 3, 4], weights=[0.8, 0.1, 0.1])[0]  # IDLE, CHARGE, DISCHARGE
                    error_code = 0
                    if random.random() < 0.005:
                        error_code = 1 << random.randint(1, 4)
                    data_198 = bytes([state, error_code])
                    self._send_can_frame(0x198, data_198)

                # Кадр 0x001 (Данные поезда)
                if counter % 10 == 0:
                    train_data = bytes([
                        1,  # BATTERY_MODE: автономный ход
                        2,  # TRAIN_POSITION: тоннель
                        0,  # резерв
                        1,  # MOTION_MODE: ход
                        50  # HANDLER_POSITION
                    ])
                    self._send_can_frame(0x001, train_data)

                # Кадр 0x002 (Состояние накопителя)
                if counter % 25 == 0:
                    system_status = random.randint(0, 3)
                    subsystems = 0
                    if random.random() < 0.03:
                        subsystems |= (1 << 2)  # CVC_ALARM
                    data_002 = bytes([system_status, subsystems & 0xFF, (subsystems >> 8) & 0xFF, 0, 0])
                    self._send_can_frame(0x002, data_002)

                counter += 1
                # Пауза 50 мс для имитации цикла ~20 кадров в секунду
                time.sleep(0.05)

            except Exception as e:
                print(f"[SIMULATOR] Ошибка в цикле генерации: {e}")
                time.sleep(0.1)

# --- Точка входа для запуска симулятора ---
if __name__ == "__main__":
    # !!! ВАЖНО: Укажите здесь ВТОРОЙ порт из созданной пары !!!
    # Например, если вы создали пару COM7 и COM8, и config.json использует COM7,
    # то симулятор должен использовать COM8.
    SIMULATOR_PORT = "COM11"  # Замените на ваш второй порт

    simulator = SLCANSimulator(SIMULATOR_PORT, 115200)
    try:
        simulator.start()
        print("[SIMULATOR] Работает. Нажмите Ctrl+C для остановки.")
        # Бесконечный цикл для поддержания работы
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SIMULATOR] Получен сигнал остановки.")
    finally:
        simulator.stop()