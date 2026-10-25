# -*- coding: utf-8 -*-
"""Модели запроса /generate (то, что форма менеджера присылает напрямую в сервис).

Принцип по обязательности полей:
  ОБЯЗАТЕЛЬНО — то, без чего документ не имеет смысла (если нет — pydantic вернёт 422).
  НЕОБЯЗАТЕЛЬНО (= "") — то, что в «грязном» вводе бывает неполным. Такие поля не роняют
  запрос: документ соберётся, а validators.py пометит пробел на ручную проверку
  (принцип проекта «человек подтверждает», а не «падаем»).
"""
from pydantic import BaseModel, Field


class Voditel(BaseModel):
    fio: str                       # обязательно
    pasport_seria: str             # обязательно (нужно доверенности)
    pasport_nomer: str             # обязательно
    pasport_vydan: str = ""        # кем выдан — в грязном вводе бывает не сразу -> предупреждение
    pasport_data: str = ""         # дата выдачи — аналогично
    avto: str                      # обязательно
    pricep: str = ""               # может не быть (одиночка без прицепа)
    tel_by: str = ""               # хотя бы один телефон нужен (проверяем в валидации)
    tel_ru: str = ""               # рос. номер может и не быть


class Vygruzka(BaseModel):
    # Если задано только nazvanie и оно есть в справочнике точек — адрес/контакт подтянутся.
    nazvanie: str = ""
    adres: str = ""
    kontakt: str = ""
    gruz: str = ""                 # что именно выгружаем (на рейс)


class Gruz(BaseModel):
    naimenovanie: str = ""         # дефолт «металл» подставит context.py
    gabarit: str = ""
    massa: str = ""
    stoimost: str = ""             # дефолт «1 500 000 рос. руб.» подставит context.py
    upakovka: str = ""             # дефолт «Пачки, навал» подставит context.py


class Kontragent(BaseModel):
    # ручной грузоотправитель (склад не из справочника)
    nazvanie: str = ""
    adres: str = ""
    kontakt: str = ""


class PostavshchikManual(BaseModel):
    # ручной поставщик (нет в справочнике)
    nazvanie: str = ""
    osnovanie: str = ""                 # договор/контракт (для доверенности)
    direktor_dat: str = ""              # ФИО директора в дат. падеже (для письма)
    skladskoy_dokument: str = "net"     # znp | garant | net


class Tovar(BaseModel):
    naimenovanie: str = "Металлопрокат"
    ed: str = "тн"
    kol: str = ""              # количество числом (напр. "22" или "19.992") — прописью посчитает сервис
    kol_propisyu: str = ""     # можно задать вручную — перекроет авто-расчёт


class Prilozhenie(BaseModel):
    nomer: str
    data: str


class TripRequest(BaseModel):
    # --- обязательное ---
    postavshchik: str              # код: alfa/beta/... ИЛИ произвольный (если ручной ввод — см. ниже)
    perevozchik: str               # заявка адресована ему
    data_zagruzki: str
    voditel: Voditel
    vygruzka: list[Vygruzka]
    zayavka_nomer: str             # Исх. № заявки

    # --- грузоотправитель: ИЗ СПРАВОЧНИКА (sklady) ИЛИ РУЧНОЙ (gruzootpraviteli_manual) ---
    sklady: list[str] = Field(default_factory=list)               # города складов из справочника
    gruzootpraviteli_manual: list[Kontragent] = Field(default_factory=list)  # если задан — берём его, не справочник

    # --- поставщик: если postavshchik НЕ из справочника, реквизиты сюда ---
    postavshchik_manual: PostavshchikManual | None = None

    # --- необязательное ---
    gruz: Gruz = Field(default_factory=Gruz)
    marshrut: str = ""             # если пусто — соберём из складов
    stavka_summa: str = ""
    kontakt_vygruzki: str = ""     # контактное лицо выгрузки (п.14) — выбирается из списка в форме

    # доверенность
    dover_nomer: str = ""
    dover_data: str = ""           # ГГГГ-ММ-ДД или ДД.ММ.ГГГГ (по нему считаем «действительна по» +10)
    tovary: list[Tovar] = Field(default_factory=list)
    tovar_itogo: str = ""

    # ЗНП (только Альфа): путь к присланному файлу заказа от Альфа (.xlsm)
    znp_file: str = ""
    data_otgruzki: str = ""
    vremya_priezda: str = ""

    # гарантийное письмо (только Бета)
    pismo_nomer: str = ""
    pismo_data: str = ""
    prilozheniya: list[Prilozhenie] = Field(default_factory=list)
    adres_sklada_vygruzki: str = ""

    # спецификация к сделке (необязательно): файл кладётся в папку пакета как есть (не парсится)
    spec_file: str = ""        # серверный путь к загруженному файлу (через /upload_spec)
    spec_filename: str = ""    # оригинальное имя файла (как назвал менеджер)
    spec_nomer: str = ""       # № спецификации — печатается в доверенности после Договора
    spec_data: str = ""        # дата спецификации (как ввели, напр. 19.09.25)

    # подпись/печать — по умолчанию ВЫКЛ (чувствительно: ставит подпись директора + печать компании)
    sign: bool = False
