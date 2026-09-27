# -*- mode: python ; coding: utf-8 -*-

import os
import sys

block_cipher = None

# PyInstaller не умеет находить DLL, которые conda держит в <prefix>\Library\bin,
# тогда как сами .pyd лежат в <prefix>\DLLs. Из-за этого frozen-сборка теряет
# OpenSSL: _ssl.pyd попадает в бандл, но libssl/libcrypto — нет, и
# `import ssl` падает с "DLL load failed". Вместе с этим исчезает HTTPS.
#
# Список получен разбором PE-таблиц импортов всех .pyd из <prefix>\DLLs плюс
# рекурсивное замыкание по импортам самих найденных DLL.
#
# Пути строим от sys.prefix, а не хардкодим, чтобы spec работал в venv и в
# любой другой conda/CPython-установке. Файлы, которых нет, пропускаем.
_CONDA_BIN = os.path.join(sys.prefix, 'Library', 'bin')

_MISSING_RUNTIME_DLLS = [
    'libssl-3-x64.dll',       # _ssl.pyd  -> HTTPS
    'libcrypto-3-x64.dll',    # _ssl.pyd, _hashlib.pyd
    'libexpat.dll',           # pyexpat.pyd -> XLSX (openpyxl)
    'liblzma.dll',            # lzma.pyd
    'zlib.dll',               # _zlib / zlib
    'LIBBZ2.dll',             # bz2
    'ffi.dll',                # _ctypes.pyd (stdlib ctypes) — вернуть: без него
                              # `import ctypes` падает с DLL load failed
    # sqlite3.dll УБРАН (2026-09-27): _sqlite3 ничто не импортирует —
    # аудит стартового графа это подтвердил, 1.4 МБ мёртвого веса.
    # ffi.dll ОСТАВЛЕН: нужен _ctypes.pyd из stdlib (без него `import ctypes`
    # падает с DLL load failed). cffi/pycares при этом исключены ниже.
    # UCRT-фроджеры: conda кладёт их рядом с DLL, без них не стартуют
    # модули, собранные против conda-тулчейна.
    'api-ms-win-crt-convert-l1-1-0.dll',
    'api-ms-win-crt-environment-l1-1-0.dll',
    'api-ms-win-crt-filesystem-l1-1-0.dll',
    'api-ms-win-crt-heap-l1-1-0.dll',
    'api-ms-win-crt-math-l1-1-0.dll',
    'api-ms-win-crt-runtime-l1-1-0.dll',
    'api-ms-win-crt-stdio-l1-1-0.dll',
    'api-ms-win-crt-string-l1-1-0.dll',
    'api-ms-win-crt-time-l1-1-0.dll',
    'api-ms-win-crt-utility-l1-1-0.dll',
]

binaries = []
for _dll in _MISSING_RUNTIME_DLLS:
    _src = os.path.join(_CONDA_BIN, _dll)
    if os.path.exists(_src):
        binaries.append((_src, '.'))
    else:
        print('[spec] пропущена отсутствующая DLL: %s' % _src)

# Модули, которых нет в графе импортов (проверено аудитом):
# tkinter/unittest/pydoc — stdlib-мусор хуков; sqlite3 — не используется;
# aiodns/pycares/cffi — мёртвый код, resolver всегда системный ThreadedResolver.
_EXCLUDES = [
    'tkinter', '_tkinter', 'tcl', 'tk',
    'unittest', 'pydoc', 'pydoc_data', 'doctest', 'pdb', 'bdb', 'cmd',
    'sqlite3',
    'aiodns', 'pycares', 'cffi', '_cffi_backend',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=[
        ('icon.png', '.'),       # иконка в UI (читается app/resources.py в рантайме)
        ('icon.ico', '.'),       # иконка exe
    ],
    hiddenimports=[
        'aiohttp',                # ленивый импорт в app/steam_api._aio()
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtNetwork',        # ленивый QNAM в ProfileSection
        'PyQt5.QtWidgets',
        'openpyxl',               # ленивый импорт в export_xlsx
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=_EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Qt-библиотеки, которые приложение не использует (нет QML/WebSockets/SVG):
# висят в бандле мёртвым грузом через хук PyQt5. Фильтруем по имени DLL.
# Qt5Network НЕ трогаем — нужен для аватаров.
_DROP_QT_LIBS = ('Qt5Quick', 'Qt5Qml', 'Qt5WebSockets', 'Qt5DBus', 'Qt5Svg')
a.binaries = [x for x in a.binaries
              if not os.path.basename(x[0]).startswith(_DROP_QT_LIBS)]
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SteamPlaytimeViewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,               # отключаем консольное окно
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',             # иконка для exe
)
