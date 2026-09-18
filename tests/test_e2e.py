import pytest
import requests
from agents.graph import AgentGraph
from config import OLLAMA_MODEL, OLLAMA_BASE_URL, ALLOWED_COMMANDS


def _reason_to_skip() -> str | None:
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
    except requests.RequestException as e:
        return f"Ollama inacessível em {OLLAMA_BASE_URL}: {e}"

    if resp.status_code != 200:
        return f"Ollama respondeu {resp.status_code} em {OLLAMA_BASE_URL}"

    installed = {m["name"] for m in resp.json().get("models", [])}
    if OLLAMA_MODEL not in installed:
        return f"Modelo {OLLAMA_MODEL} não está instalado (ollama pull {OLLAMA_MODEL})"

    return None


@pytest.fixture
def agent_confirm_all():
    reason = _reason_to_skip()
    if reason:
        pytest.skip(reason)
    return AgentGraph(confirm_callback=lambda payload: "s")


@pytest.fixture
def agent_reject_all():
    reason = _reason_to_skip()
    if reason:
        pytest.skip(reason)
    return AgentGraph(confirm_callback=lambda payload: "n")


def test_confirm_approve_tool(agent_confirm_all):
    received_payload = []
    agent_confirm_all.confirm_callback = lambda payload: (
            received_payload.append(payload) or "s"
    )

    result = agent_confirm_all.diagnose("verifique se o ip 8.8.8.8 está respondendo")

    executed_tool_approved = [
        s["tool"] for s in result.history
        if ALLOWED_COMMANDS[s["tool"]]["seguranca"] == "alta"
    ]

    if executed_tool_approved:
        assert received_payload, (
            "rodou tool 'alta' sem nunca chamar o confirm_callback"
        )

        questioned_tool_names = {c["name"] for p in received_payload for c in p}
        assert set(executed_tool_approved) <= questioned_tool_names

    assert result.error is None
    assert result.final_answer.strip()

