# -*- coding: utf-8 -*-
"""Сборка контекста для каждого документа из запроса + справочников.

Здесь живёт «склейка» данных: единый блок водителя, подтягивание адресов/контактов
из справочников, вычисление даты «действительна по» (+10 дней), русские даты,
и ПОДСТАНОВКА ДЕФОЛТОВ В КОДЕ (см. комментарий в config.py — почему не через Jinja).
"""
from datetime import date, datetime, timedelta
import config
import propis

_MES = {1: "Января", 2: "Февраля", 3: "Марта", 4: "Апреля", 5: "Мая", 6: "Июня",
        7: "Июля", 8: "Августа", 9: "Сентября", 10: "Октября", 11: "Ноября", 12: "Декабря"}


def _parse_date(s):
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Не понял дату '{s}' — нужен формат ГГГГ-ММ-ДД или ДД.ММ.ГГГГ")


def ru_date(s):
    """'2026-06-16' -> '16 Июня 2026 г.'"""
    d = s if isinstance(s, date) else _parse_date(s)
    return f"{d.day:02d} {_MES[d.month]} {d.year} г."


def _plus_days(s, n):
    return ru_date(_parse_date(s) + timedelta(days=n))


def _pasport_blob(v, prefix=""):
    """Паспорт одной строкой (для заявки/письма/ЗНП) из раздельных полей."""
    base = f"{v.pasport_seria} {v.pasport_nomer}".strip()
    if v.pasport_data:
        base += f", выдан {v.pasport_data}"
    if v.pasport_vydan:
        base += f" {v.pasport_vydan}"
    return (prefix + base).strip()


def _voditel_doc(v):
    """Единый блок водителя для заявки/письма (паспорт — одной строкой)."""
    return {"avto": v.avto, "pricep": v.pricep or "", "fio": v.fio,
            "pasport": _pasport_blob(v), "tel_by": v.tel_by or "", "tel_ru": v.tel_ru or ""}


def _sklad_to_gruzootpravitel(s):
    """Запись склада из справочника -> грузоотправитель шаблона (склейка контакта)."""
    naz = s["nazvanie"] + (f' / {s["ploshchadka"]}' if s.get("ploshchadka") else "")
    kontakt = f'{s.get("kontakt_lico", "")} {s.get("telefon", "")}'.strip()
    return {"nazvanie": naz, "adres": s["adres"], "kontakt": kontakt}


def _resolve_gruzootpraviteli(req, sprav):
    """Грузоотправители: ручной ввод (если задан) ИЛИ поиск по справочнику складов."""
    if req.gruzootpraviteli_manual:
        return [{"nazvanie": g.nazvanie, "adres": g.adres, "kontakt": g.kontakt}
                for g in req.gruzootpraviteli_manual]
    return [_sklad_to_gruzootpravitel(sprav.get_sklad(req.postavshchik, g)) for g in req.sklady]


def _resolve_vygruzka(req, sprav):
    """Точки выгрузки: если задано только название из справочника — подтянуть адрес/контакт."""
    out = []
    for v in req.vygruzka:
        adres, kontakt = v.adres, v.kontakt
        if v.nazvanie and (not adres or not kontakt):
            t = sprav.find_tochka(v.nazvanie)
            if t:
                adres = adres or t["adres"]
                kontakt = kontakt or t["kontakt"]
        out.append({"nazvanie": v.nazvanie or "", "adres": adres or "",
                    "kontakt": kontakt or "", "gruz": v.gruz or ""})
    return out


def _gruz_ctx(g):
    """Груз с подстановкой дефолтов в коде (а не через Jinja default — он не ловит '')."""
    stoimost = (g.stoimost or "").strip() or "1 500 000"
    if "руб" not in stoimost.lower():                    # валюту «рос. руб.» дописываем всегда
        stoimost += " рос. руб."
    return {
        "naimenovanie": g.naimenovanie or config.NAIMENOVANIE_DEFAULT,
        "gabarit": g.gabarit,
        "massa": (g.massa or "").strip() or config.MASSA_DEFAULT,
        "stoimost": stoimost,
        "upakovka": g.upakovka or config.UPAKOVKA_DEFAULT,
    }


# ---------- контексты документов ----------

