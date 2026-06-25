from utils.ai_client import ask
from utils.logger import logger

SYSTEM = (
    "Ты — профессиональный налоговый аналитик, специалист по предпроверочному анализу ФНС, "
    "налоговым рискам, корпоративной безопасности и проверке контрагентов.\n\n"
    "Отвечай кратко, только по данным ниже. Ссылайся на цифры (выручка, налоги, долги, "
    "судебные дела). Если данных для ответа нет — так и скажи, не выдумывай."
)


def _build_prompt(report_data: dict, question: str) -> tuple[str, str]:
    from agents.agent_ai_summary import _build_prompt as build_data_str

    data_str = build_data_str(report_data)
    user = f"Данные компании:\n{data_str}\n\nВопрос пользователя: {question}"
    return SYSTEM, user


async def fetch(report_data: dict, question: str) -> dict:
    try:
        if not question or not question.strip():
            return {"answer": "", "error": "Пустой вопрос"}

        system, user = _build_prompt(report_data, question)
        answer = await ask(system, user, max_tokens=1024)
        logger.info(f"AI-QA: '{question[:50]}...' -> {len(answer)} символов")
        return {"answer": answer, "error": None}
    except Exception as e:
        logger.error(f"agent_ai_qa error: {e}")
        return {"answer": "", "error": str(e)}
