rooms=["Балкон","Кухня","Детская","Спальня","Коридор","Ванная","Туалет"]
L=[]
A=L.append
A('''# Пульт тёплого пола v2: ESP32-8048S070C (7", 800x480)
# Режимы Дома/Ушёл, ночной режим, страница комнаты, настройки, вода (Нептун по UDP),
# фотогалерея при простое (фото с Home Assistant)

esphome:
  name: ekran
  platformio_options:
    board_build.flash_mode: dio
  on_boot:
    priority: -100
    then:
      - delay: 3s
      - script.execute: compute

esp32:
  board: esp32-s3-devkitc-1
  flash_size: 16MB
  framework:
    type: esp-idf

psram:
  mode: octal
  speed: 80MHz

logger:
  hardware_uart: UART0

wifi:
  ssid: ${wifi_ssid}
  password: ${wifi_password}
  ap:
    ssid: "Ekran-Setup"
    password: ${ap_password}

captive_portal:

ota:
  - platform: esphome

# Связь с Home Assistant (домашний сервер 192.168.1.110). Только чтение:
# температуры пола, цели, «греет», котёл, режим. Управление остаётся на экране.
# reboot_timeout: 0s — экран НЕ перезагружается, если Home Assistant выключен.
api:
  encryption:
    key: ${api_key_ekran}
  reboot_timeout: 0s

time:
  - platform: sntp
    id: sntp_time
    timezone: MSK-3
    on_time_sync:
      - script.execute: upd_clock

# ---------- Фотогалерея при простое ----------
# Фото лежат на Home Assistant в папке /config/www/ekran/ под именами foto1.jpg, foto2.jpg, ...
# (подготовить можно скриптом tools/foto.py: 800x480, обычный, не progressive JPEG).
# HA отдаёт папку www по адресу /local/ без пароля, только внутри домашней сети.
# Экран берёт foto1, foto2, ... по очереди; когда следующего номера нет — снова foto1.
# Слот microSD на плате есть, но ESPHome не умеет читать с него файлы, поэтому фото по сети.
http_request:
  verify_ssl: false
  timeout: 15s

online_image:
  - id: foto
    url: "http://192.168.1.110/local/ekran/foto1.jpg"
    format: JPEG
    type: RGB565
    resize: 800x480
    on_download_finished:
      - if:
          condition:
            lambda: 'return id(foto_on);'
          then:
            - lambda: |-
                ESP_LOGI("foto", "показано foto%d", id(foto_n));
                id(foto_have) = true;
                id(foto_n)++;  // в следующий раз — следующее
            - lvgl.image.update:
                id: foto_img
                src: foto
      - lambda: 'id(foto_busy) = false;'
    on_error:
      - lambda: 'id(foto_busy) = false;'
      - if:
          condition:
            lambda: 'return id(foto_on) && id(foto_n) > 1;'
          then:
            # следующего номера нет — по кругу с первого, через секунду (без вложенной загрузки)
            - lambda: |-
                ESP_LOGI("foto", "foto%d нет — снова с foto1", id(foto_n));
                id(foto_n) = 1;
                id(foto_tick) = id(foto_iv);
          else:
            # нет даже foto1 (или сервер выключен) — просто гасим экран, как раньше
            - if:
                condition:
                  lambda: 'return id(foto_on);'
                then:
                  - script.execute: foto_dark

font:
  - {file: "gfonts://Roboto", id: f_small, size: 20, glyphsets: [GF_Latin_Core, GF_Cyrillic_Core]}
  - {file: "gfonts://Roboto@500", id: f_mid, size: 26, glyphsets: [GF_Latin_Core, GF_Cyrillic_Core]}
  - {file: "gfonts://Roboto@700", id: f_big, size: 44, glyphsets: [GF_Latin_Core, GF_Cyrillic_Core]}
  - {file: "gfonts://Roboto@700", id: f_huge, size: 72, glyphsets: [GF_Latin_Core, GF_Cyrillic_Core]}

output:
  - {platform: gpio, pin: GPIO2, id: backlight_pin}

light:
  - {platform: binary, output: backlight_pin, name: "Подсветка", id: backlight, restore_mode: ALWAYS_ON}

i2c:
  sda: GPIO19
  scl: GPIO20

display:
  - platform: rpi_dpi_rgb
    id: my_display
    color_order: RGB
    auto_clear_enabled: false
    update_interval: never
    dimensions: {width: 800, height: 480}
    de_pin: GPIO41
    hsync_pin: GPIO39
    vsync_pin: GPIO40
    pclk_pin: GPIO42
    pclk_frequency: 14MHz
    pclk_inverted: true
    hsync_pulse_width: 30
    hsync_back_porch: 16
    hsync_front_porch: 210
    vsync_pulse_width: 13
    vsync_back_porch: 10
    vsync_front_porch: 22
    data_pins:
      red:   [GPIO14, GPIO21, GPIO47, GPIO48, GPIO45]
      green: [GPIO9, GPIO46, GPIO3, GPIO8, GPIO16, GPIO1]
      blue:  [GPIO15, GPIO7, GPIO6, GPIO5, GPIO4]

touchscreen:
  - platform: gt911
    id: my_touch
    display: my_display
    on_release:
      - if:
          condition: lvgl.is_paused
          then:
            - lvgl.resume:
            - lvgl.widget.redraw:
            - light.turn_on: backlight
      # касание во время фотогалереи — обратно на главный экран
      - if:
          condition:
            lambda: 'return id(foto_on);'
          then:
            - lambda: 'id(foto_on) = false; id(foto_busy) = false;'
            - lvgl.page.show: main_page
            - script.execute: refresh

# ---------- Память ----------
globals:
  - {id: tg, type: 'std::array<float, 7>', restore_value: true, initial_value: '{{24, 26, 26, 25, 25, 28, 26}}'}
  - {id: eff, type: 'std::array<float, 7>', initial_value: '{{24, 26, 26, 25, 25, 28, 26}}'}
  - {id: ft, type: 'std::array<float, 7>', initial_value: '{{NAN, NAN, NAN, NAN, NAN, NAN, NAN}}'}
  - {id: hs, type: 'std::array<bool, 7>', initial_value: '{{false, false, false, false, false, false, false}}'}
  - {id: mode, type: int, restore_value: true, initial_value: '0'}
  - {id: night_on, type: bool, restore_value: true, initial_value: 'false'}
  - {id: n_start, type: int, restore_value: true, initial_value: '23'}
  - {id: n_end, type: int, restore_value: true, initial_value: '7'}
  - {id: night_t, type: float, restore_value: true, initial_value: '22'}
  # в каких комнатах ночью снижать температуру (галочки в настройках)
  - {id: night_rm, type: 'std::array<bool, 7>', restore_value: true, initial_value: '{{true, true, true, true, true, true, true}}'}
  - {id: away_t, type: float, restore_value: true, initial_value: '15'}
  - {id: sleep_min, type: int, restore_value: true, initial_value: '2'}
  # фотогалерея: смена фото раз в foto_iv секунд, 0 — выключена (экран просто гаснет)
  - {id: foto_iv, type: int, restore_value: true, initial_value: '30'}
  - {id: foto_on, type: bool, initial_value: 'false'}
  - {id: foto_have, type: bool, initial_value: 'false'}
  - {id: foto_n, type: int, initial_value: '1'}
  - {id: foto_tick, type: int, initial_value: '0'}
  - {id: foto_busy, type: bool, initial_value: 'false'}
  - {id: wcmd, type: int, restore_value: true, initial_value: '0'}
  # номер команды воды: Нептун выполняет команду только когда номер меняется (нажатие),
  # поэтому перезагрузка экрана или Нептуна сама воду не откроет
  - {id: wseq, type: int, restore_value: true, initial_value: '0'}
  - {id: night_active, type: bool, initial_value: 'false'}
  - {id: boiler, type: bool, initial_value: 'false'}
  - {id: cur, type: int, initial_value: '0'}

script:
  - id: compute
    then:
      - lambda: |-
          auto t = id(sntp_time).now();
          bool night = false;
          if (id(night_on) && t.is_valid()) {
            int m = t.hour * 60 + t.minute;
            int s = id(n_start) * 60, e = id(n_end) * 60;
            night = (s < e) ? (m >= s && m < e) : (m >= s || m < e);
          }
          id(night_active) = night;
          for (int i = 0; i < 7; i++)
            id(eff)[i] = (id(mode) == 1) ? id(away_t) : ((night && id(night_rm)[i]) ? id(night_t) : id(tg)[i]);
          // сразу отправляем на плату, не дожидаясь опроса
          id(set1).publish_state(id(eff)[0]); id(set2).publish_state(id(eff)[1]);
          id(set3).publish_state(id(eff)[2]); id(set4).publish_state(id(eff)[3]);
          id(set5).publish_state(id(eff)[4]); id(set6).publish_state(id(eff)[5]);
          id(set7).publish_state(id(eff)[6]);
          id(water_req).publish_state((float) ((id(wseq) % 1000) * 2 + id(wcmd)));
      - script.execute: refresh
  - id: refresh
    then:
      - lambda: |-
          // «Греет» и «Котёл» берём прямо из последнего пакета платы при каждой перерисовке.
          // Раньше они менялись только по событию смены состояния, и если событие
          // терялось, плитка оставалась серой, а котёл «ждал», хотя реле были включены.
          id(hs)[0] = id(rh1).has_state() && id(rh1).state;
          id(hs)[1] = id(rh2).has_state() && id(rh2).state;
          id(hs)[2] = id(rh3).has_state() && id(rh3).state;
          id(hs)[3] = id(rh4).has_state() && id(rh4).state;
          id(hs)[4] = id(rh5).has_state() && id(rh5).state;
          id(hs)[5] = id(rh6).has_state() && id(rh6).state;
          id(hs)[6] = id(rh7).has_state() && id(rh7).state;
          id(boiler) = id(rh8).has_state() && id(rh8).state;
          char b[48];
          auto ST = [](lv_obj_t *o, const char *s) {
            const char *c = lv_label_get_text(o);
            if (c == nullptr || strcmp(c, s) != 0) lv_label_set_text(o, s);
          };
          static std::map<lv_obj_t *, uint32_t> bgc;
          auto BG = [](lv_obj_t *o, uint32_t h) {
            auto it = bgc.find(o);
            if (it != bgc.end() && it->second == h) return;
            bgc[o] = h;
            lv_obj_set_style_bg_color(o, lv_color_hex(h), LV_PART_MAIN);
          };
          lv_obj_t *lc[7] = {id(lc1), id(lc2), id(lc3), id(lc4), id(lc5), id(lc6), id(lc7)};
          lv_obj_t *lt[7] = {id(lt1), id(lt2), id(lt3), id(lt4), id(lt5), id(lt6), id(lt7)};
          lv_obj_t *tl[7] = {id(tile1), id(tile2), id(tile3), id(tile4), id(tile5), id(tile6), id(tile7)};
          for (int i = 0; i < 7; i++) {
            if (isnan(id(ft)[i])) ST(lc[i], "--");
            else { snprintf(b, sizeof(b), "%.1f°", id(ft)[i]); ST(lc[i], b); }
            if (isnan(id(ft)[i])) ST(lt[i], "нет датчика");
            else { snprintf(b, sizeof(b), "цель %.1f°", id(eff)[i]); ST(lt[i], b); }
            BG(tl[i], id(hs)[i] ? 0x0F6E56 : 0x263238);
          }
          BG(id(btn_home), id(mode) == 0 ? 0x185FA5 : 0x263238);
          BG(id(btn_away), id(mode) == 1 ? 0x185FA5 : 0x263238);
          std::string st = id(boiler) ? "Котёл работает" : "Котёл ждёт";
          if (id(mode) == 0 && id(night_active)) st += "  ·  ночь";
          ST(id(lstatus), st.c_str());
          // Вода: показываем реальное состояние Нептуна, а не последнюю команду
          bool nl = id(np_link).has_state() && id(np_link).state;
          bool leak = nl && id(np_leak).has_state() && id(np_leak).state;
          bool closed = nl && id(np_closed).has_state() && id(np_closed).state;
          bool closing = nl && id(np_closing).has_state() && id(np_closing).state;
          bool opening = nl && id(np_opening).has_state() && id(np_opening).state;
          ST(id(lwater), !nl ? "нет связи" : leak ? "ПРОТЕЧКА!" : closing ? "закрывается..." :
                         opening ? "открывается..." : closed ? "закрыта" : "открыта");
          BG(id(tilew), !nl ? 0x37474F : leak ? 0xA32D2D : (closing || opening) ? 0x8A6D1F :
                        closed ? 0x0C447C : 0x263238);
          ST(id(s_night), id(night_on) ? "Вкл" : "Выкл");
          BG(id(b_night), id(night_on) ? 0x185FA5 : 0x455A64);
          snprintf(b, sizeof(b), "%02d:00", id(n_start)); ST(id(s_start), b);
          snprintf(b, sizeof(b), "%02d:00", id(n_end)); ST(id(s_end), b);
          snprintf(b, sizeof(b), "%.1f°", id(night_t)); ST(id(s_nt), b);
          BG(id(b_nr0), id(night_rm)[0] ? 0x185FA5 : 0x455A64);
          BG(id(b_nr1), id(night_rm)[1] ? 0x185FA5 : 0x455A64);
          BG(id(b_nr2), id(night_rm)[2] ? 0x185FA5 : 0x455A64);
          BG(id(b_nr3), id(night_rm)[3] ? 0x185FA5 : 0x455A64);
          BG(id(b_nr4), id(night_rm)[4] ? 0x185FA5 : 0x455A64);
          BG(id(b_nr5), id(night_rm)[5] ? 0x185FA5 : 0x455A64);
          BG(id(b_nr6), id(night_rm)[6] ? 0x185FA5 : 0x455A64);
          snprintf(b, sizeof(b), "%.1f°", id(away_t)); ST(id(s_at), b);
          snprintf(b, sizeof(b), "%d мин", id(sleep_min)); ST(id(s_sl), b);
          if (id(foto_iv) <= 0) ST(id(s_foto), "Выкл");
          else if (id(foto_iv) < 60) { snprintf(b, sizeof(b), "%d с", id(foto_iv)); ST(id(s_foto), b); }
          else { snprintf(b, sizeof(b), "%d мин", id(foto_iv) / 60); ST(id(s_foto), b); }
          BG(id(b_foto), id(foto_iv) > 0 ? 0x185FA5 : 0x455A64);
  - id: upd_clock
    then:
      - lambda: |-
          static const char *DN[7] = {"Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"};
          static const char *MN[12] = {"января", "февраля", "марта", "апреля", "мая", "июня",
                                       "июля", "августа", "сентября", "октября", "ноября", "декабря"};
          auto t = id(sntp_time).now();
          char b[64];
          if (!t.is_valid()) snprintf(b, sizeof(b), "--:--");
          else snprintf(b, sizeof(b), "%s, %d %s   %02d:%02d", DN[t.day_of_week - 1], t.day_of_month,
                        MN[t.month - 1], t.hour, t.minute);
          const char *c = lv_label_get_text(id(lclock));
          if (c == nullptr || strcmp(c, b) != 0) lv_label_set_text(id(lclock), b);
          if (t.is_valid()) snprintf(b, sizeof(b), "%02d:%02d", t.hour, t.minute);
          c = lv_label_get_text(id(lfclock));
          if (c == nullptr || strcmp(c, b) != 0) lv_label_set_text(id(lfclock), b);
  # Простой: фотогалерея, а ночью (ночной режим) и в режиме «Ушёл» — просто гасим экран
  - id: foto_start
    then:
      - if:
          condition:
            lambda: 'return id(foto_iv) > 0 && id(mode) == 0 && !id(night_active);'
          then:
            - lambda: 'id(foto_on) = true; id(foto_tick) = 0; id(foto_busy) = true;'
            - script.execute: upd_clock
            - lvgl.page.show: foto_page
            - online_image.set_url:
                id: foto
                url: !lambda 'return "http://192.168.1.110/local/ekran/foto" + to_string(id(foto_n)) + ".jpg";'
          else:
            - script.execute: foto_dark
  - id: foto_dark
    then:
      - lambda: 'id(foto_on) = false;'
      - lvgl.page.show: main_page
      - light.turn_off: backlight
      - lvgl.pause:
  - id: room_open
    then:
      - lambda: |-
          static const char *RN[7] = {"Балкон", "Кухня", "Детская", "Спальня", "Коридор", "Ванная", "Туалет"};
          char b[48];
          int i = id(cur);
          lv_label_set_text(id(r_name), RN[i]);
          snprintf(b, sizeof(b), "%.1f°", id(tg)[i]); lv_label_set_text(id(r_tgt), b);
          if (isnan(id(ft)[i])) lv_label_set_text(id(r_floor), "пол: нет датчика");
          else { snprintf(b, sizeof(b), "пол %.1f°%s", id(ft)[i], id(hs)[i] ? "  ·  греет" : ""); lv_label_set_text(id(r_floor), b); }
          lv_arc_set_value(id(r_arc), (int)(id(tg)[i] * 2));
          const char *note = "";
          if (id(mode) == 1) note = "Сейчас режим «Ушёл»: держим температуру «Ушёл»";
          else if (id(night_active) && id(night_rm)[i]) note = "Сейчас ночь: держим ночную температуру";
          lv_label_set_text(id(r_note), note);

# ---------- Связь с платой реле ----------
udp:

packet_transport:
  - platform: udp
    update_interval: 1s
    sensors: [set1, set2, set3, set4, set5, set6, set7, water_req]
    providers:
      - name: teplopol
      - name: neptun

interval:
  - interval: 20s
    then:
      - script.execute: compute
      - script.execute: upd_clock
  # Страховка: раз в 2 с сверяем экран с последними данными платы
  # (перерисовывается только то, что изменилось, мерцания не будет)
  - interval: 2s
    then:
      - script.execute: refresh
  # Фотогалерея: следующее фото раз в foto_iv секунд; с наступлением ночи или «Ушёл» — гасим
  - interval: 1s
    then:
      - if:
          condition:
            lambda: 'return id(foto_on);'
          then:
            - if:
                condition:
                  lambda: 'return id(foto_iv) <= 0 || id(mode) != 0 || id(night_active);'
                then:
                  - script.execute: foto_dark
                else:
                  - if:
                      condition:
                        # пока прошлое фото качается — ждём, номер не сдвигаем
                        lambda: 'return ++id(foto_tick) >= id(foto_iv) && !id(foto_busy);'
                      then:
                        - lambda: 'id(foto_tick) = 0; id(foto_busy) = true;'
                        - online_image.set_url:
                            id: foto
                            url: !lambda 'return "http://192.168.1.110/local/ekran/foto" + to_string(id(foto_n)) + ".jpg";'

sensor:
  # Сила Wi-Fi сигнала экрана (в Home Assistant): лучше −67 дБм, хуже −75 — обрывы прошивки
  - {platform: wifi_signal, name: "Wi-Fi сигнал", update_interval: 60s}''')
