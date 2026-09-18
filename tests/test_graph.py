"""
Testes para agents/graph.py.

O LLM é mockado (nada de Ollama) e `execute` é mockado (nada de subprocess),
então a suíte não depende nem do modelo local nem do sistema operacional.
O que se valida aqui é o contrato do state entre os nós: o fan-out de várias
tools por iteração, o loop do decide_next, o limite de iterações e o que
acontece quando a validação de segurança bloqueia alguma tool.
"""
from unittest.mock import MagicMock

import pytest

from agents.graph import AgentGraph, NextDecision


class FakeToolMessage:
    """Simulates the LLM's response when it decides to call one or more tools"""
    content = ""

    def __init__(self, calls):
        self.tool_calls = [
            {"name": name, "args": args or {}, "id": f"call_{i}"}
            for i, (name, args) in enumerate(calls)
        ]


class FakeNoToolMessage:
    """Simulates the LLM's response when it does NOT choose any tool"""
    content = ""
    tool_calls = []


class FakePlainMessage:
    """Simulates a free-text response (analysis or final answer)"""
    def __init__(self, text):
        self.content = text


def make_fake_llm(calls=(("memoria_livre", None),), needs_more_sequence=(False,)):
    """Mock LLM. `calls` é a lista de (tool, args) devolvida por decide_tool."""
    fake_llm = MagicMock()
    fake_llm.bind_tools.return_value = fake_llm

    def fake_invoke(messages):
        system_text = messages[0].content
        if "Escreva a resposta final" in system_text:
            return FakePlainMessage("Resposta final consolidada fake.")
        if "escolher" in system_text:  # SYSTEM_CHOICE
            return FakeToolMessage(calls)
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


@pytest.fixture(autouse=True)
def no_subprocess(monkeypatch):
    """Nenhum teste deste módulo pode rodar comando de verdade."""
    monkeypatch.setattr(
        "agents.graph.execute",
        lambda command, timeout=None: {
            "success": True, "returncode": 0,
            "stdout": "saida fake", "stderr": "", "error": None,
        },
    )


@pytest.fixture
def build_graph(monkeypatch):
    """Devolve (graph, fake_llm) com o LLM mockado."""

    def _build(calls=(("memoria_livre", None),), needs_more_sequence=(False,), **kwargs):
        fake_llm = make_fake_llm(calls, needs_more_sequence)
        monkeypatch.setattr("agents.graph.get_llm", lambda *a, **k: fake_llm)
        return AgentGraph(**kwargs), fake_llm

    return _build


# ---------- happy path ----------

def test_diagnose_happy_path_one_iteration(build_graph):
    graph, _ = build_graph()
    result = graph.diagnose("tem algo estranho na memória?")

    assert result.error is None
    assert result.iteration == 1
    assert len(result.history) == 1
    assert result.history[0]["tool"] == "memoria_livre"
    assert result.final_answer == "Resposta final consolidada fake."


def test_history_carrega_dados_do_comando_executado(build_graph):
    graph, _ = build_graph()
    result = graph.diagnose("como está a memória?")
    step = result.history[0]

    assert step["comando"] == "free -h"
    assert step["saida"] == "saida fake"
    assert step["alertas"] == []
    # a análise é da rodada inteira, não de cada step
    assert "analise" not in step
    assert result.analyses == ["Análise fake."]


def test_analise_e_uma_chamada_por_rodada_e_nao_por_tool(build_graph):
    """N tools numa rodada = 1 chamada de análise. Com LLM local, uma chamada
    por tool dominava o tempo total da pergunta."""
    graph, fake_llm = build_graph(
        calls=(("top_cpu", None), ("top_memoria", None), ("espaco_disco", None))
    )
    result = graph.diagnose("cpu, memória e disco")

    analises = [
        c for c in fake_llm.invoke.call_args_list
        if "especialista" in c.args[0][0].content
        and "VÁRIOS comandos" in c.args[0][0].content
    ]
    assert len(analises) == 1
    assert len(result.history) == 3
    assert len(result.analyses) == 1


