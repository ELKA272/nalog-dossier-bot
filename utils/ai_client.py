from openai import OpenAI
from config import OPENROUTER_API_KEY

CLIENT = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)
DEFAULT_MODEL = "qwen/qwen-2.5-72b-instruct"
FALLBACK_MODEL = "deepseek/deepseek-chat-v3-0324"


async def ask(
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1024,
    temperature: float = 0.2,
) -> str:
    if not OPENROUTER_API_KEY:
        return "❌ OPENROUTER_API_KEY не задан в .env"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    for attempt, mdl in enumerate([model, FALLBACK_MODEL]):
        try:
            resp = CLIENT.chat.completions.create(
                model=mdl,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                seed=42,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            if attempt == 0:
                continue
            return f"❌ Ошибка AI: {e}"
    return "❌ Не удалось получить ответ от AI"