for i in range(1,8):
    A(f"  - {{platform: template, id: set{i}, internal: true, update_interval: 60s, lambda: 'return id(eff)[{i-1}];'}}")
A("  - {platform: template, id: water_req, internal: true, update_interval: 60s, lambda: 'return (float) ((id(wseq) % 1000) * 2 + id(wcmd));'}")
for i in range(1,8):
    A(f'  - {{platform: template, name: "Цель {i} {rooms[i-1]}", unit_of_measurement: "°C", device_class: temperature, accuracy_decimals: 1, update_interval: 30s, lambda: \'return id(eff)[{i-1}];\'}}')
for i in range(1,8):
    A(f'''  - platform: packet_transport
    provider: teplopol
    remote_id: t{i}
    id: rt{i}
    name: "Пол {i} {rooms[i-1]}"
    internal: false
    unit_of_measurement: "°C"
    device_class: temperature
    state_class: measurement
    accuracy_decimals: 1
    on_value:
      - lambda: 'id(ft)[{i-1}] = x;'
      - script.execute: refresh''')
A('''
text_sensor:
  - platform: template
    name: "Режим"
    update_interval: 30s
    lambda: |-
      if (id(mode) == 1) return std::string("Ушёл");
      return std::string(id(night_active) ? "Дома, ночь" : "Дома");
  # Состояние воды от Нептуна — для Home Assistant
  - platform: template
    name: "Вода (water)"
    update_interval: 5s
    lambda: |-
      bool nl = id(np_link).has_state() && id(np_link).state;
      if (!nl) return std::string("нет связи");
      if (id(np_leak).has_state() && id(np_leak).state) return std::string("протечка");
      if (id(np_closing).has_state() && id(np_closing).state) return std::string("закрывается");
      if (id(np_opening).has_state() && id(np_opening).state) return std::string("открывается");
      return std::string(id(np_closed).has_state() && id(np_closed).state ? "закрыта" : "открыта");''')
