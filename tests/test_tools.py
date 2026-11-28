import json

import pytest

from app.services import invoices as invoices_service
from app.tools.dispatch import run_tool
from app.tools.tools import TOOLS


def test_get_invoice_found(db_session, sample_invoices):
    out = run_tool(db_session, "get_invoice", '{"invoice_id": 1}')
    assert out["found"] is True
    assert out["invoice"]["vendor"] == "AWS"
    assert out["invoice"]["amount"] == "100.00"  # Decimal -> exact string


def test_get_invoice_not_found_is_data_not_exception(db_session, sample_invoices):
    out = run_tool(db_session, "get_invoice", '{"invoice_id": 999}')
    assert out == {"found": False, "invoice_id": 999}


def test_search_invoices(db_session, sample_invoices):
    out = run_tool(db_session, "search_invoices", '{"status": "overdue"}')
    assert out["count"] == 1
    assert out["invoices"][0]["vendor"] == "Figma"


def test_summarize_spend(db_session, sample_invoices):
    out = run_tool(db_session, "summarize_spend", '{"group_by": "vendor", "status": "paid"}')
    assert out["summary"]["totals"] == {"USD": "2111.99"}


def test_unknown_tool(db_session):
    out = run_tool(db_session, "delete_everything", "{}")
    assert "error" in out


@pytest.mark.parametrize(
    "name, raw",
    [
        ("get_invoice", '{"invoice_id": 0}'),  # ge=1
        ("get_invoice", "{}"),  # missing required
        ("search_invoices", '{"month": "march"}'),  # hallucinated arg -> extra=forbid
        ("summarize_spend", '{"group_by": "planet"}'),  # bad enum
        ("search_invoices", "not json"),  # broken JSON from the model
    ],
)
def test_invalid_args_return_error(db_session, name, raw):
    out = run_tool(db_session, name, raw)
    assert out["error"] == "invalid arguments"
    assert out["details"]


def test_tool_crash_is_caught(db_session, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("db on fire")

    monkeypatch.setattr(invoices_service, "summarize_spend", boom)
    out = run_tool(db_session, "summarize_spend", '{"group_by": "vendor"}')
    assert out == {"error": "tool failed"}  # no internals leaked to the LLM


@pytest.mark.parametrize(
    "name, raw",
    [
        ("get_invoice", '{"invoice_id": 1}'),
        ("search_invoices", "{}"),
        ("summarize_spend", '{"group_by": "category"}'),
    ],
)
def test_every_tool_output_is_json_serializable(db_session, sample_invoices, name, raw):
    json.dumps(run_tool(db_session, name, raw))  # M3 sends this straight back to OpenAI


def test_registry_is_complete():
    for tool in TOOLS.values():
        assert tool.description, f"{tool.name} has no description"
        schema = tool.args_model.model_json_schema()
        assert schema.get("additionalProperties") is False
