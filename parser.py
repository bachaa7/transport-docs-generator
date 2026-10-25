# -*- coding: utf-8 -*-
"""Разбор текста с данными водителя от перевозчика в поля формы.

Формат (стабильный, но допускаем отклонения):
    Авто: Даф АА 0003-7
    Прицеп: Шмитц АБ 0003-7
    Водитель: Кузнецов Кирилл Кириллович
    Паспорт: НВ 0000003 выдан Ленинским РОВД г.Минска 02.05.2024
    Тел.: +375 29 0000003 / +7 900 0000003

Парсер устойчив: не падает на отклонениях; что не распозналось — пустое поле.
"""
import re

EMPTY = {"avto": "", "pricep": "", "fio": "",
         "pasport_seria": "", "pasport_nomer": "", "pasport_vydan": "", "pasport_data": "",
         "tel_by": "", "tel_ru": ""}


def _after_label(text, labels):
    """Значение после метки в начале строки (метки — варианты написания)."""
    pat = r"^\s*(?:" + "|".join(labels) + r")[\s:\.\-]*(.+?)\s*$"
    for line in text.splitlines():
        m = re.match(pat, line, re.I)
        if m and m.group(1).strip():
            return m.group(1).strip()
    return ""


def parse_voditel(text):
    out = dict(EMPTY)
    if not text or not text.strip():
        return out

    out["avto"] = _after_label(text, [r"Авто", r"А/?м", r"Машина", r"ТС"])
    out["pricep"] = _after_label(text, [r"Прицеп", r"П/?п", r"Полуприцеп"])
    out["fio"] = _after_label(text, [r"Водитель", r"ФИО"])

    # --- паспорт ---
    pas = _after_label(text, [r"Паспорт", r"Пасп"])
    if pas:
        # серия: 1-3 буквы (кириллица/латиница); номер: 6-9 цифр (слитно или через пробел)
        m = re.match(r"\s*([A-Za-zА-Яа-яЁё]{1,3})\s*([0-9]{6,9})\b(.*)$", pas)
        if m:
            out["pasport_seria"] = m.group(1).strip()
            out["pasport_nomer"] = m.group(2).strip()
            rest = m.group(3).strip()
            # дата в конце: ДД.ММ.ГГГГ или ДД.ММ.ГГ (разделители . - /)
            dm = re.search(r"(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})\s*$", rest)
            if dm:
                out["pasport_data"] = dm.group(1)
                rest = rest[:dm.start()].strip()
            # выдан: после слова «выдан»; если слова нет — берём текст между номером и датой
            vm = re.search(r"выдан\w*\s*(.*)$", rest, re.I)
            out["pasport_vydan"] = (vm.group(1) if vm else rest).strip(" .,;")

    # --- телефоны ---
    tel = _after_label(text, [r"Тел", r"Телефон", r"Моб", r"Контакт"])
    if tel:
        parts = [p.strip() for p in re.split(r"\s*/\s*", tel) if p.strip()]
        if parts:
            out["tel_by"] = parts[0]
        if len(parts) > 1:
            out["tel_ru"] = parts[1]

    return out