A('''
# ---------- Управление из Home Assistant ----------
# Цели только в пределах 15–35°. Режим «Дома» из HA воду НЕ открывает
# (вода из сети — только закрыть; открыть можно только кнопкой на экране).
# Из HA воду можно только ЗАКРЫТЬ (например, по беспроводному датчику протечки).
button:
  - platform: template
    name: "Закрыть воду (close)"
    on_press:
      - lambda: 'id(wcmd) = 1; id(wseq)++;'
      - script.execute: compute

select:
  - platform: template
    name: "Режим пола"
    options: ["Дома", "Ушёл"]
    update_interval: 5s
    lambda: 'return std::string(id(mode) == 1 ? "Ушёл" : "Дома");'
    set_action:
      - lambda: |-
          if (x == "Ушёл") { id(mode) = 1; id(wcmd) = 1; id(wseq)++; }
          else { id(mode) = 0; }
      - script.execute: compute

number:''')
for i in range(1,8):
    A(f'''  - platform: template
    name: "Уставка {i} {rooms[i-1]}"
    unit_of_measurement: "°C"
    min_value: 15
    max_value: 35
    step: 0.5
    mode: box
    update_interval: 5s
    lambda: 'return id(tg)[{i-1}];'
    set_action:
      - lambda: 'id(tg)[{i-1}] = std::max(15.0f, std::min(35.0f, x));'
      - script.execute: compute''')