# ---------- fan-out: várias tools numa iteração ----------

def test_fan_out_executa_todas_as_tools_escolhidas(build_graph):
    """O bug original: o grafo usava só tool_calls[0] e descartava o resto."""
    graph, _ = build_graph(
        calls=(("top_cpu", None), ("memoria_livre", None), ("espaco_disco", None))
    )
    result = graph.diagnose("avaliação geral de cpu, memória e disco")

    assert [s["tool"] for s in result.history] == ["top_cpu", "memoria_livre", "espaco_disco"]
    assert result.iteration == 1  # três tools, uma única iteração


def test_fan_out_deduplica_tools_repetidas_na_mesma_rodada(build_graph):
    graph, _ = build_graph(calls=(("top_cpu", None), ("top_cpu", None)))
    result = graph.diagnose("e a cpu?")

    assert [s["tool"] for s in result.history] == ["top_cpu"]


def test_nao_repete_tool_ja_executada_na_iteracao_seguinte(build_graph):
    """Na 2a rodada o LLM devolve a mesma tool; ela já está em `executed`,
    então não há nada novo e o grafo finaliza em vez de gastar iteração."""
    graph, _ = build_graph(
        calls=(("memoria_livre", None),), needs_more_sequence=(True, False)
    )
    result = graph.diagnose("como está o servidor?")

    assert [s["tool"] for s in result.history] == ["memoria_livre"]
    assert result.iteration == 1


# ---------- loop e limite de iterações ----------

def test_loop_quando_decide_next_pede_mais(build_graph, monkeypatch):
    """Cada rodada devolve uma tool inédita, então o loop avança de verdade."""
    sequence = iter([
        [("memoria_livre", None)],
        [("top_cpu", None)],
    ])
    graph, fake_llm = build_graph(needs_more_sequence=(True, False))

    def fake_invoke(messages):
        system_text = messages[0].content
        if "Escreva a resposta final" in system_text:
            return FakePlainMessage("Resposta final consolidada fake.")
        if "escolher" in system_text:
            try:
                return FakeToolMessage(next(sequence))
            except StopIteration:
                return FakeNoToolMessage()
        return FakePlainMessage("Análise fake.")

    fake_llm.invoke.side_effect = fake_invoke

    result = graph.diagnose("como está o servidor?")

    assert result.iteration == 2
    assert [s["tool"] for s in result.history] == ["memoria_livre", "top_cpu"]


def test_respeita_limite_maximo_de_iteracoes(build_graph):
    graph, _ = build_graph(
        needs_more_sequence=(True, True, True, True, True), max_iterations=2
    )
    result = graph.diagnose("como está o servidor?")

    assert result.iteration <= 2
    assert len(result.history) <= 2


# ---------- LLM não escolhe tool ----------

def test_llm_nao_escolhe_nenhuma_tool(build_graph):
    graph, fake_llm = build_graph()
    fake_llm.invoke.side_effect = lambda messages: (
        FakePlainMessage("Resposta final consolidada fake.")
        if "Escreva a resposta final" in messages[0].content
        else FakeNoToolMessage()
    )

    result = graph.diagnose("pergunta sem sentido nenhum")

    assert result.history == []
    assert "reformular" in result.final_answer.lower()


# ---------- validação de segurança ----------

def test_tool_fora_da_whitelist_reporta_erro(build_graph):
    graph, _ = build_graph(calls=(("comando_que_nao_existe", None),))
    result = graph.diagnose("faz algo estranho")

    assert result.history == []
    assert "Não consegui investigar" in result.final_answer
    assert "fora da whitelist" in result.error


def test_parametro_perigoso_e_bloqueado(build_graph):
    graph, _ = build_graph(calls=(("ping", {"host": "8.8.8.8; rm -rf /"}),))
    result = graph.diagnose("faz ping em 8.8.8.8; rm -rf /")

    assert result.history == []
    assert "Não consegui investigar" in result.final_answer
    assert "caracteres não permitidos" in result.error


