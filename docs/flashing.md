# Прошивка с Windows

## Что установлено на ноутбуке

- Python 3.12 (через Python install manager)
- ESPHome 2026.10.x: `py -3.12 -m pip install esphome`
- Git for Windows

## Проблема: русское имя пользователя

Имя пользователя Windows — «Семья». С русскими буквами в пути ESP-IDF (сборка для ESP32) не работает. Поэтому всё складывается в `C:\esphome`, и это делает `esp.bat`:

- Python запускается по полному пути из `%USERPROFILE%`.
- `LOCALAPPDATA`, `TEMP`, `TMP` перенаправлены в `C:\esphome\...`.
- `PLATFORMIO_CORE_DIR=C:\esphome\pio`, `ESPHOME_ESP_IDF_PREFIX=C:\esphome\idf`.
- Перед сборкой удаляется `CMakeCache.txt`: в нём русский путь ломает повторную сборку (`UnicodeDecodeError`).
- Перед сборкой выполняется `git pull`, то есть всегда берётся свежая версия с GitHub.

## Как прошить

```
C:\esphome\home_smart\esp.bat ekran.yaml      # экран, по кабелю это COM5
C:\esphome\home_smart\esp.bat teplopol.yaml   # плата реле
```

ESPHome спросит, куда прошивать: в COM-порт (кабель) или по Wi-Fi (OTA).

Если Windows не находит `ekran.local` (ошибка `Error resolving IP address`), укажите IP вручную:
```
esp.bat ekran.yaml 192.168.1.121
```
IP устройства видно в роутере или в журнале при прошивке кабелем (`IP Address:`). Чтобы IP не менялся, закрепите его в роутере (резервирование DHCP).

### Плата реле кабелем (если OTA не работает)
1. Отсоединить провод SCL от вывода RXD.
2. CP2102: TX→RX, RX→TX, GND→GND. GPIO0 замкнуть на GND и подать питание.
3. Прошить, вернуть SCL на место.

## secrets.yaml

Лежит рядом с yaml-файлами, в GitHub не попадает. Образец: `secrets.example.yaml`.