A('\nbinary_sensor:')
for i in range(1,8):
    A(f'''  - platform: packet_transport
    provider: teplopol
    remote_id: h{i}
    id: rh{i}
    name: "Греет {i} {rooms[i-1]}"
    internal: false
    device_class: heat
    on_state:
      - lambda: 'id(hs)[{i-1}] = x;'
      - script.execute: refresh''')
A('''  - platform: packet_transport
    provider: teplopol
    remote_id: h8
    id: rh8
    name: "Котёл"
    internal: false
    device_class: heat
    on_state:
      - lambda: 'id(boiler) = x;'
      - script.execute: refresh
  # Нептун (ESP32-C3 по RS-485): реальное состояние воды
  - {platform: packet_transport, provider: neptun, remote_id: np_link, id: np_link, internal: true, on_state: [script.execute: refresh]}
  - {platform: packet_transport, provider: neptun, remote_id: np_leak, id: np_leak, internal: true, on_state: [script.execute: refresh]}
  - {platform: packet_transport, provider: neptun, remote_id: np_closed, id: np_closed, internal: true, on_state: [script.execute: refresh]}
  - {platform: packet_transport, provider: neptun, remote_id: np_closing, id: np_closing, internal: true, on_state: [script.execute: refresh]}
  - {platform: packet_transport, provider: neptun, remote_id: np_opening, id: np_opening, internal: true, on_state: [script.execute: refresh]}

# ---------- Интерфейс ----------
lvgl:
  displays: [my_display]
  touchscreens: [my_touch]
  buffer_size: 25%
  on_idle:
    timeout: !lambda "return id(sleep_min) * 60000;"
    then:
      - script.execute: foto_start
  style_definitions:
    - {id: tile_st, bg_color: 0x263238, bg_opa: COVER, radius: 14, border_width: 0, pad_all: 6}
    - {id: btn_st, bg_color: 0x455A64, radius: 10, shadow_width: 0}
    - {id: row_st, bg_color: 0x1E272C, bg_opa: COVER, radius: 10, border_width: 0, pad_all: 4}
  pages:
    - id: main_page
      bg_color: 0x101418
      widgets:
        - label: {x: 16, y: 12, text_font: f_mid, text_color: 0xFFFFFF, text: "Тёплый пол"}
        - label: {id: lstatus, x: 200, y: 16, text_font: f_small, text_color: 0xB0BEC5, text: "Котёл ждёт"}
        - label: {id: lclock, align: TOP_RIGHT, x: -90, y: 12, text_font: f_mid, text_color: 0xFFFFFF, text: "--:--"}
        - button:
            align: TOP_RIGHT
            x: -10
            y: 6
            width: 70
            height: 42
            styles: btn_st
            widgets:
              - label: {align: CENTER, text_font: f_small, text: "Настр."}
            on_click:
              - script.execute: refresh
              - lvgl.page.show: set_page
        - button:
            id: btn_home
            x: 8
            y: 56
            width: 388
            height: 50
            styles: btn_st
            widgets:
              - label: {align: CENTER, text_font: f_mid, text: "Дома"}
            on_click:
              - lambda: 'id(mode) = 0; id(wcmd) = 0; id(wseq)++;'
              - script.execute: compute
        - button:
            id: btn_away
            x: 404
            y: 56
            width: 388
            height: 50
            styles: btn_st
            widgets:
              - label: {align: CENTER, text_font: f_mid, text: "Ушёл"}
            on_click:
              - lambda: 'id(mode) = 1; id(wcmd) = 1; id(wseq)++;'
              - script.execute: compute''')
