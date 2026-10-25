# -*- coding: utf-8 -*-
"""FastAPI-сервис документов задачи C (Ромашка).

Эндпоинты:
  GET  /        — health-проверка.
  POST /generate — принимает данные поездки, возвращает пакет документов.

Состав пакета по поставщику (из справочника, поле skladskoy_dokument):
  всем           -> заявка + доверенность
  Альфа  (znp)    -> + ЗНП (заполнение присланного .xlsm по карте полей)
  Бета   (garant) -> + гарантийное письмо
"""
import io
import os
import re
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import Body, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response

import config
import context
import generators
import numbering
import parser
import validators
from references import Spravochniki
from schemas import TripRequest

app = FastAPI(title="Сервис документов — задача C (Ромашка)", version="1.1")
# CORS — чтобы кастомную форму можно было открывать/слать данные при необходимости.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Справочники грузим один раз при старте. Если файлы битые — запомним ошибку.
SPRAV = None
_SPRAV_ERR = None
try:
    SPRAV = Spravochniki()
except Exception as e:  # noqa: BLE001
    _SPRAV_ERR = f"{type(e).__name__}: {e}"


@app.get("/")
def health():
    if SPRAV is None:
        return {"ok": False, "oshibka": _SPRAV_ERR}
    return {"ok": True, "status": "сервис документов работает",
            "postavshchiki": list(SPRAV.postavshchiki), "output_dir": str(config.OUTPUT_DIR)}


@app.get("/spravochniki")
def spravochniki():
    """Справочники для формы: поставщики (с их складами) + точки выгрузки."""
    if SPRAV is None:
        raise HTTPException(500, f"Справочники не загружены: {_SPRAV_ERR}")
    posts = []
    for code, p in SPRAV.postavshchiki.items():
        sklady_block = SPRAV.sklady.get(code, {})
        sklady = [s["gorod"] for s in sklady_block.get("sklady", [])]
        posts.append({"code": code, "nazvanie": p["nazvanie"],
                      "skladskoy_dokument": p.get("skladskoy_dokument", "net"), "sklady": sklady})
    tochki = [{"nazvanie": t.get("nazvanie", ""), "adres": t.get("adres", ""),
               "kontakt": t.get("kontakt", "")} for t in SPRAV.vygruzka]
    perevozchiki = [{"nazvanie": p.get("nazvanie", "")} for p in SPRAV.perevozchiki]
    return {"postavshchiki": posts, "tochki_vygruzki": tochki, "perevozchiki": perevozchiki,
            "kontakty_vygruzki": config.KONTAKTY_VYGRUZKI}


@app.get("/form", response_class=HTMLResponse)
def form():
    """Кастомная веб-форма (HTML/JS). По умолчанию отправляет данные прямо в этот же сервис
    (/generate) — работает из коробки, без всякой настройки. При необходимости адрес можно
    переопределить через env GENERATE_URL (например, на внешний обработчик)."""
    html = (config.BASE_DIR / "form.html").read_text(encoding="utf-8")
    target = os.environ.get("GENERATE_URL", "/generate")
    return html.replace("__GENERATE_URL__", target)


@app.post("/upload_znp")
async def upload_znp(file: UploadFile = File(...)):
    """Приём файла заказа Альфа (.xlsm), выбранного в форме через проводник.
    Сохраняет на сервер и возвращает серверный путь — он уходит в TripRequest.znp_file."""
    up_dir = config.UPLOAD_DIR          # отдельно от output (входящие файлы Альфа)
    name = generators.safe_name(file.filename or "zakaz.xlsm")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = up_dir / f"{stamp}_{name}"
    dest.write_bytes(await file.read())
    return {"path": str(dest), "filename": file.filename or name}


@app.post("/upload_spec")
async def upload_spec(file: UploadFile = File(...)):
    """Приём файла спецификации к сделке (PDF/картинка — любой формат). Содержимое не читаем:
    сохраняем во временную папку, а в /generate кладём в папку пакета под оригинальным именем."""
    up_dir = config.UPLOAD_DIR
    name = generators.safe_name(file.filename or "specifikaciya")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = up_dir / f"spec_{stamp}_{name}"
    dest.write_bytes(await file.read())
    return {"path": str(dest), "filename": file.filename or name}


