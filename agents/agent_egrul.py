import asyncio
import re
import time
from utils.logger import logger


def _find_chrome() -> str:
    import os as _os
    base = str(_os.path.expanduser("~/Library/Caches/ms-playwright"))
    if not _os.path.isdir(base):
        return ""
    for d in _os.listdir(base):
        if d.startswith("chromium-") and "headless" not in d:
            exe = _os.path.join(base, d, "chrome-mac-arm64",
                                "Google Chrome for Testing.app",
                                "Contents", "MacOS", "Google Chrome for Testing")
            if _os.path.isfile(exe):
                return exe
            exe2 = _os.path.join(base, d, "chrome-mac",
                                 "Chromium.app", "Contents", "MacOS", "Chromium")
            if _os.path.isfile(exe2):
                return exe2
    return ""


def _is_russian_name(s: str) -> bool:
    parts = s.strip().split()
    if len(parts) < 2:
        return False
    has_rus = any(ord(c) > 1024 for word in parts for c in word)
    if not has_rus:
        return False
    for word in parts:
        if not word.isupper():
            return False
        if not word.isalpha():
            return False
    return True


def _is_ip(lines: list) -> bool:
    has_fio = any(l.strip() == "ФИО:" for l in lines)
    has_ogrnip = any("огрнип" in l.lower() for l in lines)
    return has_fio or has_ogrnip


def _parse_pb_nalog(body: str, inn: str) -> dict:
    result = {"inn": inn, "is_demo": False}
    lines = [l.strip() for l in body.split("\n") if l.strip()]
    text = " ".join(lines)
    is_ip = _is_ip(lines)

    if is_ip:
        return _parse_ip_nalog(body, inn)
    return _parse_ul_nalog(body, inn)


def _parse_ip_nalog(body: str, inn: str) -> dict:
    result = {"inn": inn, "is_demo": False, "is_ip": True}
    lines = [l.strip() for l in body.split("\n") if l.strip()]
    text = " ".join(lines)

    for l in lines:
        if re.match(r"^ИП\s", l) and len(l) > 5:
            result["name"] = l
            break

    for i, l in enumerate(lines):
        if l == "ФИО:" and i + 1 < len(lines):
            result["fio"] = lines[i + 1]
            break

    for i, l in enumerate(lines):
        if "огрнип" in l.lower() and i + 1 < len(lines):
            result["ogrn"] = lines[i + 1]
            break

    for i, l in enumerate(lines):
        if "дата присвоения огрнип" in l.lower() or "дата присвоения" in l.lower() and i + 1 < len(lines):
            m = re.search(r"\d{2}\.\d{2}\.\d{4}", lines[i + 1])
            if m:
                result["registration_date"] = m.group(0)
                break

    for i, l in enumerate(lines):
        if "дата постановки на учёт" in l.lower() and i + 1 < len(lines):
            m = re.search(r"\d{2}\.\d{2}\.\d{4}", lines[i + 1])
            if m:
                result["reg_date"] = m.group(0)
                break
    if not result.get("registration_date") and not result.get("reg_date"):
        for i, l in enumerate(lines):
            m = re.search(r"\d{2}\.\d{2}\.\d{4}", l)
            if m and ("огрн" in lines[i-1].lower() if i > 0 else False):
                result["registration_date"] = m.group(0)
                break

    for i, l in enumerate(lines):
        if "основной вид деятельности" in l.lower() and i + 1 < len(lines):
            result["okved"] = lines[i + 1]
            break

    for i, l in enumerate(lines):
        if "налоговый орган" in l.lower() and "регистраци" in l.lower() and i + 1 < len(lines):
            result["ifns"] = lines[i + 1]
            break

    for i, l in enumerate(lines):
        if l == "ИНН:" and i + 1 < len(lines):
            result["inn_found"] = lines[i + 1]
            break

    if "действующий" in text.lower() or "действующая" in text.lower():
        result["status"] = "действующий"
    if "участник эдо" in text.lower():
        result["edo_participant"] = True

    for i, l in enumerate(lines):
        if "упрощенная" in l.lower() or "усн" in l.lower():
            result["tax_regime"] = "УСН"
            break
    if not result.get("tax_regime"):
        for i, l in enumerate(lines):
            if "специальные налоговые режимы" in l.lower() and i + 2 < len(lines):
                if "упрощенная" in lines[i + 2].lower() or "усн" in lines[i + 2].lower():
                    result["tax_regime"] = "УСН"
                    break

    if "микропредприятие" in text.lower():
        result["sme_status"] = "микропредприятие"
    elif "малое предприятие" in text.lower():
        result["sme_status"] = "малое"

    m = re.search(r"(\d+)\s*чел", text)
    if m:
        result["employees"] = int(m.group(1))

    logger.info(f"pb.nalog.ru: данные ИП получены")
    return result