def test_tool_bloqueada_nao_aborta_as_demais_do_fan_out(build_graph):
    """Uma tool bloqueada não pode matar as outras da mesma rodada -- e o
    bloqueio precisa aparecer no resultado, não sumir em silêncio."""
    graph, _ = build_graph(
        calls=(("ping", {"host": "8.8.8.8; rm -rf /"}), ("memoria_livre", None))
    )
    result = graph.diagnose("ping e memória")

    assert [s["tool"] for s in result.history] == ["memoria_livre"]
    assert "caracteres não permitidos" in result.error
    assert "não foi possível executar" in result.final_answer


def test_parametro_valido_executa_normalmente(build_graph):
    graph, _ = build_graph(calls=(("ping", {"host": "8.8.8.8"}),))
    result = graph.diagnose("faz ping em 8.8.8.8")

    assert result.error is None
    assert len(result.history) == 1
    assert "8.8.8.8" in result.history[0]["comando"]


# ---------- resiliência ao ResponseError do Ollama ----------

def test_decide_tool_faz_retry_quando_o_llm_falha(build_graph):
    """O Ollama aborta o stream quando o modelo emite tool call malformada.
    É intermitente, então a tentativa seguinte costuma funcionar."""
    graph, fake_llm = build_graph()
    chamadas = {"n": 0}

    def fake_invoke(messages):
        system_text = messages[0].content
        if "Escreva a resposta final" in system_text:
            return FakePlainMessage("Resposta final consolidada fake.")
        if "escolher" in system_text:
            chamadas["n"] += 1
            if chamadas["n"] == 1:
                raise RuntimeError("invalid character 'T' looking for beginning of value")
            return FakeToolMessage([("memoria_livre", None)])
        return FakePlainMessage("Análise fake.")

    fake_llm.invoke.side_effect = fake_invoke

    result = graph.diagnose("como está a memória?")

    assert chamadas["n"] == 2  # falhou uma vez, teve sucesso na segunda
    assert [s["tool"] for s in result.history] == ["memoria_livre"]


def test_falha_persistente_do_llm_nao_derruba_o_grafo(build_graph):
    graph, fake_llm = build_graph()

    def fake_invoke(messages):
        if "Escreva a resposta final" in messages[0].content:
            return FakePlainMessage("Resposta final consolidada fake.")
        raise RuntimeError("invalid character 'T' looking for beginning of value")

    fake_llm.invoke.side_effect = fake_invoke

    result = graph.diagnose("como está a memória?")

    assert result.history == []
    assert "não respondeu" in result.error
    assert "Não consegui investigar" in result.final_answer


def test_falha_no_analyze_nao_perde_os_comandos_executados(build_graph):
    """Os comandos já rodaram; perder o history por causa da análise seria
    jogar fora trabalho já feito."""
    graph, fake_llm = build_graph()

    def fake_invoke(messages):
        system_text = messages[0].content
        if "Escreva a resposta final" in system_text:
            return FakePlainMessage("Resposta final consolidada fake.")
        if "escolher" in system_text:
            return FakeToolMessage([("memoria_livre", None)])
        raise RuntimeError("ollama caiu no meio da análise")

    fake_llm.invoke.side_effect = fake_invoke

    result = graph.diagnose("como está a memória?")

    assert [s["tool"] for s in result.history] == ["memoria_livre"]
    assert result.analyses == []
    assert "analisar as saídas" in result.error


def test_falha_no_finalize_entrega_o_que_foi_apurado(build_graph):
    """Falhar na consolidação é o pior momento para quebrar: tudo já rodou."""
    graph, fake_llm = build_graph()

    def fake_invoke(messages):
        system_text = messages[0].content
        if "Escreva a resposta final" in system_text:
            raise RuntimeError("ollama caiu no finalize")
        if "escolher" in system_text:
            return FakeToolMessage([("memoria_livre", None)])
        return FakePlainMessage("Análise fake.")

    fake_llm.invoke.side_effect = fake_invoke

    result = graph.diagnose("como está a memória?")

    assert "$ free -h" in result.final_answer
    assert "Análise fake." in result.final_answer
    assert len(result.history) == 1


