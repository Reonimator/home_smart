# Умный дом — прошивки ESPHome

- `teplopol.yaml` — плата реле (ESP12F_Relay_X8): 7 зон + котёл
- `ekran.yaml` — сенсорный экран 7" (ESP32-8048S070C)
- `esp.bat` — забирает свежие файлы с GitHub и прошивает: `esp.bat ekran.yaml`
- `secrets.yaml` — пароль Wi-Fi, лежит только на ноутбуке, в GitHub не попадает:
  `wifi_password: "пароль"`

## Первый запуск на ноутбуке
```
cd C:\esphome
git clone https://github.com/Reonimator/home_smart
```
Положить `secrets.yaml` в `C:\esphome\home_smart`, затем: `C:\esphome\home_smart\esp.bat ekran.yaml`