@app.post("/parse_voditel")
def parse_voditel_endpoint(payload: dict = Body(...)):
    """Разобрать вставленный текст перевозчика в поля водителя (для кнопки «Разобрать» в форме)."""
    return parser.parse_voditel(payload.get("text", ""))


@app.get("/next_nomer")
def next_nomer():
    """Сегодняшняя дата + предлагаемые Исх. № для заявки и письма (ДДММ/N). Превью, без записи."""
    return numbering.info()


def _pdf_if_needed(path, do_pdf):
    if not config.ENABLE_PDF:        # PDF отключён глобально (config.ENABLE_PDF) — без LibreOffice
        return None
    if not do_pdf:
        return None
    p = generators.to_pdf(path)
    return str(p) if p else None


# Плавающие подпись(и) и печать ПОВЕРХ прочерков (прочерки в шаблоне остаются — это линии подписи).
# Каждая запись: картинка, якорь-абзац, размер (h=высота ИЛИ w=ширина, мм), смещение dx/dy (мм).
def _sign_layout(doc_type):
    L = {
        "doverennost": [
            {"img": config.PECHAT,   "anchor": "Руководитель",      "w": 40, "dx": 22, "dy": -2, "z": 100},
            {"img": config.SIGN_RUK, "anchor": "Руководитель",      "h": 22, "dx": 32, "dy": -4, "z": 200},
            {"img": config.SIGN_BUH, "anchor": "Главный бухгалтер",  "h": 20, "dx": 46, "dy": -4, "z": 200},
        ],
        "zayavka": [
            {"img": config.PECHAT,   "anchor": "Директор", "w": 38, "dx": 60, "dy": -6, "z": 100},
            {"img": config.SIGN_RUK, "anchor": "Директор", "h": 22, "dx": 72, "dy": 0,  "z": 200},
        ],
        "pismo": [
            {"img": config.PECHAT,   "anchor": "Директор", "w": 38, "dx": 112, "dy": -12, "z": 100},
            {"img": config.SIGN_RUK, "anchor": "Директор", "h": 22, "dx": 124, "dy": -4,  "z": 200},
        ],
    }
    return L.get(doc_type, [])


def _apply_signatures(out_path, doc_type, sign):
    """Наложить плавающие подпись(и) и печать поверх прочерков, если sign И файлы на месте."""
    if not sign:
        return
    for it in _sign_layout(doc_type):
        if Path(it["img"]).exists():
            generators.add_floating_stamp(out_path, it["img"], it["anchor"],
                                          width_mm=it.get("w"), height_mm=it.get("h"),
                                          dx_mm=it["dx"], dy_mm=it["dy"], z=it.get("z", 251658240))


def _znp_sign_images(sign):
    """Подпись+печать для ЗНП (Excel), область подписи Покупателя (ячейка L26:P27).
    Печать первой → подпись поверх. Якоря/размеры подгоняются."""
    if not sign:
        return []
    imgs = []
    if Path(config.PECHAT).exists():
        imgs.append({"img": config.PECHAT, "anchor": "L26", "h": 240, "dx": 95, "dy": -30})  # печать крупнее, выше, правее
    if Path(config.SIGN_RUK).exists():
        imgs.append({"img": config.SIGN_RUK, "anchor": "I26", "h": 170, "dx": 0, "dy": 8})  # подпись: штрих над ФИО (центр I)
    return imgs


