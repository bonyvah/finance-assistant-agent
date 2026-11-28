import json
import logging

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.tools.tools import TOOLS


def run_tool(session: Session, name: str, raw_args: str) -> dict:
    tool = TOOLS.get(name)
    if not tool:
        return {"error": f"unknown tool {name}"}
    try:
        args = tool.args_model.model_validate_json(raw_args)
    except ValidationError as e:
        return {
            "error": "invalid arguments",
            "details": json.loads(e.json(include_url=False)),
        }
    try:
        return tool.fn(session, args)
    except Exception as e:
        logging.exception("tool %s failed", name)
        return {"error": "tool failed"}
    
