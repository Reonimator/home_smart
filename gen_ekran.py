rooms=["Балкон","Кухня","Детская","Спальня","Коридор","Ванная","Туалет"]
L=[]
A=L.append
A('''# Пульт тёплого пола v2: ESP32-8048S070C (7", 800x480)
# Режимы Дома/Ушёл, ночной режим, страница комнаты, настройки, вода (заготовка)

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
    sdkconfig_options:
      CONFIG_ESP32S3_DATA_CACHE_64KB: y
      CONFIG_ESP32S3_DATA_CACHE_LINE_64B: y
      CONFIG_SPIRAM_FETCH_INSTRUCTIONS: y
      CONFIG_SPIRAM_RODATA: y

psram:
  mode: octal
  speed: 80MHz

logger:

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  ap:
    ssid: "Ekran-Setup"
    password: !secret ap_password

captive_portal:

ota:
  - platform: esphome

time:
  - platform: sntp
    id: sntp_time
    timezone: MSK-3
    on_time_sync:
      - script.execute: upd_clock

font:
  - {file: "gfonts://Roboto", id: f_small, size: 20, glyphsets: [GF_Latin_Core, GF_Cyrillic_Core]}
  - {file: "gfonts://Roboto@500", id: f_mid, size: 26, glyphsets: [GF_Latin_Core, GF_Cyrillic_Core]}
  - {file: "gfonts://Roboto@700", id: f_big, size: 44, glyphsets: [GF_Latin_Core, GF_Cyrillic_Core]}
  - {file: "gfonts://Roboto@700", id: f_huge, size: 72, glyphsets: [GF_Latin_Core, GF_Cyrillic_Core]}

output:
  - {platform: ledc, pin: GPIO2, id: backlight_pwm, frequency: 20000Hz}

light:
  - {platform: monochromatic, output: backlight_pwm, name: "Подсветка", id: backlight, restore_mode: ALWAYS_ON}

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
  - {id: away_t, type: float, restore_value: true, initial_value: '15'}
  - {id: sleep_min, type: int, restore_value: true, initial_value: '2'}
  - {id: wcmd, type: int, restore_value: true, initial_value: '0'}
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
            id(eff)[i] = (id(mode) == 1) ? id(away_t) : (night ? id(night_t) : id(tg)[i]);
      - script.execute: refresh
  - id: refresh
    then:
      - lambda: |-
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
          ST(id(lwater), id(wcmd) ? "закрыта" : "открыта");
          BG(id(tilew), id(wcmd) ? 0x0C447C : 0x263238);
          ST(id(s_night), id(night_on) ? "Вкл" : "Выкл");
          BG(id(b_night), id(night_on) ? 0x185FA5 : 0x455A64);
          snprintf(b, sizeof(b), "%02d:00", id(n_start)); ST(id(s_start), b);
          snprintf(b, sizeof(b), "%02d:00", id(n_end)); ST(id(s_end), b);
          snprintf(b, sizeof(b), "%.1f°", id(night_t)); ST(id(s_nt), b);
          snprintf(b, sizeof(b), "%.1f°", id(away_t)); ST(id(s_at), b);
          snprintf(b, sizeof(b), "%d мин", id(sleep_min)); ST(id(s_sl), b);
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
          else if (id(night_active)) note = "Сейчас ночь: держим ночную температуру";
          lv_label_set_text(id(r_note), note);

# ---------- Связь с платой реле ----------
udp:

packet_transport:
  - platform: udp
    update_interval: 5s
    sensors: [set1, set2, set3, set4, set5, set6, set7, water_cmd]
    providers:
      - name: teplopol

interval:
  - interval: 20s
    then:
      - script.execute: compute
      - script.execute: upd_clock

sensor:''')
for i in range(1,8):
    A(f"  - {{platform: template, id: set{i}, internal: true, update_interval: 5s, lambda: 'return id(eff)[{i-1}];'}}")
A("  - {platform: template, id: water_cmd, internal: true, update_interval: 5s, lambda: 'return (float) id(wcmd);'}")
for i in range(1,8):
    A(f'''  - platform: packet_transport
    provider: teplopol
    remote_id: t{i}
    id: rt{i}
    internal: true
    on_value:
      - lambda: 'id(ft)[{i-1}] = x;'
      - script.execute: refresh''')
A('\nbinary_sensor:')
for i in range(1,8):
    A(f'''  - platform: packet_transport
    provider: teplopol
    remote_id: h{i}
    id: rh{i}
    internal: true
    on_state:
      - lambda: 'id(hs)[{i-1}] = x;'
      - script.execute: refresh''')
A('''  - platform: packet_transport
    provider: teplopol
    remote_id: h8
    id: rh8
    internal: true
    on_state:
      - lambda: 'id(boiler) = x;'
      - script.execute: refresh

# ---------- Интерфейс ----------
lvgl:
  displays: [my_display]
  touchscreens: [my_touch]
  buffer_size: 25%
  on_idle:
    timeout: !lambda "return id(sleep_min) * 60000;"
    then:
      - light.turn_off: backlight
      - lvgl.pause:
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
              - lambda: 'id(mode) = 0; id(wcmd) = 0;'
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
              - lambda: 'id(mode) = 1; id(wcmd) = 1;'
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
                    - lambda: 'id(wcmd) = 1;'
                    - script.execute: refresh
              - button:
                  align: BOTTOM_RIGHT
                  width: 84
                  height: 56
                  styles: btn_st
                  widgets:
                    - label: {{align: CENTER, text_font: f_small, text: "Откр."}}
                  on_click:
                    - lambda: 'id(wcmd) = 0;'
                    - script.execute: refresh''')
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
              - script.execute: room_open''')
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
 ("Ночь начинается", "id(n_start) = (id(n_start) + 23) % 24;", "id(n_start) = (id(n_start) + 1) % 24;", "s_start"),
 ("Ночь заканчивается", "id(n_end) = (id(n_end) + 23) % 24;", "id(n_end) = (id(n_end) + 1) % 24;", "s_end"),
 ("Температура ночью", "id(night_t) = std::max(15.0f, id(night_t) - 0.5f);", "id(night_t) = std::min(30.0f, id(night_t) + 0.5f);", "s_nt"),
 ("Температура «Ушёл»", "id(away_t) = std::max(5.0f, id(away_t) - 0.5f);", "id(away_t) = std::min(20.0f, id(away_t) + 0.5f);", "s_at"),
 ("Гасить экран через", "id(sleep_min) = std::max(1, id(sleep_min) - 1);", "id(sleep_min) = std::min(30, id(sleep_min) + 1);", "s_sl"),
]
for k,(title,minus,plus,lid) in enumerate(rows):
    y=62+k*68
    A(f'''        - obj:
            x: 10
            y: {y}
            width: 780
            height: 62
            styles: row_st
            scrollable: false
            widgets:
              - label: {{align: LEFT_MID, x: 10, text_font: f_mid, text_color: 0xFFFFFF, text: "{title}"}}''')
    if minus is None:
        A('''              - button:
                  id: b_night
                  align: RIGHT_MID
                  x: -6
                  width: 150
                  height: 50
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
                  height: 50
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
                  height: 50
                  styles: btn_st
                  widgets:
                    - label: {{align: CENTER, text_font: f_mid, text: "+"}}
                  on_click:
                    - lambda: '{plus}'
                    - script.execute: compute''')
open('ekran.yaml','w',encoding='utf-8').write("\n".join(L)+"\n")
