import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import Optional

from config import CACHE_DIR
from utils.ai_client import ask
from utils.logger import logger

CACHE_TTL = timedelta(hours=24)

SYSTEM_BRIEF = (
    "Ты — профессиональный налоговый аналитик, специалист по предпроверочному анализу ФНС, "
    "налоговым рискам, корпоративной безопасности и проверке контрагентов. "
    "Твоя задача — собирать, анализировать и структурировать информацию об организациях "
    "и индивидуальных предпринимателях на основании открытых и законно доступных источников, "
    "выявлять налоговые, финансовые, корпоративные и репутационные риски.\n\n"
    "Клиент: собственник бизнеса или налоговый консультант. "
    "Пиши простым русским языком, без юридических терминов. "
    "В конце укажи главный вывод: работать с компанией можно / осторожно / нельзя."
)

SYSTEM_DETAILED = (
    "Ты — профессиональный налоговый аналитик, специалист по предпроверочному анализу ФНС, "
    "налоговым рискам, корпоративной безопасности и проверке контрагентов.\n\n"
    "Клиент: налоговый консультант. Выполни полный разбор компании по каждому блоку рисков. "
    "Для каждого риска укажи: суть проблемы, цифры (суммы, количество), уровень опасности. "
    "В конце — сводная таблица рисков и итоговый вывод."
)

SYSTEM_COMPARE = (
    "Ты — профессиональный налоговый аналитик, специалист по предпроверочному анализу ФНС, "
    "налоговым рискам, корпоративной безопасности и проверке контрагентов.\n\n"
    "Клиент: аналитик. Сравни показатели компании со среднеотраслевыми по ОКВЭД. "
    "Оцени: налоговая нагрузка, выручка, сотрудники, судебные дела. "
    "Укажи отклонения от нормы и вывод: стандартный риск / повышенное внимание / высокий риск."
)

SYSTEMS = {
    "brief": SYSTEM_BRIEF,
    "detailed": SYSTEM_DETAILED,
    "compare": SYSTEM_COMPARE,
}

MAX_TOKENS = {
    "brief": 1024,
    "detailed": 2048,
    "compare": 1536,
}


