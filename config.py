# -*- coding: utf-8 -*-
"""Конфигурация: пути к шаблонам/справочникам и константы Ромашки.

INPUT_DIR  — где лежат шаблоны и справочники (по умолчанию ваша папка input_dir).
OUTPUT_DIR — куда складывать готовые документы.
Оба можно переопределить переменными окружения (удобно при деплое на Linux).
"""
import os
import sys
from pathlib import Path

# Корень для поиска/записи данных рядом с программой.
# Под .exe (PyInstaller, sys.frozen) — папка самого .exe, чтобы input_dir/assets_private/output/…
# лежали и писались РЯДОМ с .exe, а не во временной папке распаковки (_MEIPASS; в onefile она стирается).
# В обычном запуске (python) — папка с кодом. Переменные окружения ниже всё это переопределяют.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

# Шаблоны/справочники: по умолчанию папка input_dir рядом с кодом (в репозитории) — работает
# сразу после клонирования; при необходимости переопределяется переменной окружения INPUT_DIR.
INPUT_DIR = Path(os.environ.get("INPUT_DIR", str(BASE_DIR / "input_dir")))
# Результат: по умолчанию рядом с кодом (./output) — работает и на Windows, и на Linux; можно задать OUTPUT_DIR.
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", str(BASE_DIR / "output")))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
# Входящие файлы заказов Альфа (загрузка из формы) — в подпапке input (отдельно от результатов output).
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(INPUT_DIR / "upload_znp")))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Данные сервиса (счётчик исходящих номеров и т.п.).
DATA_DIR = Path(os.environ.get("DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
NUMBERS_FILE = DATA_DIR / "nomera.json"

# --- Шаблоны ---
TPL_ZAYAVKA    = INPUT_DIR / "ШАБЛОН_заявка_на_транспортную_перевозку.docx"
TPL_DOVERENOST = INPUT_DIR / "ШАБЛОН_доверенность_М-2.docx"
TPL_GARANT     = INPUT_DIR / "ШАБЛОН_гарантийное_письмо.docx"
TPL_ZNP        = INPUT_DIR / "ШАБЛОН_ЗНП_пустой.xlsx"   # ЗАПАСНОЙ (если файл от Альфа не прислан)
ZNP_KARTA      = INPUT_DIR / "ЗНП_карта_полей.yaml"

# --- Справочники ---
SPRAV_SKLADY        = INPUT_DIR / "spravochnik_sklady_pogruzki.yaml"
SPRAV_POSTAVSHCHIKI = INPUT_DIR / "spravochnik_postavshchiki.yaml"
SPRAV_TOCHKI        = INPUT_DIR / "spravochnik_tochki_vygruzki.yaml"
SPRAV_PEREVOZCHIKI  = INPUT_DIR / "spravochnik_perevozchiki.yaml"

# --- Подпись и печать (приватные картинки; НЕ в git, кладутся на сервер вручную) ---
ASSETS_DIR = Path(os.environ.get("ASSETS_DIR", str(BASE_DIR / "assets_private")))
SIGN_RUK   = ASSETS_DIR / "podpis_ruk.png"    # росчерк — руководитель (Иванов)
SIGN_BUH   = ASSETS_DIR / "podpis_buh.png"    # курсивная — гл. бухгалтер (Петрова)
PECHAT     = ASSETS_DIR / "pechat.png"        # печать ООО «Ромашка»
PODPIS_PECHAT = ASSETS_DIR / "podpis_pechat_ruk.png"   # склейка: росчерк Иванов + печать (один объект)

FILES = {
    "Заявка": TPL_ZAYAVKA,
    "Доверенность": TPL_DOVERENOST,
    "Гарантийное письмо": TPL_GARANT,
    "ЗНП шаблон (запасной)": TPL_ZNP,
    "ЗНП карта полей": ZNP_KARTA,
    "Справочник складов": SPRAV_SKLADY,
    "Справочник поставщиков": SPRAV_POSTAVSHCHIKI,
    "Справочник выгрузки": SPRAV_TOCHKI,
    "Справочник перевозчиков": SPRAV_PEREVOZCHIKI,
}


def check_files():
    """Проверка, что все шаблоны и справочники на месте (запуск: python config.py)."""
    ok = True
    for key, value in FILES.items():
        exists = value.exists()
        ok = ok and exists
        print(f"{'OK ' if exists else 'НЕТ'}  {key}: {value}")
    print("ИТОГО:", "все файлы на месте" if ok else "ЕСТЬ ОТСУТСТВУЮЩИЕ ФАЙЛЫ")
    return ok


# --- Константы и значения по умолчанию ---
# ВАЖНО: дефолты применяем здесь/в context.py (в коде), а НЕ через Jinja-фильтр default()
# в шаблоне. Причина: default() подставляет значение только если поле «не передано»,
# а на ПУСТУЮ строку ("") он НЕ срабатывает. Поэтому пустую стоимость и т.п. правильнее
# закрывать в коде ("значение or дефолт"), иначе в документе будет пусто.

# PDF-версии документов (через LibreOffice). ВЫКЛ для первой сборки .exe — LibreOffice не нужен.
# Подпись/печать и так вшиты в .docx, PDF — лишь нередактируемая копия. Включить позже: ENABLE_PDF = True
# (и поставить LibreOffice на машины). Весь PDF-код (generators.to_pdf) остаётся на месте.
ENABLE_PDF = False

GRUZOPOLUCHATEL  = "ООО «Ромашка»"
KONTAKT_VYGRUZKI = "+375 29 000-00-01 Иван"          # по умолчанию (п.14 заявки)
KONTAKTY_VYGRUZKI = [                                  # список для выпадающего в форме
    "+375 29 000-00-01 Иван",
    "+375 29 000-00-02 Мария",
    "+375 29 000-00-03 Пётр",
]
SROK_DOSTAVKI    = "1-2 дня"
USLOVIE_OPLATY   = "Оплата в течение 7 банковских дней с момента выставления акта выполненных работ"
STOIMOST_DEFAULT = "1 500 000 рос. руб."
MASSA_DEFAULT    = "20тн +/-10% т"
NAIMENOVANIE_DEFAULT = "металл"
UPAKOVKA_DEFAULT = "Пачки, навал"
DOVER_SROK_DNEY  = 10   # доверенность действительна = дата доверенности + N дней

STANDARD_INSTRUKCII = [
    "Документы из РФ никому на выгрузке не отдаем, отмечаем СМР (1 экз для водителя) и оставляем сертификаты.",
    "Просьба при погрузке обращать внимание на качество металла (визуально) – наличие ржавчины, "
    "дефектов, вмятин и т.д.! При наличии дефектов согласовать с менеджером загрузку!",
]
# 3-я инструкция (п.17 заявки): телефон берётся из выбранного контакта выгрузки (п.14),
# а не хардкодится — иначе при смене контакта в п.14 в п.17 оставался бы номер Ивана.
INSTRUKCIA_FOTO = ("После загрузки сбросить в хорошем качестве (читаемые) фото товарной накладной, "
                   "УПД, СМР на телефон {kontakt}.")


if __name__ == "__main__":
    check_files()
