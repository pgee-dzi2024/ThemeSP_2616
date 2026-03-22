import asyncio
from bleak import BleakScanner


# Callback функция, която се извиква при всяко засечено BLE устройство
def detection_callback(device, advertisement_data):
    # Вземаме името на устройството (ако има такова), MAC адреса и силата на сигнала (RSSI)
    name = device.name if device.name else "Неизвестно устройство"
    mac_address = device.address
    rssi = advertisement_data.rssi

    # Принтираме данните в конзолата
    print(f"Име: {name:<25} | MAC: {mac_address} | RSSI: {rssi} dBm")


async def run_scanner():
    print("Стартиране на BLE сканиране...")
    print("Натисни Ctrl+C за спиране.\n")
    print("-" * 65)

    # Инициализираме скенера и му подаваме callback функцията
    scanner = BleakScanner(detection_callback=detection_callback)

    try:
        await scanner.start()
        # Скенерът работи асинхронно, затова просто "чакаме" безкрайно
        # докато потребителят не спре програмата
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        # Важно е да спрем скенера коректно при изход
        await scanner.stop()
        print("\nСканирането е спряно.")


if __name__ == "__main__":
    try:
        # Стартиране на асинхронния цикъл
        asyncio.run(run_scanner())
    except KeyboardInterrupt:
        print("\nПрограмата е прекъсната от потребителя.")

# Име: HC-05                     | MAC: 36:33:AB:AE:EB:AB | RSSI: -62 dBm