@app.post("/generate")
def generate(req: TripRequest, pdf: bool = Query(False, description="Сделать PDF (нужен LibreOffice)")):
    if SPRAV is None:
        raise HTTPException(500, f"Справочники не загружены: {_SPRAV_ERR}")

    code = req.postavshchik.strip().lower()
    req = req.model_copy(update={"postavshchik": code})

    # 1) поставщик: из справочника ИЛИ ручные реквизиты (postavshchik_manual)
    try:
        post = SPRAV.get_postavshchik(code)
    except LookupError as e:
        pm = req.postavshchik_manual
        if pm and (pm.nazvanie or "").strip():
            post = {"nazvanie": pm.nazvanie, "osnovanie": pm.osnovanie,
                    "direktor_dat": pm.direktor_dat, "skladskoy_dokument": pm.skladskoy_dokument or "net"}
        else:
            raise HTTPException(400, str(e) + " Если поставщика нет в справочнике — заполните postavshchik_manual.")

    # 2) состав пакета по поставщику
    sklad_dok = post.get("skladskoy_dokument", "net")
    sostav = ["zayavka"]
    if sklad_dok != "znp":           # для Альфа (идёт ЗНП) доверенность НЕ делаем
        sostav.append("doverennost")
    if sklad_dok == "znp":
        sostav.append("znp")
    elif sklad_dok == "garant":
        sostav.append("pismo")

    warnings = validators.validate(req)

    # 3) источник ЗНП: присланный Альфа файл; если его нет — запасной пустой шаблон + предупреждение
    znp_src = None
    if "znp" in sostav:
        if req.znp_file:
            p = Path(req.znp_file)
            znp_src = p if p.is_absolute() else (config.INPUT_DIR / p)
            if not znp_src.exists():
                raise HTTPException(400, f"Файл заказа Альфа не найден: {znp_src}")
        else:
            znp_src = config.TPL_ZNP   # запасной пустой бланк
            warnings.append({"pole": "znp_file",
                             "soobshchenie": "Файл заказа от Альфа не передан — использован пустой "
                                             "шаблон ЗНП (продукция и объём НЕ заполнены)."})

    # 4) генерация. Папка по сеансу: output/{ПОСТАВЩИК}_{Исх№}_{дата-время}/ —
    #    поставщик в начале (видно сразу, что за рейс), дата-время чтобы рейсы не перетирались.
    nm = generators.safe_name(req.zayavka_nomer)
    post_tag = generators.safe_name(code).upper()        # ALFA / BETA / GAMMA (для ручного — его название)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    core = f"{nm}_{stamp}" if (req.zayavka_nomer or "").strip() else stamp
    session_name = f"{post_tag}_{core}"
    session_dir = config.OUTPUT_DIR / session_name
    session_dir.mkdir(parents=True, exist_ok=True)
    dokumenty = []
    try:
        for tip in sostav:
            if tip == "zayavka":
                out = session_dir / f"zayavka_{nm}.docx"
                generators.render_docx(config.TPL_ZAYAVKA, context.zayavka_context(req, SPRAV), out)
                _apply_signatures(out, "zayavka", req.sign)
                dokumenty.append({"tip": "zayavka", "fail": out.name, "put": str(out),
                                  "pdf": _pdf_if_needed(out, pdf or req.sign)})

            elif tip == "doverennost":
                out = session_dir / f"doverennost_{nm}.docx"
                generators.render_docx(config.TPL_DOVERENOST, context.doverennost_context(req, SPRAV, post), out)
                _apply_signatures(out, "doverennost", req.sign)
                dokumenty.append({"tip": "doverennost", "fail": out.name, "put": str(out),
                                  "pdf": _pdf_if_needed(out, pdf or req.sign)})

            elif tip == "pismo":
                out = session_dir / f"pismo_{nm}.docx"
                generators.render_docx(config.TPL_GARANT, context.pismo_context(req, SPRAV, post), out)
                _apply_signatures(out, "pismo", req.sign)
                dokumenty.append({"tip": "pismo", "fail": out.name, "put": str(out),
                                  "pdf": _pdf_if_needed(out, pdf or req.sign)})

            elif tip == "znp":
                # расширение как у исходного бланка: присланный .xlsm остаётся .xlsm (с макросами),
                # демо-бланк .xlsx — .xlsx (иначе Excel не откроет файл с чужим расширением)
                out = session_dir / f"znp_{nm}{Path(znp_src).suffix.lower() or '.xlsm'}"
                _, missed = generators.fill_znp(znp_src, SPRAV.znp_karta,
                                                context.znp_data(req, SPRAV), out,
                                                images=_znp_sign_images(req.sign))
                if missed:
                    warnings.append({"pole": "znp",
                                     "soobshchenie": f"В ЗНП не нашлись поля: {missed} — проверьте бланк."})
                dokumenty.append({"tip": "znp", "fail": out.name, "put": str(out), "pdf": None})

    except LookupError as e:          # склад не найден и т.п.
        raise HTTPException(400, str(e))
    except Exception as e:            # noqa: BLE001
        raise HTTPException(500, f"Ошибка генерации документа: {type(e).__name__}: {e}")

    # спецификация (необязательно): кладём приложенный файл в папку пакета как есть, не парсим.
    # Имя — оригинальное, очищенное safe_name (защита от path traversal); сбой не рушит пакет.
    if (req.spec_file or "").strip():
        src = Path(req.spec_file)
        src = src if src.is_absolute() else (config.UPLOAD_DIR / src)
        spec_name = generators.safe_name(req.spec_filename or src.name)
        dest = (session_dir / spec_name).resolve()
        if not src.exists():
            warnings.append({"pole": "spec_file",
                             "soobshchenie": f"Приложенная спецификация не найдена на сервере: {src}"})
        elif session_dir.resolve() != dest.parent:        # имя вырвалось бы из папки пакета — отклоняем
            warnings.append({"pole": "spec_file",
                             "soobshchenie": f"Имя файла спецификации отклонено: {spec_name}"})
        else:
            try:
                shutil.copyfile(src, dest)
                dokumenty.append({"tip": "specifikaciya", "fail": dest.name,
                                  "put": str(dest), "pdf": None})
            except Exception as e:    # noqa: BLE001
                warnings.append({"pole": "spec_file",
                                 "soobshchenie": f"Не удалось сохранить спецификацию: {type(e).__name__}: {e}"})

    # зафиксировать счётчик исходящих номеров (заявка всегда; письмо — если в пакете)
    used_nomera = [req.zayavka_nomer]
    if "pismo" in sostav:
        used_nomera.append(req.pismo_nomer or req.zayavka_nomer)
    numbering.commit(used_nomera)
    if "doverennost" in sostav:
        numbering.dover_commit(req.dover_nomer)   # сквозной счётчик доверенностей (N-Д)

    return {
        "ok": True,
        "postavshchik": post["nazvanie"],
        "papka": str(session_dir),
        "session": session_name,        # имя папки сеанса — для ссылок на скачивание из формы
        "sostav_paketa": sostav,
        "dokumenty": dokumenty,
        "predupezhdeniya": warnings,
    }


