import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from config import TELEGRAM_BOT_TOKEN
from utils.logger import logger
from utils.parser import parse_input
from utils.telegram_reporter import build_all_messages
from orchestrator.orchestrator import run as run_orchestrator
from agents import agent_ai_summary, agent_ai_qa


MAX_MSG_LEN = 4000

_ai_cache: dict[int, dict] = {}
_qa_waiting: set[int] = set()


async def _send_long(update, text):
    if len(text) <= MAX_MSG_LEN:
        await update.message.reply_text(text, parse_mode="HTML")
        return

    parts = []
    while text:
        if len(text) <= MAX_MSG_LEN:
            parts.append(text)
            break
        split_at = text.rfind("\n", 0, MAX_MSG_LEN)
        if split_at == -1:
            split_at = MAX_MSG_LEN
        parts.append(text[:split_at])
        text = text[split_at:]

    for part in parts:
        await update.message.reply_text(part, parse_mode="HTML")
        await asyncio.sleep(0.5)


async def start(update, context):
    try:
        logger.info(f"Команда /start от {update.effective_user.username or update.effective_user.id}")
        msg = (
            "👋 <b>Налоговое досье — бот проверки контрагентов</b>\n\n"
            "Просто отправь мне <b>ИНН</b> (10 или 12 цифр) организации — "
            "и я соберу полное досье из открытых источников.\n\n"
            "📋 Что будет в отчёте:\n"
            "• Общая информация (ЕГРЮЛ)\n"
            "• Руководители и учредители\n"
            "• Финансовый анализ\n"
            "• Судебные дела\n"
            "• Исполнительные производства\n"
            "• Налоговые, финансовые, корпоративные, репутационные риски\n"
            "• Дробление бизнеса и признаки технической компании\n"
            "• Вероятные претензии ФНС\n"
            "• Рекомендации\n\n"
            "Пример: <code>7707083893</code>\n\n"
            "Команды:\n"
            "/start — это сообщение\n"
            "/help — справка"
        )
        await update.message.reply_text(msg, parse_mode="HTML")
        logger.info(f"Ответ на /start отправлен")
    except Exception as e:
        logger.exception(f"Ошибка в start: {e}")


async def help_command(update, context):
    await update.message.reply_text(
        "📖 <b>Как пользоваться:</b>\n\n"
        "1. Отправьте ИНН (10 цифр для юрлица, 12 для ИП)\n"
        "2. Подождите 2-5 минут — идёт сбор данных из 10+ источников\n"
        "3. Получите полный отчёт прямо в чат + DOCX-файл\n\n"
        "📊 <b>Оцениваемые риски:</b>\n"
        "• Налоговый (дробление, тех. компании, разрывы НДС)\n"
        "• Финансовый (убытки, долги, активы)\n"
        "• Корпоративный (смены, ликвидация, массовые признаки)\n"
        "• Репутационный (СМИ, суды, взыскания)\n\n"
        "Источники: ЕГРЮЛ, ФНС, ФССП, КАД Арбитраж, Федресурс, СМИ",
        parse_mode="HTML",
    )