W,H=190,178
for i in range(1,9):
    col=(i-1)%4; row=(i-1)//4
    x=8+col*(W+6); y=114+row*(H+8)
    if i<=7:
        A(f'''        - obj:
            id: tile{i}
            x: {x}
            y: {y}
            width: {W}
            height: {H}
            styles: tile_st
            scrollable: false
            clickable: true
            on_click:
              - lambda: 'id(cur) = {i-1};'
              - script.execute: room_open
              - lvgl.page.show: room_page
            widgets:
              - label: {{align: TOP_MID, y: 4, text_font: f_mid, text_color: 0xFFFFFF, text: "{rooms[i-1]}"}}
              - label: {{id: lc{i}, align: CENTER, y: 4, text_font: f_big, text_color: 0xFFFFFF, text: "--"}}
              - label: {{id: lt{i}, align: BOTTOM_MID, y: -6, text_font: f_small, text_color: 0xCFD8DC, text: ""}}''')
    else:
        A(f'''        - obj:
            id: tilew
            x: {x}
            y: {y}
            width: {W}
            height: {H}
            styles: tile_st
            scrollable: false
            widgets:
              - label: {{align: TOP_MID, y: 4, text_font: f_mid, text_color: 0xFFFFFF, text: "Вода"}}
              - label: {{id: lwater, align: TOP_MID, y: 40, text_font: f_small, text_color: 0xCFD8DC, text: "открыта"}}
              - button:
                  align: BOTTOM_LEFT
                  width: 84
                  height: 56
                  styles: btn_st
                  widgets:
                    - label: {{align: CENTER, text_font: f_small, text: "Закр."}}
                  on_click:
                    - lambda: 'id(wcmd) = 1; id(wseq)++;'
                    - script.execute: compute
              - button:
                  align: BOTTOM_RIGHT
                  width: 84
                  height: 56
                  styles: btn_st
                  widgets:
                    - label: {{align: CENTER, text_font: f_small, text: "Откр."}}
                  on_click:
                    - lambda: 'id(wcmd) = 0; id(wseq)++;'
                    - script.execute: compute''')
