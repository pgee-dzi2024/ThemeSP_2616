import asyncio
import time
import configparser
import ctypes
import os # <-- ДОБАВЯМЕ ТОВА
from collections import deque
from bleak import BleakScanner

# --- 1. Намиране и четене на конфигурацията от config.ini ---
# Вземаме точната папка, в която се намира текущият скрипт
current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, 'config.ini')

# Проверяваме изрично дали файлът съществува
if not os.path.exists(config_path):
    print(f"КРИТИЧНА ГРЕШКА: Файлът не е намерен тук: {config_path}")
    print("Моля, създай config.ini в същата папка.")
    exit(1)

config = configparser.ConfigParser()
config.read(config_path, encoding='utf-8')

try:
    TOKEN_MAC = config['Settings']['TOKEN_MAC'].upper()
    LOCK_THRESHOLD = int(config['Settings']['LOCK_THRESHOLD'])
    MA_WINDOW_SIZE = int(config['Settings']['MA_WINDOW_SIZE'])
    TIMEOUT_SECONDS = int(config['Settings']['TIMEOUT_SECONDS'])
except KeyError as e:
    print(f"Грешка: Липсва ключ в config.ini: {e}")
    print("Увери се, че файлът започва с [Settings].")
    exit(1)


# --- 2. Глобални променливи за състоянието ---
# deque автоматично премахва най-старата стойност, когато достигне максималния размер (MA_WINDOW_SIZE)
rssi_history = deque(maxlen=MA_WINDOW_SIZE)
last_seen_time = time.time()
is_locked = False


# --- 3. Функция за заключване ---
def lock_computer():
    global is_locked
    if not is_locked:
        print(f"\n[{time.strftime('%H:%M:%S')}] СИГНАЛ ЗА ЗАКЛЮЧВАНЕ! Компютърът се заключва.")
        # Команда за заключване на Windows (Workstation Lock)
#        ctypes.windll.user32.LockWorkStation()
        is_locked = True


# --- 4. Callback при засичане на устройство ---
def detection_callback(device, advertisement_data):
    global last_seen_time, is_locked

    if device.address.upper() == TOKEN_MAC:
        current_rssi = advertisement_data.rssi

        # Обновяваме времето на последно виждане и добавяме стойността в опашката
        last_seen_time = time.time()
        rssi_history.append(current_rssi)

        # Изчисляваме Moving Average (осреднена стойност)
        avg_rssi = sum(rssi_history) / len(rssi_history)

        # Ако сме се доближили (сигналът е над прага + малък буфер (хистерезис), за да не превключва постоянно)
        if is_locked and avg_rssi > (LOCK_THRESHOLD + 5):
            print(
                f"[{time.strftime('%H:%M:%S')}] Токенът е близо (Средно: {avg_rssi:.1f} dBm). Очаква се ръчно отключване.")
            is_locked = False

        # Само за дебъгване - принтираме текущото състояние в конзолата
        print(f"Текущо: {current_rssi} dBm | Средно: {avg_rssi:.1f} dBm | Брой извадки: {len(rssi_history)}", end="\r")


# --- 5. Основен цикъл на програмата ---
async def main():
    print(f"Стартиране... Търсим токен с MAC: {TOKEN_MAC}")
    scanner = BleakScanner(detection_callback=detection_callback)
    await scanner.start()

    try:
        while True:
            await asyncio.sleep(1)

            # Проверяваме дали токенът не се е изгубил напълно
            time_since_last_seen = time.time() - last_seen_time
            if time_since_last_seen > TIMEOUT_SECONDS and not is_locked:
                print(f"\n[{time.strftime('%H:%M:%S')}] Токенът е изгубен за повече от {TIMEOUT_SECONDS} сек!")
                lock_computer()
                rssi_history.clear()  # Изчистваме историята, защото устройството го няма

            # Проверяваме дали средната стойност не е паднала под прага
            elif len(rssi_history) == MA_WINDOW_SIZE:
                avg_rssi = sum(rssi_history) / MA_WINDOW_SIZE
                if avg_rssi < LOCK_THRESHOLD and not is_locked:
                    print(f"\n[{time.strftime('%H:%M:%S')}] Сигналът е твърде слаб (Средно: {avg_rssi:.1f} dBm).")
                    lock_computer()

    except asyncio.CancelledError:
        pass
    finally:
        await scanner.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nПрограмата е спряна.")