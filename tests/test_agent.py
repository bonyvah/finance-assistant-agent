import asyncio
import json
from types import SimpleNamespace
import httpx2, openai
import pytest

from app.llm.agent import run_agent
from app.main import app
from app.routers.chat import get_openai_client


class FakeResponses:
    """Stands in for client.responses: returns scripted responses, logs every call."""

    def __init__(self, scripted):
        self._scripted = list(scripted)
        self.calls = []

    async def create(self, **kwargs):
        # Snapshot input: the agent keeps appending to the same list after this call.
        self.calls.append({**kwargs, "input": list(kwargs["input"])})
        return self._scripted.pop(0)


class RaisingResponses:
    async def create(self, **kwargs):
        raise openai.APIConnectionError(request=httpx2.Request("POST", "http://x"))


class FakeClient:
    def __init__(self, scripted):
        self.responses = FakeResponses(scripted)


def fn_call(name, args, call_id):
    return SimpleNamespace(
        type="function_call", name=name, arguments=json.dumps(args), call_id=call_id
    )


def final(text):
    message = SimpleNamespace(type="message", content=text)
    return SimpleNamespace(output=[message], output_text=text)


def calls(*fn_calls):
    return SimpleNamespace(output=list(fn_calls), output_text="")


def outputs(sent_input):
    """function_call_output items, keyed by call_id."""
    return {
        item["call_id"]: json.loads(item["output"])
        for item in sent_input
        if isinstance(item, dict) and item.get("type") == "function_call_output"
    }


def run(client, session, message="hi", max_steps=5):
    return asyncio.run(run_agent(client, session, message, "test-model", max_steps))


def test_direct_answer(db_session):
    client = FakeClient([final("Hello!")])

    out = run(client, db_session)

    assert out.answer == "Hello!"
    assert out.tool_calls == []
    assert out.steps == 1
    assert len(client.responses.calls) == 1


def test_one_tool_then_answer(db_session, sample_invoices):
    call = fn_call("get_invoice", {"invoice_id": 1}, "c1")
    client = FakeClient([calls(call), final("Invoice 1 is AWS, 100.00 USD.")])

    out = run(client, db_session, "show invoice 1")

    assert out.steps == 2
    assert out.answer == "Invoice 1 is AWS, 100.00 USD."
    assert [t.name for t in out.tool_calls] == ["get_invoice"]
    assert out.tool_calls[0].arguments == {"invoice_id": 1}

    second_input = client.responses.calls[1]["input"]
    # The model's function_call item must be echoed back before its output.
    assert call in second_input
    sent = outputs(second_input)
    assert set(sent) == {"c1"}
    assert sent["c1"]["found"] is True
    assert sent["c1"]["invoice"]["vendor"] == "AWS"


def test_chat_endpoint_502(client):
    app.dependency_overrides[get_openai_client] = lambda: SimpleNamespace(
        responses=RaisingResponses()
    )
    try:
        resp = client.post("/chat", json={"message": "hi"})
    finally:
        app.dependency_overrides.pop(get_openai_client, None)
    assert resp.status_code == 502


def test_two_tools_one_turn(db_session, sample_invoices):
    client = FakeClient(
        [
            calls(
                fn_call("get_invoice", {"invoice_id": 1}, "c1"),
                fn_call("search_invoices", {"status": "overdue"}, "c2"),
            ),
            final("done"),
        ]
    )

    out = run(client, db_session)

    assert out.steps == 2
    assert [t.name for t in out.tool_calls] == ["get_invoice", "search_invoices"]
    sent = outputs(client.responses.calls[1]["input"])
    assert set(sent) == {"c1", "c2"}
    assert sent["c1"]["invoice"]["id"] == 1
    assert sent["c2"]["count"] == 1
    assert sent["c2"]["invoices"][0]["vendor"] == "Figma"


def test_broken_json_args(db_session):
    bad = SimpleNamespace(
        type="function_call", name="get_invoice", arguments='{"bad', call_id="c1"
    )
    client = FakeClient([calls(bad), final("ok")])
    out = run(client, db_session)
    assert out.steps == 2
    assert out.tool_calls[0].arguments == {}
    assert "error" in outputs(client.responses.calls[1]["input"])["c1"]


def test_bad_args_returns_error_and_loop_continues(db_session):
    client = FakeClient(
        [
            calls(fn_call("get_invoice", {"invoice_id": 0}, "c1")),
            final("Invoice IDs start at 1."),
        ]
    )

    out = run(client, db_session)

    assert out.steps == 2
    assert out.answer == "Invoice IDs start at 1."
    assert out.tool_calls[0].result["error"] == "invalid arguments"
    assert "error" in outputs(client.responses.calls[1]["input"])["c1"]


def test_step_limit_returns_fallback(db_session, sample_invoices):
    max_steps = 3
    client = FakeClient(
        [
            calls(fn_call("get_invoice", {"invoice_id": 1}, f"c{i}"))
            for i in range(max_steps)
        ]
    )

    out = run(client, db_session, max_steps=max_steps)

    assert out.steps == max_steps
    assert out.answer == "Sorry, I couldn't finish that request."
    assert len(out.tool_calls) == max_steps
    assert len(client.responses.calls) == max_steps


@pytest.fixture
def fake_openai():
    fake = FakeClient([final("You have 1 overdue invoice.")])
    app.dependency_overrides[get_openai_client] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_openai_client, None)


def test_chat_endpoint(client, fake_openai):
    resp = client.post("/chat", json={"message": "what's overdue?"})

    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "answer": "You have 1 overdue invoice.",
        "tool_calls": [],
        "steps": 1,
    }
    assert fake_openai.responses.calls[0]["input"][-1] == {
        "role": "user",
        "content": "what's overdue?",
    }


def test_chat_endpoint_rejects_empty_message(client, fake_openai):
    resp = client.post("/chat", json={"message": ""})

    assert resp.status_code == 422
    assert fake_openai.responses.calls == []
