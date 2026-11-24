# Домашний сервер на ноутбуке HP (Proxmox + Home Assistant OS)

Ноутбук: HP, Intel Core i7-4700MQ (4 ядра / 8 потоков), 8 ГБ DDR3L, жёсткий диск (HDD), Windows 10 — стираем полностью.
Задачи сервера: Home Assistant (пол, экран, Нептун, позже Алиса, Mosquitto), камеры с регистратора XVR, телевизор LG webOS, тестовые виртуальные машины.

**В интернет ничего не открываем.** Никаких пробросов портов на роутере. Удалённый доступ (VPN) — на паузе, см. `plan.md`.

## 1. Что докупить

| Что | Зачем | Ориентир цены (оценка) |
|---|---|---|
| SSD 2,5″ SATA 512 ГБ (Samsung 870 EVO, Crucial MX500, Kingston KC600, WD Blue) | HDD медленный и шумный, Home Assistant пишет на диск постоянно | 3–5 тыс. ₽ |
| Память DDR3L-1600 SO-DIMM, 2 × 8 ГБ (именно **DDR3L**, 1,35 В) | 8 ГБ мало для Proxmox + HA + тестов | 2–3 тыс. ₽ б/у |
| Патч-корд RJ-45 нужной длины | Proxmox работает по кабелю, не по Wi-Fi | 200–500 ₽ |
| Флешка от 4 ГБ (любая, будет стёрта) | Установщик Proxmox | есть дома |

Перед покупкой памяти проверить модель ноутбука (наклейка снизу) и число слотов: в большинстве HP с i7-4700MQ два слота, максимум 16 ГБ.
Можно начать и на 8 ГБ и старом HDD, а SSD поставить потом — но тогда всё придётся ставить заново. Лучше сразу с SSD.

## 2. Загрузочная флешка (на любом компьютере с Windows)

1. Скачать ISO **Proxmox VE** (последняя версия): https://www.proxmox.com/en/downloads → Proxmox Virtual Environment → ISO Installer.
2. Скачать **Rufus**: https://rufus.ie (или balenaEtcher).
3. Rufus: выбрать флешку, выбрать ISO, «Старт». Если спросит режим — **DD-образ**.

## 3. Настройка BIOS ноутбука

Включить ноутбук и сразу жать **Esc** (у HP), затем **F10** — BIOS Setup.

- **Virtualization Technology (VT-x)** — Enabled (обычно System Configuration → Device Configurations / Virtualization). Без этого виртуальные машины не запустятся.
- **Secure Boot** — Disabled (Legacy можно не включать, UEFI оставить).
- Сохранить (F10). Потом при включении Esc → **F9** (Boot Menu) → выбрать флешку.

## 4. Установка Proxmox

Кабель к роутеру подключить **до** установки.

1. В меню выбрать **Install Proxmox VE (Graphical)**.
2. Target Harddisk — SSD, файловая система **ext4** (ZFS на 16 ГБ памяти не нужен).
3. Страна Russia, часовой пояс Europe/Moscow, раскладка — U.S. English.
4. Пароль root — надёжный, записать. E-mail — любой.
5. Сеть:
   - Management Interface — проводной (`enp…` / `eno…`), **не** `wlp…`.
   - Hostname: `pve.home.lan`
   - IP: `192.168.1.10/24` (адрес вне диапазона DHCP роутера; проверить в настройках роутера, что он свободен)
   - Gateway и DNS: адрес роутера (обычно `192.168.1.1`).
6. Install, после перезагрузки вынуть флешку.

Дальше всё делается с другого компьютера в той же сети: браузер → `https://192.168.1.10:8006` → пользователь `root`, realm «Linux PAM». Предупреждение о сертификате — «Всё равно перейти».

## 5. Донастройка Proxmox (Shell узла `pve`)

Выбрать в левом дереве `pve` → **Shell** и выполнить по очереди.

Чтобы ноутбук не засыпал при закрытой крышке:

```sh
sed -i 's/^#\?HandleLidSwitch=.*/HandleLidSwitch=ignore/; s/^#\?HandleLidSwitchExternalPower=.*/HandleLidSwitchExternalPower=ignore/; s/^#\?HandleLidSwitchDocked=.*/HandleLidSwitchDocked=ignore/' /etc/systemd/logind.conf
systemctl restart systemd-logind
```

