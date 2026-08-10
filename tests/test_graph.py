
from unittest.mock import MagicMock
from agents.graph import AgentGraph, NextDecision


class FakeToolMessage:
    """Simulates the LLM's response when it decides to call a tool"""
    content = ""

    def __init__(self, name, args=None):
        self.tool_calls = [{"name": name, "args": args or {}, "id": "call_1"}]


class FakeNoToolMessage:
    """Simulates the LLM's response when it does NOT choose any tool"""
    content = ""
    tool_calls = []


class FakePlainMessage:
    """Simulates a free-text response (analysis or final answer)"""
    def __init__(self, text):
        self.content = text


def make_fake_llm(tool_name="memoria_livre", tool_args=None, needs_more_sequence=(False,)):
    """Mock LLM"""
    fake_llm = MagicMock()
    fake_llm.bind_tools.return_value = fake_llm

    def fake_invoke(messages):
        system_text = messages[0].content
        if "Decida" in system_text or "resposta final" in system_text.lower() or "Escreva a resposta final" in system_text:
            if "resposta final" in system_text.lower() or "Escreva a resposta final" in system_text:
                return FakePlainMessage("Resposta final consolidada fake.")
            return FakePlainMessage("Análise fake.")
        if "agente de diagnóstico" in system_text:
            return FakeToolMessage(tool_name, tool_args)
        return FakePlainMessage("Análise fake.")

    fake_llm.invoke.side_effect = fake_invoke

    sequence = iter(needs_more_sequence)

    class FakeStructured:
        def invoke(self, message):
            try:
                needs_more = next(sequence)
            except StopIteration:
                needs_more = False
            return NextDecision(needs_more=needs_more, reason="teste")

    fake_llm.with_structured_output.return_value = FakeStructured()
    return fake_llm


# ---------- happy path: an iteration ----------
def test_diagnose_happy_path_one_iteration(monkeypatch):
    fake_llm = make_fake_llm(tool_name="memoria_livre", needs_more_sequence=(False,))
    monkeypatch.setattr("agents.graph.get_llm", lambda: fake_llm)

    graph = AgentGraph()
    result = graph.diagnose("tem algo estranho na memória?")

    assert result.error is None
    assert result.iteration == 1
    assert len(result.history) == 1
    assert result.history[0]["tool"] == "memoria_livre"
    assert result.final_answer == "Resposta final consolidada fake."


def test_diagnose_history_acumula_dados_do_comando_executado(monkeypatch):
    fake_llm = make_fake_llm(tool_name="memoria_livre", needs_more_sequence=(False,))
    monkeypatch.setattr("agents.graph.get_llm", lambda: fake_llm)

    graph = AgentGraph()
    result = graph.diagnose("como está a memória?")

    step = result.history[0]
    assert step["comando"] == "free -h"
    assert "analise" in step
    assert "alertas" in step


# ---------- loop: decide next—ask for another round ----------
def test_diagnose_loop_when_deciding_next_requests_more(monkeypatch):
    fake_llm = make_fake_llm(tool_name="memoria_livre", needs_more_sequence=(True, False))
    monkeypatch.setattr("agents.graph.get_llm", lambda: fake_llm)

    graph = AgentGraph(max_iterations=3)
    result = graph.diagnose("como está o servidor?")

    assert result.iteration == 2
    assert len(result.history) == 2


def test_diagnose_respects_maximum_iteration_limit(monkeypatch):
    fake_llm = make_fake_llm(tool_name="memoria_livre", needs_more_sequence=(True, True, True, True, True))
    monkeypatch.setattr("agents.graph.get_llm", lambda: fake_llm)

    graph = AgentGraph(max_iterations=2)
    result = graph.diagnose("como está o servidor?")

    assert result.iteration <= 2
    assert len(result.history) <= 2


# ---------- The LLM does not select any tool ----------
def test_diagnose_llm_does_not_choose_tool(monkeypatch):
    fake_llm = MagicMock()
    fake_llm.bind_tools.return_value = fake_llm
    fake_llm.invoke.return_value = FakeNoToolMessage()
    monkeypatch.setattr("agents.graph.get_llm", lambda: fake_llm)

    graph = AgentGraph()
    result = graph.diagnose("pergunta sem sentido nenhum")

    assert result.history == []
    assert "reformular" in result.final_answer.lower()


# ---------- Tool not on the whitelist ----------
def test_diagnose_tool_fora_da_whitelist(monkeypatch):
    fake_llm = make_fake_llm(tool_name="comando_que_nao_existe")
    monkeypatch.setattr("agents.graph.get_llm", lambda: fake_llm)

    graph = AgentGraph()
    result = graph.diagnose("faz algo estranho")

    assert result.history == []
    assert "Não consegui investigar" in result.final_answer


# ---------- parameter blocked by security validation ----------
def test_diagnose_dangerous_and_blocked_parameter(monkeypatch):
    fake_llm = make_fake_llm(tool_name="ping", tool_args={"host": "8.8.8.8; rm -rf /"})
    monkeypatch.setattr("agents.graph.get_llm", lambda: fake_llm)

    graph = AgentGraph()
    result = graph.diagnose("faz ping em 8.8.8.8; rm -rf /")

    assert result.history == []
    assert "Não consegui investigar" in result.final_answer


def test_diagnose_with_valid_parameter_executes_normally(monkeypatch):
    fake_llm = make_fake_llm(tool_name="ping", tool_args={"host": "8.8.8.8"}, needs_more_sequence=(False,))
    monkeypatch.setattr("agents.graph.get_llm", lambda: fake_llm)

    graph = AgentGraph()
    result = graph.diagnose("faz ping em 8.8.8.8")

    assert result.error is None
    assert len(result.history) == 1
    assert "8.8.8.8" in result.history[0]["comando"]