def zayavka_context(req, sprav):
    gruzo = _resolve_gruzootpraviteli(req, sprav)
    marshrut = req.marshrut or f"{', '.join(req.sklady)} (Россия) – Минск (Беларусь)"
    kontakt = req.kontakt_vygruzki or config.KONTAKT_VYGRUZKI          # контакт выгрузки (п.14)
    # п.17: базовые инструкции + «сбросить фото на телефон <выбранный контакт>» (не хардкод Ивана)
    instrukcii = list(config.STANDARD_INSTRUKCII) + [config.INSTRUKCIA_FOTO.format(kontakt=kontakt)]
    return {
        # дата у номера (para «От …») = дата загрузки (п.2) — одно и то же поле
        "zayavka": {"nomer": req.zayavka_nomer, "data": req.data_zagruzki},
        "perevozchik": {"nazvanie": req.perevozchik},
        "marshrut": marshrut,
        "data_zagruzki": req.data_zagruzki,
        "voditel": _voditel_doc(req.voditel),
        "gruzootpraviteli": gruzo,
        "gruz": _gruz_ctx(req.gruz),
        "gruzopoluchatel": config.GRUZOPOLUCHATEL,
        "adresa_vygruzki": _resolve_vygruzka(req, sprav),
        "kontakt_vygruzki": kontakt,
        "srok_dostavki": config.SROK_DOSTAVKI,
        "stavka": {"summa": req.stavka_summa, "uslovie_oplaty": config.USLOVIE_OPLATY},
        "instrukcii": instrukcii,
    }


def doverennost_context(req, sprav, post):
    # post — реквизиты поставщика (из справочника ИЛИ ручные), резолвятся в main.py
    dover_data = req.dover_data or date.today().isoformat()
    # ТМЦ: количество вводится ЧИСЛОМ, прописью считает сервис (ручное прописью — перекрывает).
    tovary, total, have_total = [], 0.0, False
    for t in req.tovary:
        kol_propisyu = t.kol_propisyu or propis.propis(t.kol)
        n = propis.to_number(t.kol)
        if n is not None:
            total += n
            have_total = True
        tovary.append({"naimenovanie": t.naimenovanie, "ed": t.ed, "kol_propisyu": kol_propisyu})
    if not tovary:
        tovary = [{"naimenovanie": "Металлопрокат", "ed": "тн", "kol_propisyu": ""}]
    tovar_itogo = req.tovar_itogo or (propis.itogo(total) if have_total else "")
    # спецификация — ОТДЕЛЬНОЙ строкой в доверенности (под Договором), только если её ввели
    spec_stroka = ""
    if (req.spec_nomer or "").strip():
        spec_stroka = f"спецификация № {req.spec_nomer.strip()}"
        if (req.spec_data or "").strip():
            spec_stroka += f" от {req.spec_data.strip()}"
    return {
        "dover": {"deystv_po": _plus_days(dover_data, config.DOVER_SROK_DNEY),
                  "nomer": req.dover_nomer, "data": ru_date(dover_data)},
        "voditel": {"fio": req.voditel.fio, "pasport_seria": req.voditel.pasport_seria,
                    "pasport_nomer": req.voditel.pasport_nomer,
                    "pasport_vydan": req.voditel.pasport_vydan,
                    "pasport_data": req.voditel.pasport_data},
        "postavshchik": {"nazvanie": post["nazvanie"]},
        "osnovanie": post.get("osnovanie") or "___",
        "spec_stroka": spec_stroka,
        "tovary": tovary,
        "tovar_itogo": tovar_itogo,
    }


def pismo_context(req, sprav, post):
    adres = req.adres_sklada_vygruzki or (req.vygruzka[0].adres if req.vygruzka else "")
    return {
        "pismo": {"nomer": req.pismo_nomer or req.zayavka_nomer,
                  "data": req.pismo_data or req.data_zagruzki},
        "postavshchik": {"nazvanie": post["nazvanie"], "direktor_dat": post.get("direktor_dat") or "___"},
        "prilozheniya": [pr.model_dump() for pr in req.prilozheniya],
        "adres_sklada": adres,
        "voditel": _voditel_doc(req.voditel),
        # для строки «По доверенности № … от …» — берём ту же доверенность из пакета
        "dover": {"nomer": req.dover_nomer,
                  "data": ru_date(req.dover_data) if req.dover_data else ""},
    }


def znp_data(req, sprav):
    """Данные для заполнения ЗНП по карте полей (istochnik: voditel.* / reys.* / vygruzka.*)."""
    adres = ""
    if req.vygruzka:
        adres = _resolve_vygruzka(req, sprav)[0]["adres"]
    telefon = req.voditel.tel_ru or req.voditel.tel_by or ""   # рос. номер может не быть -> берём белорусский
    return {
        "voditel": {"fio": req.voditel.fio, "telefon": telefon,
                    "pasport": _pasport_blob(req.voditel, prefix="Паспорт "),
                    "avto": req.voditel.avto, "pricep": req.voditel.pricep or ""},
        "reys": {"data_otgruzki": req.data_otgruzki, "vremya_priezda": req.vremya_priezda,
                 "data_sozdaniya": req.data_otgruzki,
                 # ответственное лицо со стороны клиента = выбранный контакт выгрузки (не хардкод Ивана)
                 "otvetstvennoe": req.kontakt_vygruzki or config.KONTAKT_VYGRUZKI},
        "vygruzka": {"adres": adres},
    }