Гасить экран через минуту (экономия и меньше нагрев):

```sh
sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="quiet"/GRUB_CMDLINE_LINUX_DEFAULT="quiet consoleblank=60"/' /etc/default/grub && update-grub
```

Бесплатные репозитории обновлений (без подписки) удобнее включить скриптом сообщества
«Proxmox VE Post Install» с https://community-scripts.github.io/ProxmoxVE/ (раздел Proxmox VE Tools) — на все вопросы ответить «yes», кроме «Disable high availability» → yes, «Reboot» → yes.

## 6. Виртуальная машина Home Assistant OS

Проще всего скриптом сообщества «Home Assistant OS VM» (страница: https://community-scripts.github.io/ProxmoxVE/ → поиск «Home Assistant OS»). Команда со страницы вставляется в Shell узла `pve`; выбрать **Default Settings**.
Скрипт создаст ВМ (2 ядра, 4 ГБ памяти, 32 ГБ диска) и запустит её.

После запуска: ВМ → Summary → IP-адрес. В браузере `http://<IP>:8123`, подождать 5–20 минут первичной подготовки, создать пользователя.

В настройках роутера закрепить за ВМ Home Assistant постоянный адрес (резервирование DHCP по MAC), например `192.168.1.11`.
ВМ → Options → **Start at boot: Yes** (скрипт обычно ставит сам — проверить).

## 7. Подключение к Home Assistant (через экран)

Home Assistant: `http://192.168.1.110:8123` (адрес закреплён в роутере). Proxmox: `https://192.168.1.10:8006`.

В Home Assistant тёплый пол виден **через экран** (ESP32-S3), а не через плату реле: у ESP8266 нет памяти на ещё одно соединение, а все данные зон экран и так получает от платы. Так же решено и для будущего приложения (см. `plan.md`).

Что экран отдаёт в Home Assistant (только чтение): «Пол N Комната» (°C), «Цель N Комната» (°C), «Греет N Комната», «Котёл», «Режим» (Дома / Дома, ночь / Ушёл), «Подсветка». Управление целями и режимом — по-прежнему с экрана.

### Прошивка экрана с сервера (без компьютера)

Дополнение **ESPHome Device Builder** в Home Assistant. Вся конфигурация экрана берётся с GitHub (`ekran_base.yaml`), на сервере хранятся только пароли.

1. ESPHome → ⋮ → **Secrets**: по одному добавить `wifi_ssid`, `wifi_password`, `ap_password`, `api_key_ekran` (ключ: на сервере `openssl rand -base64 32`).
2. Создать устройство `ekran` (ESP32-S3), открыть Edit, заменить всё на:

```yaml
substitutions:
  wifi_ssid: !secret wifi_ssid
  wifi_password: !secret wifi_password
  ap_password: !secret ap_password
  api_key_ekran: !secret api_key_ekran

packages:
  ekran:
    url: https://github.com/Reonimator/home_smart
    ref: main
    files: [ekran_base.yaml]
    refresh: 0s
```

3. Save → Install → Wirelessly. Каждая следующая сборка сама берёт свежий `main`.

С компьютера по-прежнему можно: `esp.bat ekran.yaml` (обёртка с паролями из `secrets.yaml`).

4. Home Assistant → Настройки → Устройства и службы: появится «ekran» → Настроить → ввести тот же ключ.

`reboot_timeout: 0s` — экран не перезагружается, если сервер выключен. Пол работает и без Home Assistant.
Нептун подключим после того, как заработает связь по RS-485; кнопку «Открыть воду» в Home Assistant не выводим (вода из сети — только закрыть).

## 8. Потом

- Телевизор LG — встроенная интеграция «LG webOS TV»; в телевизоре включить «Включение через Wi-Fi/LAN».
- Камеры — потоки RTSP/ONVIF с регистратора XVR (нужно знать приложение регистратора: XMEye / iCSee / DMSS).
- Mosquitto, Алиса — дополнения Home Assistant.
- Резервные копии: Proxmox → Datacenter → Backup, раз в неделю; плюс встроенные бэкапы Home Assistant.