@app.get("/files/{session}/{name}")
def download(session: str, name: str):
    """Отдать готовый документ на скачивание. Только из OUTPUT_DIR (защита от обхода путей)."""
    base = config.OUTPUT_DIR.resolve()
    target = (base / session / name).resolve()
    if base not in target.parents or not target.is_file():
        raise HTTPException(404, "Файл не найден")
    return FileResponse(str(target), filename=name)


@app.get("/zip/{session}")
def download_zip(session: str):
    """Скачать ВСЕ документы сеанса одним ZIP. Только из OUTPUT_DIR (защита от обхода путей)."""
    base = config.OUTPUT_DIR.resolve()
    sess_dir = (base / session).resolve()
    if base not in sess_dir.parents or not sess_dir.is_dir():
        raise HTTPException(404, "Папка сеанса не найдена")
    files = [f for f in sorted(sess_dir.iterdir()) if f.is_file()]
    if not files:
        raise HTTPException(404, "В папке сеанса нет файлов")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, arcname=f.name)        # кладём только имена файлов, без путей
    zip_name = re.sub(r"[^A-Za-z0-9._-]", "_", session) + ".zip"
    return Response(content=buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{zip_name}"'})


def _notify(title, msg):
    """Сообщение пользователю — работает и без консоли (MessageBox на Windows), иначе print."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, msg, title, 0x40)   # MB_ICONINFORMATION
    except Exception:
        try:
            print(f"{title}: {msg}")
        except Exception:
            pass


def _port_busy(host, port):
    """Занят ли порт — значит сервис уже запущен (защита от второго экземпляра)."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def _open_browser_later(url, delay=1.2):
    """Открыть браузер на форме через паузу, чтобы сервер успел подняться (фоновый поток)."""
    import threading
    import time
    import webbrowser

    def _go():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_go, daemon=True).start()


def run_app():
    host, port = "127.0.0.1", 8077
    url = f"http://{host}:{port}/form"
    # под .exe без консоли stdout/stderr = None → логирование uvicorn может падать; уводим в «никуда»
    if getattr(sys, "frozen", False):
        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
        if sys.stderr is None:
            sys.stderr = open(os.devnull, "w", encoding="utf-8")
    # второй запуск / порт занят — не падаем: открываем форму уже работающего сервиса и выходим
    if _port_busy(host, port):
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass
        _notify("Сервис документов «Ромашка»",
                f"Программа уже запущена — открыл форму в браузере:\n{url}")
        return
    _open_browser_later(url)
    # app — объект (не строка "main:app"): нужно для запуска из .exe; reload=False обязателен под заморозкой
    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()   # PyInstaller: иначе при заморозке возможны повторные окна
    run_app()