def _parse_ul_nalog(body: str, inn: str) -> dict:
    result = {"inn": inn, "is_demo": False, "is_ip": False}
    lines = [l.strip() for l in body.split("\n") if l.strip()]
    text = " ".join(lines)

    for l in lines:
        if re.search(r'\b(ООО|АО|ПАО|ЗАО)\b', l):
            if len(l) > 6 and "предприниматель" not in l.lower() and l not in ("АО", "ООО", "ПАО", "ЗАО"):
                result["name"] = l
                break
    if not result.get("name"):
        for i, l in enumerate(lines):
            if "полное наименование" in l.lower():
                if i + 1 < len(lines) and len(lines[i + 1]) > 5:
                    result["name"] = lines[i + 1]
                    break

    for i, l in enumerate(lines):
        if "огрн:" in l.lower() and i + 1 < len(lines) and re.match(r"^\d{13,15}$", lines[i + 1]):
            result["ogrn"] = lines[i + 1]
            break

    for i, l in enumerate(lines):
        if "дата регистрации" in l.lower() and i + 1 < len(lines):
            m = re.search(r"\d{2}\.\d{2}\.\d{4}", lines[i + 1])
            if m:
                result["registration_date"] = m.group(0)
                break

    for i, l in enumerate(lines):
        if "адрес организации" in l.lower() and i + 1 < len(lines):
            result["address"] = lines[i + 1]
            break

    for i, l in enumerate(lines):
        if "основной вид деятельности" in l.lower() and i + 1 < len(lines):
            result["okved"] = lines[i + 1]
            break

    if "упрощенная" in text.lower() or "усн" in text.lower():
        result["tax_regime"] = "УСН"
    elif "общая система" in text.lower():
        result["tax_regime"] = "ОСНО"

    if "микропредприятие" in text.lower():
        result["sme_status"] = "микропредприятие"
    elif "малое предприятие" in text.lower():
        result["sme_status"] = "малое"

    # Director
    director_section_idx = None
    for i, l in enumerate(lines):
        if "имеющем право без доверенности действовать от имени" in l.lower():
            director_section_idx = i
            break

    if director_section_idx is not None:
        for offset in range(1, 5):
            idx = director_section_idx + offset
            if idx < len(lines) and _is_russian_name(lines[idx]):
                result["director_name"] = lines[idx]
                break

    if not result.get("director_name"):
        for i, l in enumerate(lines):
            if "директор" in l.upper() or "руководител" in l.lower() or "управляющий" in l.lower():
                for offset in (-5, -4, -3, -2, -1, 1, 2):
                    idx = i + offset
                    if 0 <= idx < len(lines) and _is_russian_name(lines[idx]):
                        result["director_name"] = lines[idx]
                        break
                if result.get("director_name"):
                    break

    for i, l in enumerate(lines):
        if l == "ИНН:" and director_section_idx is not None and i > director_section_idx and i < director_section_idx + 6:
            if i + 1 < len(lines) and re.match(r"^\d{12}$", lines[i + 1]):
                result["director_inn"] = lines[i + 1]
                break

    # Founders
    founders_start = None
    for i, l in enumerate(lines):
        if "учредител" in l.lower() or "участник" in l.lower() or "единственном акционере" in l.lower():
            founders_start = i
            break
    if founders_start is not None:
        for j in range(founders_start + 1, min(founders_start + 8, len(lines))):
            if _is_russian_name(lines[j]):
                result.setdefault("founders", []).append(lines[j])
            elif lines[j].startswith("Сведения о") or lines[j].startswith("Количество"):
                break

    if "действующая" in text.lower():
        result["status"] = "действующее"
    if "участник эдо" in text.lower():
        result["edo_participant"] = True

    # Financial data
    for i, l in enumerate(lines):
        if l == "Доход" and i + 1 < len(lines):
            m = re.search(r"([\d\s]+)\s*₽", lines[i + 1])
            if m:
                result["revenue"] = m.group(1).strip()
        if l == "Расход" and i + 1 < len(lines):
            m = re.search(r"([\d\s]+)\s*₽", lines[i + 1])
            if m:
                result["expenses"] = m.group(1).strip()
        if "уплаченная сумма" in l.lower() and i + 1 < len(lines):
            m = re.search(r"([\d\s]+)\s*₽", lines[i + 1])
            if m:
                result["tax_paid"] = m.group(1).strip()

    for i, l in enumerate(lines):
        if "уставный капитал" in l.lower():
            m = re.search(r"(\d[\d\s]*)\s*₽", l)
            if m:
                result["authorized_capital"] = m.group(1).strip()

    for i, l in enumerate(lines):
        if l == "Общая сумма" and i + 1 < len(lines):
            m = re.search(r"(\d[\d\s]*)\s*₽", lines[i + 1])
            if m:
                result["tax_debt"] = m.group(1).strip()
    if "не имеет задолженность" in text.lower():
        result["tax_debt"] = "0"

    m = re.search(r"(\d+)\s*чел", text)
    if m:
        result["employees"] = int(m.group(1))

    for i, l in enumerate(lines):
        if l == "КПП:" and i + 1 < len(lines):
            result["kpp"] = lines[i + 1]
            break

    rev_val = _parse_amount(result.get("revenue", "0"))
    tax_val = _parse_amount(result.get("tax_paid", "0"))
    if rev_val and tax_val and rev_val > 0:
        result["tax_burden_percent"] = round(tax_val / rev_val * 100, 1)

    return result


