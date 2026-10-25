# -*- mode: python ; coding: utf-8 -*-
# PyInstaller .spec — сборка сервиса документов DocGenerator в .exe (onedir).
#
#   Сборка:    pyinstaller doc_generator.spec
#   Результат: dist/DocGenerator/  (DocGenerator.exe + папка _internal/)
#
# Данные (input_dir, assets_private, form.html) НАМЕРЕННО НЕ вшиваются в .exe —
# их кладут РЯДОМ с .exe вручную, чтобы править без пересборки. См. СБОРКА_EXE.md.

from PyInstaller.utils.hooks import collect_submodules, collect_all, collect_data_files

# ── ПЕРЕКЛЮЧАТЕЛЬ КОНСОЛИ ──────────────────────────────────────────────
#   True  — окно консоли видно (видны ошибки) → для ОТЛАДКИ;
#   False — без консоли (чисто для менеджеров) → ФИНАЛЬНАЯ сборка.
DEBUG_CONSOLE = True

# ── скрытые импорты / данные библиотек ─────────────────────────────────
hiddenimports = []
datas = []
binaries = []

hiddenimports += collect_submodules('uvicorn')        # циклы/протоколы/lifespan (динамические)
hiddenimports += collect_submodules('pydantic')       # pydantic v2 (pydantic_core тянется хуком)
hiddenimports += ['multipart', 'python_multipart']    # приём файлов формой (lazy import в starlette)
hiddenimports += ['PIL._imaging', 'PIL.Image', 'PIL.PngImagePlugin']  # печать/подпись в ЗНП через openpyxl

_nw = collect_all('num2words')                        # язык RU подтягивается динамически
datas += _nw[0]; binaries += _nw[1]; hiddenimports += _nw[2]

datas += collect_data_files('docx')                   # python-docx: пакетный default.docx

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],          # ничего не исключаем для первой сборки (меньше риска «забыл нужное»)
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,        # onedir: бинарники в отдельной папке _internal (не один файл)
    name='DocGenerator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                    # UPX выключен — меньше ложных срабатываний антивируса
    console=DEBUG_CONSOLE,        # см. переключатель вверху
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='app.ico',       # если появится иконка — положить рядом и раскомментировать
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='DocGenerator',
)