def _build_prompt(report_data: dict) -> str:
    agent = report_data.get("agent_data", {})
    eg = agent.get("agent_egrul", {})
    tp = agent.get("agent_transparent", {})
    fssp = agent.get("agent_fssp", {})
    ar = agent.get("agent_arbitr", {})
    br = agent.get("agent_bankrupt", {})
    md = agent.get("agent_media", {})
    cx = agent.get("agent_crosscheck", {})
    sc = report_data.get("scoring", {})
    sp = report_data.get("splitting", {})
    tc = report_data.get("technical", {})
    top3 = report_data.get("top3_risks", [])
    recs = report_data.get("recommendations", [])

    def v(val):
        return str(val) if val is not None and val != "" else "—"

    def fmt(val):
        if val is None or val == "" or val == 0:
            return "—"
        try:
            vv = float(val)
            if abs(vv) >= 1_000_000:
                return f"{vv / 1_000_000:.2f} млн"
            if abs(vv) >= 1_000:
                return f"{vv / 1_000:.1f} тыс"
            return f"{vv:.0f}"
        except (ValueError, TypeError):
            return str(val)

    name = v(eg.get("short_name") or eg.get("full_name"))
    inn = v(eg.get("inn"))

    lines = [
        f"Компания: {name} (ИНН {inn})",
        f"Статус: {v(eg.get('status'))}",
        f"ОГРН: {v(eg.get('ogrn'))} | ОКВЭД: {v(eg.get('okved_main'))}",
        f"Адрес: {v(eg.get('address'))}",
        f"Дата регистрации: {v(eg.get('reg_date'))}",
        f"Уставной капитал: {fmt(eg.get('authorized_capital'))} ₽",
        f"Сотрудники: {v(eg.get('employees'))}",
        f"Налоговый режим: {v(eg.get('tax_regime'))}",
        f"Массовый руководитель: {v(eg.get('mass_director'))}",
        f"Массовый адрес: {v(eg.get('mass_address'))}",
        "",
        "Финансы:",
        f"  Выручка (2025): {fmt(eg.get('revenue_2025'))} ₽",
        f"  Прибыль (2025): {fmt(eg.get('profit_2025'))} ₽",
        f"  Налоговый долг: {fmt(tp.get('tax_debt', eg.get('tax_debt', 0)))} ₽",
        f"  Налоги уплачено: {fmt(tp.get('taxes_paid', 0))} ₽",
        f"  Налоговая нагрузка: {v(tp.get('tax_burden_percent', eg.get('tax_burden_percent', 0)))}%",
        f"  Доходы: {fmt(tp.get('income', 0))} ₽",
        f"  Расходы: {fmt(tp.get('expenses', 0))} ₽",
        "",
        "Скоринг рисков:",
        f"  Общий: {sc.get('total_score', 0)}/100 — {v(sc.get('total_level'))}",
        f"  Налоговый: {sc.get('tax_score', 0)}/100",
        f"  Финансовый: {sc.get('financial_score', 0)}/100",
        f"  Корпоративный: {sc.get('corporate_score', 0)}/100",
        f"  Репутационный: {sc.get('reputation_score', 0)}/100",
        "",
        f"Дробление бизнеса: {v(sp.get('conclusion'))}",
        f"Техническая компания: {v(tc.get('conclusion'))}",
        "",
        "Судебные дела:",
        f"  Всего: {v(ar.get('total_cases', 0))}",
        f"  Как ответчик: {v(ar.get('as_defendant', 0))}",
        f"  Налоговые споры: {v(ar.get('tax_disputes', 0))}",
        f"  Сумма исков: {fmt(ar.get('total_claims_amount', 0))} ₽",
        "",
        f"Исполнительные производства (ФССП):",
        f"  Всего: {v(fssp.get('total_proceedings', 0))}",
        f"  Общий долг: {fmt(fssp.get('total_debt', 0))} ₽",
        "",
        f"Банкротства: {'есть' if br.get('has_bankruptcy') else 'нет'} "
        f"(записей: {v(br.get('total_records', 0))})",
        "",
        f"СМИ/репутация: {v(md.get('overall_sentiment'))}",
        f"Показатели дробления: {v(cx.get('splitting_indicators_count', 0))}",
    ]

    if top3 and top3 != ["Значимых рисков не выявлено"]:
        lines.append("")
        lines.append("Ключевые риски:")
        for r in top3[:3]:
            lines.append(f"  • {r}")

    if recs:
        lines.append("")
        lines.append("Рекомендации:")
        for r in recs[:5]:
            lines.append(f"  • {r}")

    return "\n".join(lines)


def _cache_path(data_hash: str) -> str:
    return os.path.join(CACHE_DIR, f"ai_{data_hash}.json")


def _load_cache(data_hash: str) -> Optional[str]:
    path = _cache_path(data_hash)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            entry = json.load(f)
        saved = datetime.fromisoformat(entry["saved_at"])
        if datetime.now() - saved > CACHE_TTL:
            os.remove(path)
            return None
        logger.info("AI-резюме взято из кеша")
        return entry["summary"]
    except Exception:
        return None


def _save_cache(data_hash: str, summary: str):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = _cache_path(data_hash)
    try:
        with open(path, "w") as f:
            json.dump({"summary": summary, "saved_at": datetime.now().isoformat()}, f)
    except Exception as e:
        logger.warning(f"Не удалось сохранить кеш AI: {e}")


async def fetch(report_data: dict, mode: str = "brief") -> dict:
    try:
        data_str = _build_prompt(report_data)
        data_hash = hashlib.md5(data_str.encode()).hexdigest()

        cached = _load_cache(data_hash)
        if cached:
            return {"summary": cached, "error": None, "cached": True}

        system = SYSTEMS.get(mode, SYSTEMS["brief"])
        max_tok = MAX_TOKENS.get(mode, 1024)
        summary = await ask(system, data_str, max_tokens=max_tok)

        if not summary.startswith("❌"):
            _save_cache(data_hash, summary)

        logger.info(f"AI-резюме готово ({mode}, {len(summary)} символов)")
        return {"summary": summary, "error": None, "cached": False}
    except Exception as e:
        logger.error(f"agent_ai_summary error: {e}")
        return {"summary": "", "error": str(e), "cached": False}