# room page
A('''
    - id: room_page
      bg_color: 0x101418
      widgets:
        - label: {id: r_name, x: 20, y: 14, text_font: f_mid, text_color: 0xFFFFFF, text: ""}
        - button:
            align: TOP_RIGHT
            x: -10
            y: 6
            width: 120
            height: 46
            styles: btn_st
            widgets:
              - label: {align: CENTER, text_font: f_small, text: "Назад"}
            on_click:
              - script.execute: compute
              - lvgl.page.show: main_page
        - arc:
            id: r_arc
            x: 60
            y: 70
            width: 340
            height: 340
            min_value: 30
            max_value: 70
            value: 50
            adjustable: true
            arc_width: 26
            arc_color: 0x37474F
            indicator:
              arc_width: 26
              arc_color: 0x1D9E75
            knob:
              bg_color: 0xFFFFFF
            on_value:
              - lambda: |-
                  id(tg)[id(cur)] = x / 2.0f;
                  char b[16]; snprintf(b, sizeof(b), "%.1f°", id(tg)[id(cur)]);
                  lv_label_set_text(id(r_tgt), b);
            on_release:
              - script.execute: compute
        - label: {id: r_tgt, x: 140, y: 190, width: 180, text_align: CENTER, text_font: f_huge, text_color: 0xFFFFFF, text: ""}
        - label: {id: r_floor, x: 450, y: 110, text_font: f_mid, text_color: 0xCFD8DC, text: ""}
        - label: {id: r_note, x: 450, y: 150, width: 330, text_font: f_small, text_color: 0x85B7EB, text: ""}''')