def _parse_amount(s: str) -> float:
    try:
        return float(s.replace(" ", "").replace(",", "."))
    except (ValueError, AttributeError):
        return 0.0


def _sync_fetch(inn: str) -> dict:
    chrome_path = _find_chrome()
    if not chrome_path:
        return {"source": "ЕГРЮЛ/Прозрачный бизнес", "error": "Chromium не найден"}

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                executable_path=chrome_path,
                args=["--no-sandbox"],
            )
            context = browser.new_context()
            page = context.new_page()

            page.goto("https://pb.nalog.ru/search.html", wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)

            page.fill("input[name='queryAll']", inn)
            page.press("input[name='queryAll']", "Enter")
            time.sleep(12)

            card = page.query_selector(".pb-card--clickable")
            if not card:
                browser.close()
                return {"source": "ЕГРЮЛ/Прозрачный бизнес", "error": "Карточка не найдена", "inn": inn}

            page.evaluate('document.querySelector(".pb-card--clickable").click()')
            time.sleep(22)

            body = page.inner_text("body")
            browser.close()

            parsed = _parse_pb_nalog(body, inn)
            is_ip = parsed.get("is_ip", False)

            founders_list = []
            for f_name in parsed.get("founders", []):
                founders_list.append({"fio": f_name, "inn": "", "share": ""})

            rev_val = _parse_amount(parsed.get("revenue", "0"))
            exp_val = _parse_amount(parsed.get("expenses", "0"))
            profit_val = rev_val - exp_val if rev_val and exp_val else 0

            result = {
                "source": "ЕГРЮЛ/Прозрачный бизнес (pb.nalog.ru)",
                "inn": inn,
                "ogrn": parsed.get("ogrn", ""),
                "kpp": parsed.get("kpp", ""),
                "full_name": parsed.get("name", ""),
                "short_name": parsed.get("name", ""),
                "reg_date": parsed.get("registration_date", "") or parsed.get("reg_date", ""),
                "address": parsed.get("address", ""),
                "ifns": parsed.get("ifns", ""),
                "tax_regime": parsed.get("tax_regime", ""),
                "okved_main": parsed.get("okved", ""),
                "okved_additional": [],
                "status": parsed.get("status", ""),
                "director": {"fio": parsed.get("director_name", "") or parsed.get("fio", ""), "inn": parsed.get("director_inn", "")},
                "founders": founders_list,
                "authorized_capital": str(parsed.get("authorized_capital", "")),
                "mass_address": False,
                "mass_director": False,
                "changes_history": [],
                "employees": parsed.get("employees", 0),
                "tax_debt": parsed.get("tax_debt", 0),
                "tax_paid": parsed.get("tax_paid", 0),
                "revenue": parsed.get("revenue", ""),
                "revenue_2025": parsed.get("revenue", ""),
                "expenses_2025": parsed.get("expenses", ""),
                "profit_2025": str(int(profit_val)) if profit_val else "",
                "tax_burden_percent": parsed.get("tax_burden_percent", 0),
                "is_ip": is_ip,
                "is_demo": parsed.get("is_demo", False),
                "error": None,
            }
            return result
    except Exception as e:
        logger.error(f"Playwright pb.nalog.ru error: {e}")
        return {"source": "ЕГРЮЛ/Прозрачный бизнес", "error": str(e), "inn": inn}


async def fetch(inn: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_fetch, inn)
