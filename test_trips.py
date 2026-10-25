# -*- coding: utf-8 -*-
"""Тест сервиса на двух поездках (Альфа и Бета) + проверка ошибки и валидации.

Запуск из этой папки:  python test_trips.py
Использует FastAPI TestClient — отдельный сервер поднимать не нужно.
"""
import os
import sys
import json
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
from fastapi.testclient import TestClient
import config
from main import app

client = TestClient(app)

# Альфа (Северный -> Минск): пакет = заявка + доверенность + ЗНП
ALFA = {
    "postavshchik": "alfa",
    "sklady": ["Северный"],
    "perevozchik": "ООО «ТрансЛогистик»",
    "data_zagruzki": "16.06.2026 г",
    "voditel": {
        "fio": "Петров Пётр Петрович",
        "pasport_seria": "НВ", "pasport_nomer": "0000001",
        "pasport_vydan": "Центральным РОВД г. Минска", "pasport_data": "01.12.2020",
        "avto": "DAF XF АА 0001-7", "pricep": "SCHMITZ АБ 0001-7",
        "tel_by": "+375 29 000-00-31", "tel_ru": "+7 900 000-00-31",
    },
    "vygruzka": [{"nazvanie": "ООО «Ромашка»", "adres": "г. Минск, ул. Складская, 10",
                  "kontakt": "Александр +375 29 000-00-11"}],
    "gruz": {"gabarit": "Мах дл 6м", "massa": "20 тн +/-10%"},
    "stavka_summa": "1100р",
    "zayavka_nomer": "1606/2",
    "dover_nomer": "281", "dover_data": "2026-06-16",
    "tovary": [{"naimenovanie": "Металлопрокат", "kol_propisyu": "Двадцать"}],
    "tovar_itogo": "20 (Двадцать)",
    # путь к присланному файлу заказа Альфа (в проде грузится через форму /upload_znp;
    # здесь — демо-бланк из input_dir, путь относительно INPUT_DIR)
    "znp_file": "ШАБЛОН_ЗНП_пустой.xlsx",
    "data_otgruzki": "16.06.2026", "vremya_priezda": "14.00 - 16.00",
}

# Бета (Заречный+Лесной -> Минск): пакет = заявка + доверенность + письмо
# (у этого водителя НЕТ рос. номера — проверяем, что не падаем)
BETA = {
    "postavshchik": "beta",
    "sklady": ["Заречный", "Лесной"],
    "perevozchik": "ЧУП «Быстрый груз»",
    "data_zagruzki": "16.06.2026 г",
    "voditel": {
        "fio": "Сидоров Сидор Сидорович",
        "pasport_seria": "МР", "pasport_nomer": "0000002",
        "pasport_vydan": "Ленинским РУВД г. Минска", "pasport_data": "17.05.2015",
        "avto": "MAN TGX АВ 0002-7", "pricep": "SCHMITZ АБ 0002-7",
        "tel_by": "+375 29 000-00-32",       # tel_ru не задан — допустимо
    },
    "vygruzka": [
        {"nazvanie": "ООО «Стройпарк»", "gruz": "Выгружаем трубу 100х100х8"},  # адрес/контакт из справочника
        {"nazvanie": "ООО «Ромашка»", "adres": "г. Минск, ул. Кооперативная, 30",
         "kontakt": "Наталья +375 29 000-00-13", "gruz": "Остальное"},
    ],
    "gruz": {"gabarit": "Мах дл 12м", "massa": "15 тн +/-10%"},
    "stavka_summa": "1500р",
    "zayavka_nomer": "1606/3",
    "dover_nomer": "282", "dover_data": "2026-06-16",
    "tovary": [{"naimenovanie": "Труба профильная 100х100х8", "kol_propisyu": "Пятнадцать"}],
    "tovar_itogo": "15 (Пятнадцать)",
    "pismo_nomer": "160626/01", "pismo_data": "16.06.2026 г.",
    "prilozheniya": [{"nomer": "000101", "data": "08.06.2026 г."},
                     {"nomer": "000102", "data": "08.06.2026 г."}],
    "adres_sklada_vygruzki": "г. Минск, ул. Кооперативная, 30",
}

BAD = dict(ALFA, postavshchik="neizvestnyy")   # поставщик не из справочника


def call(name, payload):
    r = client.post("/generate", json=payload)
    print("\n" + "=" * 70 + f"\n{name}: HTTP {r.status_code}\n" + "=" * 70)
    print(json.dumps(r.json(), ensure_ascii=False, indent=2))


print("HEALTH:", json.dumps(client.get("/").json(), ensure_ascii=False))
call("ПОЕЗДКА Альфа", ALFA)
call("ПОЕЗДКА Бета (без рос. номера)", BETA)
call("ОШИБКА (поставщик не из справочника)", BAD)

print("\n--- файлы в output ---")
for f in sorted(glob.glob(str(config.OUTPUT_DIR / "*"))):
    print("  ", os.path.basename(f), os.path.getsize(f), "байт")
