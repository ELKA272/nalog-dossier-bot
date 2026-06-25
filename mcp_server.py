#!/usr/bin/env python3
"""
MCP (Model Context Protocol) server for Налоговое досье.
JSON-RPC 2.0 over stdin/stdout. No external SDK required.
"""
import asyncio
import json
import sys
import traceback

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from orchestrator.orchestrator import run as run_orchestrator
from agents.agent_ai_summary import fetch as ai_summary_fetch
from agents.agent_ai_qa import fetch as ai_qa_fetch

TOOLS = [
    {
        "name": "analyze_company",
        "description": "Полное досье компании по ИНН (ЕГРЮЛ, ФНС, ФССП, суды, СМИ, риски, скоринг)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "inn": {
                    "type": "string",
                    "description": "ИНН организации (10 цифр — ЮЛ, 12 цифр — ИП)",
                }
            },
            "required": ["inn"],
        },
    },
    {
        "name": "ai_summary",
        "description": "AI-резюме компании по ИНН (3-5 предложений, простым языком)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "inn": {"type": "string", "description": "ИНН организации"},
                "mode": {
                    "type": "string",
                    "enum": ["brief", "detailed", "compare"],
                    "description": "Режим: brief — кратко, detailed — детально, compare — сравнение",
                },
            },
            "required": ["inn"],
        },
    },
    {
        "name": "ask_question",
        "description": "Задать вопрос о компании по ИНН (например: 'есть ли налоговые долги?')",
        "inputSchema": {
            "type": "object",
            "properties": {
                "inn": {"type": "string", "description": "ИНН организации"},
                "question": {"type": "string", "description": "Вопрос на русском языке"},
            },
            "required": ["inn", "question"],
        },
    },
]


async def handle_request(request: dict) -> dict:
    method = request.get("method")
    params = request.get("params", {})
    req_id = request.get("id")

    base = {"jsonrpc": "2.0", "id": req_id}

    if method == "initialize":
        return {
            **base,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "nalogovoe-dossier", "version": "1.0.0"},
            },
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return {**base, "result": {"tools": TOOLS}}

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        inn = arguments.get("inn", "")

        if not inn or not inn.strip():
            return {**base, "error": {"code": -32000, "message": "ИНН обязателен"}}

        try:
            if tool_name == "analyze_company":
                result = await run_orchestrator(inn)
                report_data = result.get("_report_data", {})
                return {**base, "result": {"content": [{"type": "text", "text": json.dumps(report_data, ensure_ascii=False, default=str, indent=2)}]}}

            elif tool_name == "ai_summary":
                mode = arguments.get("mode", "brief")
                result = await run_orchestrator(inn)
                report_data = result.get("_report_data", {})
                if not report_data:
                    return {**base, "error": {"code": -32000, "message": "Не удалось собрать данные"}}
                ai_result = await ai_summary_fetch(report_data, mode=mode)
                text = ai_result.get("summary", "Ошибка генерации")
                return {**base, "result": {"content": [{"type": "text", "text": text}]}}

            elif tool_name == "ask_question":
                question = arguments.get("question", "")
                if not question:
                    return {**base, "error": {"code": -32000, "message": "Вопрос обязателен"}}
                result = await run_orchestrator(inn)
                report_data = result.get("_report_data", {})
                if not report_data:
                    return {**base, "error": {"code": -32000, "message": "Не удалось собрать данные"}}
                qa_result = await ai_qa_fetch(report_data, question)
                text = qa_result.get("answer", "Ошибка")
                return {**base, "result": {"content": [{"type": "text", "text": text}]}}

            else:
                return {**base, "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"}}

        except Exception as e:
            return {**base, "error": {"code": -32000, "message": str(e), "data": traceback.format_exc()}}

    return {**base, "error": {"code": -32601, "message": f"Method '{method}' not found"}}


async def main():
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    writer_transport, writer_protocol = await loop.connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout.buffer
    )
    writer = asyncio.StreamWriter(writer_transport, writer_protocol, None, loop)

    while True:
        try:
            line = await reader.readline()
        except EOFError:
            break
        if not line:
            break

        line = line.decode("utf-8").strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            continue

        response = await handle_request(request)
        if response is not None:
            data = json.dumps(response, ensure_ascii=False) + "\n"
            writer.write(data.encode("utf-8"))
            await writer.drain()


if __name__ == "__main__":
    asyncio.run(main())
