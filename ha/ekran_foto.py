"""Фото для экрана: из «Медиа» Home Assistant в /config/www/ekran/foto1.jpg, foto2.jpg, ...

Запускается самим Home Assistant (shell_command + автоматизация раз в 5 минут,
см. ha/ekran_foto.yaml и docs/foto.md). Ничего на компьютере ставить не нужно.

Берёт все фото из /media/ekran (Медиа → Мои медиа → папка ekran → «Загрузить»),
поворачивает по EXIF, подгоняет под 800x480 (обрезая края) и сохраняет как обычный
JPEG. Уже обработанные фото не пересчитываются (кэш в /config/ekran_foto_cache).
Удалили фото в «Медиа» — оно пропадёт и с экрана.
"""
import hashlib
import os
import pathlib
import shutil
import sys
import time

SRC = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/media/ekran")
DST = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "/config/www/ekran")
CACHE = pathlib.Path(sys.argv[3] if len(sys.argv) > 3 else "/config/ekran_foto_cache")
W, H = 800, 480
EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic", ".heif"}
BUDGET = 45  # с; shell_command обрывает через 60 с, остальное доделаем в следующий запуск

try:
    from PIL import Image, ImageOps
except ImportError:
    print("Нет Pillow в Home Assistant", file=sys.stderr)
    sys.exit(1)
try:
    import pillow_heif  # фото с айфона, если библиотека вдруг есть
    pillow_heif.register_heif_opener()
except ImportError:
    pass


def key(p: pathlib.Path) -> str:
    st = p.stat()
    return hashlib.sha1(f"{p.name}|{st.st_size}|{int(st.st_mtime)}".encode()).hexdigest()[:16]


def main() -> None:
    SRC.mkdir(parents=True, exist_ok=True)
    DST.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    files = sorted((p for p in SRC.rglob("*") if p.is_file() and p.suffix.lower() in EXT),
                   key=lambda p: str(p).lower())
    if not files:
        # «Медиа» пусто — ничего не трогаем (вдруг фото положены в www вручную)
        print("в /media/ekran нет фото")
        return
    ready, wanted = [], set()
    for p in files:
        k = key(p)
        c = CACHE / f"{k}.jpg"
        bad = CACHE / f"{k}.bad"
        wanted.update({c.name, bad.name})
        if bad.exists():
            continue
        if not c.exists():
            if time.monotonic() - t0 > BUDGET:
                continue  # доделаем в следующий раз
            try:
                im = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
                im = ImageOps.fit(im, (W, H), method=Image.LANCZOS)
                tmp = c.with_suffix(".tmp")
                im.save(tmp, "JPEG", quality=85, optimize=True, progressive=False)
                os.replace(tmp, c)
                print(f"готово: {p.name}")
            except Exception as e:  # не фото или формат не поддерживается
                bad.write_text(str(e), encoding="utf-8")
                print(f"пропуск {p.name}: {e}", file=sys.stderr)
                continue
        ready.append(c)
    # кэш удалённых фото
    for c in CACHE.iterdir():
        if c.name not in wanted:
            c.unlink()
    # foto1..N по порядку; лишние номера убираем, иначе экран покажет удалённые фото
    for i, c in enumerate(ready, 1):
        out = DST / f"foto{i}.jpg"
        if not out.exists() or out.stat().st_size != c.stat().st_size or \
                out.read_bytes() != c.read_bytes():
            shutil.copyfile(c, out.with_suffix(".tmp"))
            os.replace(out.with_suffix(".tmp"), out)
    for out in DST.glob("foto*.jpg"):
        n = out.stem[4:]
        if not n.isdigit() or int(n) > len(ready) or int(n) < 1:
            out.unlink()
    print(f"на экране {len(ready)} фото из {len(files)}")


if __name__ == "__main__":
    main()