async def handle_message(update, context):
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    # Check if user is in Q&A mode
    if chat_id in _qa_waiting:
        _qa_waiting.discard(chat_id)
        report_data = _ai_cache.get(chat_id)
        if not report_data:
            await update.message.reply_text("❌ Данные устарели. Запросите новый анализ.")
            return
        await update.message.reply_text("⏳ Думаю над ответом...")
        qa_result = await agent_ai_qa.fetch(report_data, text)
        answer = qa_result.get("answer", "❌ Ошибка")
        await update.message.reply_text(f"🤖 <b>Ответ:</b>\n\n{answer}", parse_mode="HTML")
        return

    parsed = parse_input(text)

    if parsed["type"] == "unknown":
        await update.message.reply_text(
            "❌ Не могу определить формат.\n"
            "Пришлите ИНН (10 или 12 цифр), ОГРН (13 цифр) или ФИО"
        )
        return

    inn = parsed["value"]
    if parsed["type"] not in ("inn_ul", "inn_ip"):
        await update.message.reply_text("❌ Пока поддерживается только поиск по ИНН")
        return

    await update.message.reply_text(
        f"✅ <b>Запрос принят.</b>\n"
        f"ИНН: <code>{inn}</code>\n"
        f"Выполняю анализ... Это займёт 2-5 минут ⏳",
        parse_mode="HTML",
    )

    try:
        result = await run_orchestrator(inn, company_name=text if parsed["type"] == "name" else "")

        report_data = result.get("_report_data", {})
        if not report_data:
            await _send_long(update, result["summary"])
        else:
            messages = build_all_messages(
                result.get("display_name", inn),
                inn,
                report_data,
            )
            for msg in messages:
                await _send_long(update, msg)
                await asyncio.sleep(0.3)

        report_path = result.get("report_path")
        if report_path and os.path.exists(report_path):
            with open(report_path, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename=os.path.basename(report_path),
                    caption=f"📄 Полный отчёт (DOCX) по {result.get('display_name', inn)}",
                )

        await update.message.reply_text(
            f"✅ <b>Анализ завершён.</b>\n"
            f"Проверено источников: 10+",
            parse_mode="HTML",
        )

        if report_data:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [
                    InlineKeyboardButton("📄 Кратко", callback_data=f"ai|brief|{inn}"),
                    InlineKeyboardButton("📊 Детально", callback_data=f"ai|detailed|{inn}"),
                    InlineKeyboardButton("📈 Сравнение", callback_data=f"ai|compare|{inn}"),
                ]
            ]
            await update.message.reply_text(
                "🧠 <b>AI-анализ контрагента</b>\nВыберите режим:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            _ai_cache[update.effective_chat.id] = report_data
            _qa_waiting.discard(update.effective_chat.id)
    except Exception as e:
        logger.exception("Ошибка в обработке запроса")
        await update.message.reply_text(f"❌ Ошибка при анализе: {e}")


async def ai_callback(update, context):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("ai|"):
        parts = data.split("|", 2)
        if len(parts) < 3:
            return
        _, mode, inn = parts
        chat_id = update.effective_chat.id
        report_data = _ai_cache.get(chat_id)

        if not report_data:
            await query.edit_message_text("❌ Данные устарели. Запросите новый анализ.")
            return

        await query.edit_message_text("⏳ Генерирую AI-резюме...")
        ai_result = await agent_ai_summary.fetch(report_data, mode=mode)
        summary = ai_result.get("summary", "❌ Ошибка генерации")

        mode_labels = {"brief": "📄 Кратко", "detailed": "📊 Детально", "compare": "📈 Сравнение"}
        header = f"🧠 <b>AI-анализ ({mode_labels.get(mode, mode)})</b>"
        qa_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❓ Задать вопрос", callback_data=f"qa|{inn}")]
        ])
        await query.edit_message_text(
            f"{header}\n\n{summary}",
            parse_mode="HTML",
            reply_markup=qa_keyboard,
        )

    elif data.startswith("qa|"):
        _, inn = data.split("|", 1)
        chat_id = update.effective_chat.id
        report_data = _ai_cache.get(chat_id)
        if not report_data:
            await query.edit_message_text("❌ Данные устарели. Запросите новый анализ.")
            return
        _qa_waiting.add(chat_id)
        await query.edit_message_text(
            "✏️ Напишите ваш вопрос о компании одним сообщением."
        )


async def _run_bot():
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
    from telegram.error import Conflict

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(ai_callback, pattern=r"^(ai|qa)\|"))

    await app.initialize()
    await app.updater.start_polling(allowed_updates=["messages", "callback_query"], drop_pending_updates=True)
    logger.info("Бот запущен. Напишите /start в Telegram")

    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        raise
    finally:
        await app.updater.stop()
        await app.shutdown()


async def _watchdog():
    from telegram.error import Conflict

    retries = 0
    while True:
        try:
            await _run_bot()
            break
        except Conflict:
            retries += 1
            wait = min(retries * 5, 60)
            logger.warning(f"Conflict при запуске бота, повтор через {wait}с (попытка {retries})")
            await asyncio.sleep(wait)
        except Exception as e:
            logger.error(f"Бот упал: {e}. Перезапуск через 5 сек...")
            await asyncio.sleep(5)
            retries = 0


def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не задан! Запишите токен в .env")
        return
    asyncio.run(_watchdog())


if __name__ == "__main__":
    main()
