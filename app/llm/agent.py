import asyncio
from datetime import date
import json

from app.llm.prompts import SYSTEM_PROMPT
from app.llm.tool_specs import openai_tools
from app.schemas.chat import ChatOut, ToolCallTrace
from app.tools.dispatch import run_tool


def _safe_args(raw: str) -> dict:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


async def run_agent(client, session, user_message, model, max_steps) -> ChatOut:
    history = [
        {"role": "system", "content": SYSTEM_PROMPT.format(today=date.today())},
        {"role": "user", "content": user_message},
    ]
    trace = []

    for step in range(1, max_steps + 1):
        response = await client.responses.create(
            model=model, input=history, tools=openai_tools()
        )
        calls = [item for item in response.output if item.type == "function_call"]

        if not calls:
            return ChatOut(answer=response.output_text, tool_calls=trace, steps=step)

        history.extend(response.output)

        for call in calls:
            result = await asyncio.to_thread(
                run_tool, session, call.name, call.arguments
            )
            trace.append(
                ToolCallTrace(
                    name=call.name, arguments=_safe_args(call.arguments), result=result
                )
            )
            history.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result),
                }
            )

    return ChatOut(
        answer="Sorry, I couldn't finish that request.",
        tool_calls=trace,
        steps=max_steps,
    )