for sign,xx,expr in [("-",450,"std::max(15.0f, id(tg)[id(cur)] - 0.5f)"),("+",630,"std::min(35.0f, id(tg)[id(cur)] + 0.5f)")]:
    A(f'''        - button:
            x: {xx}
            y: 260
            width: 150
            height: 110
            styles: btn_st
            widgets:
              - label: {{align: CENTER, text_font: f_huge, text: "{sign}"}}
            on_click:
              - lambda: 'id(tg)[id(cur)] = {expr};'
              - script.execute: room_open
              - script.execute: compute''')
# settings
A('''
    - id: set_page
      bg_color: 0x101418
      widgets:
        - label: {x: 20, y: 14, text_font: f_mid, text_color: 0xFFFFFF, text: "Настройки"}
        - button:
            align: TOP_RIGHT
            x: -10
            y: 6
            width: 120
            height: 46
            styles: btn_st
            widgets:
              - label: {align: CENTER, text_font: f_small, text: "Назад"}
            on_click:
              - script.execute: compute
              - lvgl.page.show: main_page''')
rows=[
 ("Ночной режим каждый день", None, None, "s_night"),
 ("Ночью", None, None, "night_rooms"),
 ("Ночь начинается", "id(n_start) = (id(n_start) + 23) % 24;", "id(n_start) = (id(n_start) + 1) % 24;", "s_start"),
 ("Ночь заканчивается", "id(n_end) = (id(n_end) + 23) % 24;", "id(n_end) = (id(n_end) + 1) % 24;", "s_end"),
 ("Температура ночью", "id(night_t) = std::max(15.0f, id(night_t) - 0.5f);", "id(night_t) = std::min(30.0f, id(night_t) + 0.5f);", "s_nt"),
 ("Температура «Ушёл»", "id(away_t) = std::max(5.0f, id(away_t) - 0.5f);", "id(away_t) = std::min(20.0f, id(away_t) + 0.5f);", "s_at"),
 ("Гасить экран через", "id(sleep_min) = std::max(1, id(sleep_min) - 1);", "id(sleep_min) = std::min(30, id(sleep_min) + 1);", "s_sl"),
 ("Фото при простое, смена", None, None, "s_foto"),
]
for k,(title,minus,plus,lid) in enumerate(rows):
    y=58+k*52
    A(f'''        - obj:
            x: 10
            y: {y}
            width: 780
            height: 48
            styles: row_st
            scrollable: false
            widgets:
              - label: {{align: LEFT_MID, x: 10, text_font: f_mid, text_color: 0xFFFFFF, text: "{title}"}}''')
    if lid == "night_rooms":
        # галочки по комнатам: синяя — комната ночью снижает температуру, серая — нет
        short=["Балкон","Кухня","Детская","Спальня","Коридор","Ванная","Туалет"]
        for i,nm in enumerate(short):
            A(f'''              - button:
                  id: b_nr{i}
                  align: LEFT_MID
                  x: {104+i*95}
                  width: 91
                  height: 38
                  styles: btn_st
                  pad_all: 2
                  widgets:
                    - label: {{align: CENTER, text_font: f_small, text: "{nm}"}}
                  on_click:
                    - lambda: 'id(night_rm)[{i}] = !id(night_rm)[{i}];'
                    - script.execute: compute''')
    elif lid == "s_foto":
        A('''              - button:
                  id: b_foto
                  align: RIGHT_MID
                  x: -6
                  width: 150
                  height: 38
                  styles: btn_st
                  widgets:
                    - label: {id: s_foto, align: CENTER, text_font: f_mid, text: "30 с"}
                  on_click:
                    # Выкл -> 10 с -> 30 с -> 1 мин -> 5 мин -> Выкл
                    - lambda: |-
                        int v = id(foto_iv);
                        id(foto_iv) = v <= 0 ? 10 : v < 30 ? 30 : v < 60 ? 60 : v < 300 ? 300 : 0;
                    - script.execute: refresh''')
    elif minus is None:
        A('''              - button:
                  id: b_night
                  align: RIGHT_MID
                  x: -6
                  width: 150
                  height: 38
                  styles: btn_st
                  widgets:
                    - label: {id: s_night, align: CENTER, text_font: f_mid, text: "Выкл"}
                  on_click:
                    - lambda: 'id(night_on) = !id(night_on);'
                    - script.execute: compute''')
    else:
        A(f'''              - button:
                  align: RIGHT_MID
                  x: -200
                  width: 70
                  height: 38
                  styles: btn_st
                  widgets:
                    - label: {{align: CENTER, text_font: f_mid, text: "-"}}
                  on_click:
                    - lambda: '{minus}'
                    - script.execute: compute
              - label: {{id: {lid}, align: RIGHT_MID, x: -90, text_font: f_mid, text_color: 0xFFFFFF, text: ""}}
              - button:
                  align: RIGHT_MID
                  x: -6
                  width: 70
                  height: 38
                  styles: btn_st
                  widgets:
                    - label: {{align: CENTER, text_font: f_mid, text: "+"}}
                  on_click:
                    - lambda: '{plus}'
                    - script.execute: compute''')
