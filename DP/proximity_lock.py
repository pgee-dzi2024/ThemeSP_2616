import asyncio
import time
import configparser
import ctypes
import os
import logging
from collections import deque
from bleak import BleakScanner

# --- 1. Настройки на пътищата ---
current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, 'config.ini')
log_path = os.path.join(current_dir, 'security.log')

# --- 2. Конфигуриране на логъра ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path, encoding='utf-8'),
        logging.StreamHandler()  # Запазваме принтирането и в конзолата за тестове
    ]
)

if not os.path.exists(config_path):
    logging.error(f"Файлът не е намерен: {config_path}")
    exit(1)

config = configparser.ConfigParser()
config.read(config_path, encoding='utf-8')

try:
    TOKEN_MAC = config['Settings']['TOKEN_MAC'].upper()
    LOCK_THRESHOLD = int(config['Settings']['LOCK_THRESHOLD'])
    MA_WINDOW_SIZE = int(config['Settings']['MA_WINDOW_SIZE'])
    TIMEOUT_SECONDS = int(config['Settings']['TIMEOUT_SECONDS'])
except KeyError as e:
    logging.error(f"Липсва ключ в config.ini: {e}")
    exit(1)

rssi_history = deque(maxlen=MA_WINDOW_SIZE)
last_seen_time = time.time()
is_locked = False


def lock_computer():
    global is_locked
    if not is_locked:
        logging.warning("СИГНАЛ ЗА ЗАКЛЮЧВАНЕ! Компютърът се заключва.")
        ctypes.windll.user32.LockWorkStation()
        is_locked = True


def detection_callback(device, advertisement_data):
    global last_seen_time, is_locked

    if device.address.upper() == TOKEN_MAC:
        current_rssi = advertisement_data.rssi
        last_seen_time = time.time()
        rssi_history.append(current_rssi)

        avg_rssi = sum(rssi_history) / len(rssi_history)

        if is_locked and avg_rssi > (LOCK_THRESHOLD + 5):
            logging.info(f"Токенът е близо (Средно: {avg_rssi:.1f} dBm). Очаква се ръчно отключване.")
            is_locked = False


async def main():
    logging.info(f"Стартиране... Търсим токен с MAC: {TOKEN_MAC}")
    scanner = BleakScanner(detection_callback=detection_callback)
    await scanner.start()

    try:
        while True:
            await asyncio.sleep(1)
            time_since_last_seen = time.time() - last_seen_time
            print(f"Токенът е видян последно преди {time_since_last_seen:.1f} сек. Средната сила на сигнала е {sum(rssi_history) / MA_WINDOW_SIZE} dBm.")

            if time_since_last_seen > TIMEOUT_SECONDS and not is_locked:
                logging.warning(f"Токенът е изгубен за повече от {TIMEOUT_SECONDS} сек!")
                lock_computer()
                rssi_history.clear()

            elif len(rssi_history) == MA_WINDOW_SIZE:
                avg_rssi = sum(rssi_history) / MA_WINDOW_SIZE
                if avg_rssi < LOCK_THRESHOLD and not is_locked:
                    logging.warning(f"Сигналът е твърде слаб (Средно: {avg_rssi:.1f} dBm).")
                    lock_computer()

    except asyncio.CancelledError:
        pass
    finally:
        await scanner.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Програмата е спряна от потребителя.")