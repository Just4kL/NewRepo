# tools/build_icons.py — генерация light-вариантов, PNG и ICO из SVG сета Tray S.
import os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS = os.path.join(BASE, "assets", "icons")
NAMES = ["session", "games", "alarms", "timer", "settings", "about_tray"]
SIZES = [16, 20, 24, 28, 32, 48, 64, 128, 256]

# dark (для тёмного меню) -> light (для светлой темы)
REMAP = {
    "#E6E6E6": "#2B2B2B",  # основной контур светлый -> тёмный
    "#e6e6e6": "#2B2B2B",
    "#B8B8B8": "#6E6E6E",  # вторичный серый
    "#b8b8b8": "#6E6E6E",
    "#1B2B2B": "#FFFFFF",  # тёмная подложка бейджей -> белая
    "#1b2b2b": "#FFFFFF",
    "#5A5A5A": "#A8A8A8",  # трек слайдеров на тёмном -> трек на светлом
    "#5a5a5a": "#A8A8A8",
}

def make_light(svg_text: str) -> str:
    out = svg_text
    for src, dst in REMAP.items():
        out = out.replace(src, dst)
    return out

def main():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtSvg import QSvgRenderer
    from PyQt5.QtGui import QImage, QPainter
    from PyQt5.QtCore import QByteArray, Qt

    app = QApplication([])

    for name in NAMES:
        src = os.path.join(ICONS, f"{name}.svg")
        with open(src, "r", encoding="utf-8") as f:
            dark_svg = f.read()
        light_svg = make_light(dark_svg)
        light_path = os.path.join(ICONS, f"{name}_light.svg")
        with open(light_path, "w", encoding="utf-8") as f:
            f.write(light_svg)

        for theme, data in (("dark", dark_svg), ("light", light_svg)):
            outdir = os.path.join(ICONS, "png", theme)
            os.makedirs(outdir, exist_ok=True)
            raw = QByteArray(data.encode("utf-8"))
            for size in SIZES:
                ren = QSvgRenderer(raw)
                img = QImage(size, size, QImage.Format_ARGB32)
                img.fill(Qt.transparent)
                p = QPainter(img)
                ren.render(p)
                p.end()
                img.save(os.path.join(outdir, f"{name}_{size}.png"), "PNG")
            # ICO 64px одной картинкой (валидный ICO для меню/трея/ярлыков)
            ren = QSvgRenderer(raw)
            img = QImage(64, 64, QImage.Format_ARGB32)
            img.fill(Qt.transparent)
            p = QPainter(img)
            ren.render(p)
            p.end()
            img.save(os.path.join(outdir, f"{name}.ico"), "ICO")
    print("done:", NAMES)

if __name__ == "__main__":
    main()
