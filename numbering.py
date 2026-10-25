# -*- coding: utf-8 -*-
"""Исходящие номера документов: формат ДДММ/N (дата + порядковый за день).

Счётчик хранится по дням в config.NUMBERS_FILE. «Наибольший выигрывает»: если менеджер
вписал номер вручную (напр. /10), счётчик дня подтянется до 10 — следующий будет /11.
Если у вас сквозная (не по-дневная) нумерация — поменяйте логику здесь, остальное не трогая.
"""
import json
import re
from datetime import date

import config


def _load():
    try:
        return json.loads(config.NUMBERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(d):
    config.NUMBERS_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def peek(offset=0):
    """Превью следующего номера (БЕЗ записи): ДДММ/(N+1+offset)."""
    t = date.today()
    cnt = _load().get(t.isoformat(), 0)
    return f"{t.strftime('%d%m')}/{cnt + 1 + offset}"


def dover_peek(offset=0):
    """Следующий № доверенности: «<N>-Д» — СКВОЗНОЙ счётчик, отдельный от Исх.№ (старт с 1)."""
    cnt = _load().get("dover", 0)
    return f"{cnt + 1 + offset}-Д"


def dover_commit(nomer):
    """Зафиксировать № доверенности: счётчик = max(текущий, число из «<N>-Д»). «Выигрывает больший»."""
    d = _load()
    cur = d.get("dover", 0)
    m = re.match(r"\s*(\d+)", nomer or "")
    hi = max(cur, int(m.group(1))) if m else cur
    if hi != cur:
        d["dover"] = hi
        _save(d)
    return d.get("dover", 0)


def info():
    """Данные для формы: дата сегодня + предлагаемые номера заявки и письма."""
    t = date.today()
    return {"date": t.strftime("%d.%m.%Y"), "ddmm": t.strftime("%d%m"),
            "zayavka": peek(0), "pismo": peek(1), "doverennost": dover_peek()}


def commit(nomera):
    """Зафиксировать: счётчик дня = max(текущий, наибольший /N среди выданных номеров)."""
    key = date.today().isoformat()
    d = _load()
    cur = d.get(key, 0)
    hi = cur
    for nm in nomera:
        m = re.search(r"/(\d+)\s*$", nm or "")
        if m:
            hi = max(hi, int(m.group(1)))
    if hi != cur:
        d[key] = hi
        _save(d)
    return d.get(key, 0)