# ---------- execução concorrente do fan-out ----------

def test_comandos_do_fan_out_rodam_em_paralelo(build_graph, monkeypatch):
    """Em série um comando lento (du num filesystem grande) bloqueia os
    rápidos atrás dele. O tempo total tem de ser ~o do mais lento, não a soma."""
    import time

    def execute_lento(command, timeout=None):
        time.sleep(0.3)
        return {"success": True, "returncode": 0,
                "stdout": f"saida de {command}", "stderr": "", "error": None}

    monkeypatch.setattr("agents.graph.execute", execute_lento)

    graph, _ = build_graph(
        calls=(("top_cpu", None), ("top_memoria", None),
               ("espaco_disco", None), ("memoria_livre", None))
    )

    inicio = time.monotonic()
    result = graph.diagnose("panorama do servidor")
    decorrido = time.monotonic() - inicio

    assert len(result.history) == 4
    # em série seriam >= 1.2s; em paralelo fica perto de 0.3s
    assert decorrido < 0.9, f"parece serial: {decorrido:.2f}s para 4 comandos de 0.3s"


def test_paralelismo_preserva_a_ordem_das_tools(build_graph, monkeypatch):
    """O history e o prompt final dependem da ordem em que o LLM escolheu."""
    import time

    tempos = {"df -h": 0.3, "free -h": 0.01}

    def execute_variavel(command, timeout=None):
        time.sleep(tempos.get(command, 0.05))
        return {"success": True, "returncode": 0,
                "stdout": "ok", "stderr": "", "error": None}

    monkeypatch.setattr("agents.graph.execute", execute_variavel)

    graph, _ = build_graph(
        calls=(("espaco_disco", None), ("memoria_livre", None), ("uptime", None))
    )
    result = graph.diagnose("panorama")

    # espaco_disco é o mais lento e mesmo assim continua em primeiro
    assert [s["tool"] for s in result.history] == ["espaco_disco", "memoria_livre", "uptime"]


def test_respeita_o_limite_de_threads(build_graph, monkeypatch):
    import threading

    simultaneos = {"agora": 0, "pico": 0}
    lock = threading.Lock()

    def execute_contando(command, timeout=None):
        import time
        with lock:
            simultaneos["agora"] += 1
            simultaneos["pico"] = max(simultaneos["pico"], simultaneos["agora"])
        time.sleep(0.1)
        with lock:
            simultaneos["agora"] -= 1
        return {"success": True, "returncode": 0, "stdout": "ok", "stderr": "", "error": None}

    monkeypatch.setattr("agents.graph.execute", execute_contando)

    graph, _ = build_graph(
        calls=(("top_cpu", None), ("top_memoria", None), ("espaco_disco", None),
               ("memoria_livre", None), ("uptime", None), ("uname", None)),
        max_parallel=2,
    )
    graph.diagnose("panorama")

    assert simultaneos["pico"] <= 2, f"pico de {simultaneos['pico']} threads com max_parallel=2"


def test_comando_unico_nao_abre_thread_pool(build_graph, monkeypatch):
    """Caminho direto para uma tool só -- sem custo de pool."""
    chamadas = []
    monkeypatch.setattr(
        "agents.graph.execute",
        lambda command, timeout=None: (
            chamadas.append(command),
            {"success": True, "returncode": 0, "stdout": "ok", "stderr": "", "error": None},
        )[1],
    )

    graph, _ = build_graph(calls=(("memoria_livre", None),))
    result = graph.diagnose("e a memória?")

    assert chamadas == ["free -h"]
    assert len(result.history) == 1
