# Налоговое досье — AGENTS.md

## Entrypoints

- **Web UI** → `streamlit run app.py --server.port 8503` (port 8503) или `8504` для dev
- **Telegram bot** → `python3 main.py` (uses `bot.py:handle_message` → `orchestrator.orchestrator.run()`)
- Both share the same pipeline; no separate dev/prod mode.

## Restart after code changes

```bash
kill -9 $(lsof -ti :8503) 2>/dev/null; sleep 1
cd /Users/k/Desktop/Налоговое\ досье/agent
nohup python3 -m streamlit run app.py --server.port 8503 > /tmp/streamlit.log 2>&1 &
kill $(ps aux | grep 'python3 -u main.py' | grep -v grep | awk '{print $2}') 2>/dev/null
nohup python3 -u main.py > /tmp/bot_clean.log 2>&1 &
```

Logs: `/tmp/streamlit.log`, `/tmp/bot_clean.log`, `/tmp/ngrok.log`, `/tmp/streamlit_8504.log`

## Pipeline (orchestrator.run(inn))

1. **Single phase**: `agent_irbis.fetch(inn)` — один вызов ir-bis.org API
   - Создаёт проверку `/new/org-check.json?inn=...&token=...`
   - Ждёт готовности `org-egrul.json?event=result&version=4` (polling до 90с)
   - Параллельно фетчит **94 (ЮЛ) / 108 (ФЛ) JSON-эндпоинтов** через `asyncio.gather`
2. **Risk calc**: 7 модулей (tax, financial, corporate, reputation, splitting, technical → scorer)
3. **DOCX**: `report.report_builder.build(display_name, inn, report_data) -> str`

Returns dict with keys: `summary`, `report_path`, `scoring`, `splitting`, `technical`, `display_name`, `_report_data`

## Component contracts

| Component | Contract |
|---|---|
| `agents/agent_irbis.py` | `async def fetch(inn: str) -> dict` — единый агент ir-bis |
| `utils/irbis_client.py` | HTTP-клиент: `create_check()`, `wait_ready()`, `get()` |
| `risk_engine/risk_xxx.py` | `calculate(data) -> {"score": int, "level": str, "findings": list}` |
| `report/report_builder.py` | `build(name, inn, report_data) -> str` (file path) |
| `orchestrator/` | `run(inn) -> dict` (см. выше) |

Чтобы добавить новый эндпоинт: добавить 4-кортеж в `_org_endpoints()` или `_people_endpoints()` + `_irbis_*` ключ в `_transform_ul()` или `_transform_ip()`.

## Secrets

Только 3 vars в `.env` (gitignored), single source of truth via `config.py`:
- `TELEGRAM_BOT_TOKEN` — используется `bot.py`
- `OPENROUTER_API_KEY` — используется `utils/ai_client.py`
- `IRBIS_API_TOKEN` — токен ir-bis.org (`e4c43ba9-d5d9-4462-8ab8-d9eafee7c08c`)

## API endpoints coverage

| Метрика | Значение |
|---|---|
| Swagger paths (всего) | **216** |
| Swagger tags (категории) | **51** |
| JSON эндпоинтов (без /new/) | **209** |
| В agent_irbis.py | **202** (96.7%) |
| Пропущено (PDF) | 5 |
| Пропущено (JSON, нужен кадастр) | 2 |
| **Покрытие JSON по ИНН** | **202/204 = 99%** |

**Для ЮЛ (10 цифр):** 94 эндпоинта, 29 JSON-файлов, 44 категории
**Для ФЛ (12 цифр):** 108 эндпоинтов, 42 JSON-файла, 46 категорий

## Секции web UI (app.py)

50 секций в меню, включая:
- Основные: резюме, общая информация, руководители, связи, финансы
- Суды и долги: арбитраж, СОЮ, ФССП, банкротства, намерения о банкротстве
- Налоги/ФНС: налоговые долги, приостановления по счетам, МСП
- Имущество: залоги, товарные знаки, лизинг, недвижимость
- Регуляторы: проверки КНМ, лицензии, Роструд, РАФП, документы госрегистрации
- Реестры: санкции, иноагенты, террористы, дисквалифицированные, коррупционеры, ЦБ РФ, обеспечительные меры, субсидиарная, наследство, самозанятые, болельщики
- Розыск: МВД, ФСИН, контролируемые лица, паспорт, водительское удостоверение, ML-индекс, популярность
- Инфраструктура: контакты, раскрытие, ФСГС, адрес (ОКАТО), история ЕГРЮЛ

## Toolchain quirks

- **ir-bis API**: базовый URL `https://ir-bis.org`, токен в query-параметре `token=` (строчные). Swagger: `https://apidocs.ir-bis.org/get-swagger-api-doc` (Basic Auth apidocs/rD8q9Gaa1NvRvYcS). 202/209 endpoints coverage (96.7%), пропущены PDF/кадастр.
- **Никакого Playwright / parser-api.com** — всё через `irbis_client.py` (httpx, verify=True)
- **Watchdog**: `bot.py` catches `Conflict` (duplicate instance) and retries with backoff up to 60s
- **Agent model**: `qwen/qwen-2.5-72b-instruct` via OpenRouter (fallback: `deepseek/deepseek-chat-v3-0324`). Both paid but ~$0.00002/req.
- **AI on-demand**: button in web UI / inline button in Telegram → `agent_ai_summary.fetch(report_data)`
- **requirements.txt is incomplete**: streamlit, pandas установлены глобально
- **Pipeline**: ~12-13 секунд на ИНН (94/108 endpoint параллельно)
- **Данные с `event=data` (page/rows) стабильно возвращают `status=-1`**: preview-эндпоинты работают мгновенно, data-эндпоинты требуют длительной генерации на сервере или не работают совсем.
  - Агрегированные данные (количество дел, суммы долгов, итоги) доступны из EGRUL preview и специализированных preview-эндпоинтов
  - Индивидуальные записи (конкретные дела, исполнительные производства) недоступны — `_extract_result()` возвращает `[]` при `status=-1`
  - В `_transform_fssp` и `_transform_arbitr` используется fallback: корректные счётчики + пустой список деталей
  - **Не тратить время на long-polling data-эндпоинтов**: 5-секундный retry — максимум; все известные data-эндпоинты не становятся ready в течение хотя бы 90 секунд

## Ports / services

| Service | Port | Command |
|---|---|---|
| Streamlit (prod) | 8503 | `lsof -ti :8503` |
| Streamlit (dev) | 8504 | `lsof -ti :8504` |
| ngrok admin | 4040 | `ps aux \| grep ngrok` |
| Telegram bot | none (polling) | `ps aux \| grep main.py` |
