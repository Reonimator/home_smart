"""Готовит фото для фотогалереи экрана (ESP32-8048S070C, 800x480).

Берёт все JPG/PNG/HEIC* из папки, поворачивает по EXIF, подгоняет под 800x480
и сохраняет как обычный (не progressive) JPEG: foto1.jpg, foto2.jpg, ...
Экран показывает их по кругу, пока ничего не нажимают.

    pip install pillow
    python tools/foto.py C:\\Фото\\Для_экрана  C:\\Фото\\ekran
    python tools/foto.py папка_с_фото папка_вывода --pad   # не обрезать, а добавить чёрные поля

Затем содержимое папки вывода скопировать на Home Assistant в /config/www/ekran/
(папку www создать, если её нет, и один раз перезапустить HA). Проверка в браузере:
http://192.168.1.110:8123/local/ekran/foto1.jpg

* HEIC с айфона — только если установлен pillow-heif (pip install pillow-heif).
"""
import argparse
import pathlib

from PIL import Image, ImageOps

try:  # фото с айфона
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

W, H = 800, 480
EXT = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".bmp"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=pathlib.Path, help="папка с исходными фото")
    ap.add_argument("dst", type=pathlib.Path, help="куда сложить foto1.jpg, foto2.jpg, ...")
    ap.add_argument("--pad", action="store_true", help="вписать целиком с чёрными полями вместо обрезки")
    ap.add_argument("--quality", type=int, default=85)
    a = ap.parse_args()

    files = sorted(p for p in a.src.iterdir() if p.suffix.lower() in EXT)
    if not files:
        raise SystemExit(f"В {a.src} нет фото")
    a.dst.mkdir(parents=True, exist_ok=True)
    old = list(a.dst.glob("foto*.jpg"))
    for p in old:  # старые номера убираем, иначе экран покажет лишние
        p.unlink()

    n = 0
    for p in files:
        try:
            im = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
        except Exception as e:  # битый или неподдерживаемый файл
            print(f"пропуск {p.name}: {e}")
            continue
        if a.pad:
            im = ImageOps.pad(im, (W, H), method=Image.LANCZOS, color=(0, 0, 0))
        else:
            im = ImageOps.fit(im, (W, H), method=Image.LANCZOS)
        n += 1
        out = a.dst / f"foto{n}.jpg"
        im.save(out, "JPEG", quality=a.quality, optimize=True, progressive=False)
        print(f"{p.name} -> {out.name} ({out.stat().st_size // 1024} КБ)")
    print(f"Готово: {n} фото в {a.dst}")


if __name__ == "__main__":
    main()
