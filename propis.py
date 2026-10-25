# -*- coding: utf-8 -*-
"""Количество прописью (Вариант А, как в реальных доверенностях):
целое + ', ' + тысячные (килограммы) прописью, с заглавной буквы.

  22      -> 'Двадцать два'
  15      -> 'Пятнадцать'
  19.992  -> 'Девятнадцать , Девятьсот девяносто два'
  2.5     -> 'Два , Пятьсот'
"""
from num2words import num2words


def to_number(s):
    """'19,992' / '19.992' / 22 -> float; иначе None (на мусоре не падаем)."""
    try:
        return float(str(s).replace(",", ".").strip())
    except (ValueError, AttributeError, TypeError):
        return None


def propis(n):
    f = to_number(n)
    if f is None:
        return ""
    whole = int(f)
    words = num2words(whole, lang="ru").capitalize()
    frac = round(round(f - whole, 3) * 1000)          # тысячные = килограммы
    if frac:
        words += " , " + num2words(frac, lang="ru").capitalize()
    return words


def chislo(n):
    """Число без лишних нулей: 22.0->'22', 19.992->'19.992', 2.5->'2.5'."""
    f = to_number(n)
    if f is None:
        return ""
    return (f"{f:.3f}".rstrip("0").rstrip(".")) or "0"


def itogo(total):
    """Строка «Итого»: 'число (прописью)'."""
    f = to_number(total)
    if f is None:
        return ""
    return f"{chislo(f)} ({propis(f)})"
