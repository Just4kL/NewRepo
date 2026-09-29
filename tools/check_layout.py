# tools/check_layout.py
"""Статический чекер лейаута: % в edge-отступах + числа вне шкалы токенов.

Источник шкалы — tokens/layout.json (магических чисел здесь нет).
Выход: 0 — чисто, 1 — есть нарушения. Запуск:
    C:\\Users\\Kenig\\miniconda3\\python.exe tools/check_layout.py
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOKENS = json.loads((ROOT / "tokens" / "layout.json").read_text(encoding="utf-8"))
UI = ROOT / "ui"

SCALE = set(TOKENS["space"].values())
RADII = set(TOKENS["radius"].values())

# % запрещён в краевых/размерных свойствах. Пропорции
# setColumnStretch/setRowStretch и доли форматирования ("12,5%") не трогаем.
PCT_RE = re.compile(
    r"(margin|padding|inset|width|height|left|top|right|bottom)\s*:\s*[^;\"']*%"
)
MARGIN_CALL_RE = re.compile(r"setContentsMargins\(([^)]+)\)|setSpacing\((\d+)\)")
QSS_GEOM_RE = re.compile(
    r"(margin|padding)[^:;]*:\s*(\d+)px|border-radius\s*:\s*(\d+)px"
)

fails = []


def emit(rule, path, lineno, detail):
    fails.append((rule, str(path), lineno, detail))


def check_file(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines, 1):
        if PCT_RE.search(line):
            emit("L1pct", path.relative_to(ROOT), i, line.strip()[:80])
        for m in MARGIN_CALL_RE.finditer(line):
            for part in re.split(r"[,\s]+", m.group(1) or m.group(2)):
                part = part.strip()
                if part.isdigit() and int(part) not in SCALE:
                    emit("L2scale", path.relative_to(ROOT), i,
                         f"{part}px not in space scale")
        for m in QSS_GEOM_RE.finditer(line):
            geom, radius = m.group(2), m.group(3)
            if geom is not None and int(geom) not in SCALE:
                emit("L3qss", path.relative_to(ROOT), i,
                     f"{geom}px not in space scale")
            if radius is not None and int(radius) not in RADII:
                emit("L4radius", path.relative_to(ROOT), i,
                     f"{radius}px not in radius tokens")


def main():
    for f in sorted(UI.rglob("*.py")):
        check_file(f)
    for rule, path, lineno, detail in fails:
        print(f"[{rule}] {path}:{lineno}: {detail}")
    by_rule = {}
    for rule, *_ in fails:
        by_rule[rule] = by_rule.get(rule, 0) + 1
    print(f"TOTAL {len(fails)} {by_rule or 'clean'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