# фотогалерея при простое: касание в любом месте возвращает главный экран
A('''
    - id: foto_page
      skip: true
      bg_color: 0x000000
      scrollable: false
      widgets:
        - image: {id: foto_img, align: CENTER, src: foto}
        - label:
            id: lfclock
            align: BOTTOM_RIGHT
            x: -16
            y: -12
            text_font: f_big
            text_color: 0xFFFFFF
            bg_color: 0x000000
            bg_opa: 40%
            radius: 10
            pad_all: 6
            text: "--:--"''')
L.insert(0, "# СГЕНЕРИРОВАНО gen_ekran.py — не править руками. Пароли приходят через substitutions\n# из ekran.yaml (esp.bat) или из конфигурации на домашнем сервере (см. docs/server.md).")
open('ekran_base.yaml','w',encoding='utf-8').write("\n".join(L)+"\n")
open('ekran.yaml','w',encoding='utf-8').write('''# Экран для esp.bat: пароли из secrets.yaml, вся конфигурация — в ekran_base.yaml
# (генерируется gen_ekran.py). На домашнем сервере используется тот же ekran_base.yaml
# прямо с GitHub, см. docs/server.md.
substitutions:
  wifi_ssid: !secret wifi_ssid
  wifi_password: !secret wifi_password
  ap_password: !secret ap_password
  api_key_ekran: !secret api_key_ekran

packages:
  base: !include ekran_base.yaml
''')
