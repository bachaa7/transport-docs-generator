# -*- coding: utf-8 -*-
"""Лёгкая валидация ключевых полей.

Принцип проекта: «человек подтверждает», парсер «умеет сказать не смог». Здесь мы
НЕ роняем генерацию, а возвращаем список предупреждений — что сотруднику проверить.
"""
import re


def validate(req):
    w = []
    v = req.voditel

    # --- паспорт: серия и номер ---
    nomer = (v.pasport_nomer or "").replace(" ", "")
    if not re.fullmatch(r"\d{6,9}", nomer):
        w.append({"pole": "voditel.pasport_nomer",
                  "soobshchenie": f"Номер паспорта '{v.pasport_nomer}' выглядит необычно — проверьте."})
    if not re.fullmatch(r"[A-ZА-Я]{1,3}", (v.pasport_seria or "").strip()):
        w.append({"pole": "voditel.pasport_seria",
                  "soobshchenie": f"Серия паспорта '{v.pasport_seria}' необычная — проверьте."})

    # --- паспорт: кем/когда выдан (нужно доверенности; могут отсутствовать в грязном вводе) ---
    if not (v.pasport_vydan or "").strip():
        w.append({"pole": "voditel.pasport_vydan",
                  "soobshchenie": "Не указано, кем выдан паспорт — нужно для доверенности, проверьте."})
    if not (v.pasport_data or "").strip():
        w.append({"pole": "voditel.pasport_data",
                  "soobshchenie": "Не указана дата выдачи паспорта — нужно для доверенности, проверьте."})

    # --- телефон: хотя бы один (рос. может не быть, но один нужен) ---
    if not (v.tel_by or "").strip() and not (v.tel_ru or "").strip():
        w.append({"pole": "voditel.telefon",
                  "soobshchenie": "У водителя не указан ни один телефон — проверьте."})

    # --- масса: число в разумном диапазоне 0–25 т ---
    m = re.search(r"\d+[.,]?\d*", req.gruz.massa or "")
    if not m:
        w.append({"pole": "gruz.massa", "soobshchenie": "Масса не распознана — проверьте."})
    else:
        val = float(m.group(0).replace(",", "."))
        if not (0 < val <= 25):
            w.append({"pole": "gruz.massa",
                      "soobshchenie": f"Масса {val} т вне разумного диапазона 0–25 т — проверьте."})

    # --- стоимость: цена у каждой поставки разная; если пусто — в документах будет пробел.
    #     Оставляем пусто намеренно (видно, что не заполнили), но мягко напоминаем. ---
    if not (req.gruz.stoimost or "").strip():
        w.append({"pole": "gruz.stoimost",
                  "soobshchenie": "Стоимость груза не указана — в документах останется пусто, проверьте."})

    return w
