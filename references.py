# -*- coding: utf-8 -*-
"""Загрузка справочников (YAML) в память и поиск по ним.

Грузятся один раз при старте сервиса. При неверных данных методы бросают LookupError
с понятным текстом — его ловит эндпоинт и отдаёт как 400 (а не падает).
"""
import yaml
from config import SPRAV_SKLADY, SPRAV_TOCHKI, SPRAV_POSTAVSHCHIKI, SPRAV_PEREVOZCHIKI, ZNP_KARTA


def _load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


class Spravochniki:
    def __init__(self):
        self.sklady = _load_yaml(SPRAV_SKLADY)["postavshchiki"]
        self.postavshchiki = _load_yaml(SPRAV_POSTAVSHCHIKI)["postavshchiki"]
        self.vygruzka = _load_yaml(SPRAV_TOCHKI)["tochki"]
        # перевозчики — мягко: если файла нет (старый клон), просто пустой список, сервис не падает
        self.perevozchiki = (_load_yaml(SPRAV_PEREVOZCHIKI).get("perevozchiki", [])
                             if SPRAV_PEREVOZCHIKI.exists() else [])
        self.znp_karta = _load_yaml(ZNP_KARTA)

    def get_postavshchik(self, code):
        """Реквизиты поставщика по коду (alfa/beta/...)."""
        p = self.postavshchiki.get(code)
        if not p:
            raise LookupError(
                f"Поставщик '{code}' не найден в справочнике. "
                f"Доступны: {', '.join(self.postavshchiki)}"
            )
        return p

    def get_sklad(self, code, gorod):
        """Склад погрузки (грузоотправитель) по поставщику и городу."""
        block = self.sklady.get(code)
        if not block:
            raise LookupError(f"Поставщик '{code}' не найден в справочнике складов.")
        for s in block["sklady"]:
            if s["gorod"].strip().lower() == gorod.strip().lower():
                return s
        avail = ", ".join(s["gorod"] for s in block["sklady"])
        raise LookupError(f"Склад '{gorod}' не найден у поставщика '{code}'. Есть: {avail}")

    def find_tochka(self, nazvanie):
        """Точка выгрузки по названию (если есть в справочнике — вернёт адрес/контакт)."""
        if not nazvanie:
            return None
        for t in self.vygruzka:
            if t["nazvanie"].strip().lower() == nazvanie.strip().lower():
                return t
        return None
