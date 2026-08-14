import operator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Annotated, Any, TypedDict
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from agents.llm import get_llm
from agents.prompts import (
    SYSTEM_ANALYSIS_MULTI,
    SYSTEM_DECIDE_NEXT,
    SYSTEM_CHOICE,
    SYSTEM_FINALIZE,
    mount_human_analysis,
    mount_next_human_choice,
    mount_human_choice,
    mount_end_human_choice
)
from agents.tools import _format_to_llm, build_tools
from config import ALLOWED_COMMANDS
from core import ValidationError, execute, mount_command, summarize_result
from utils import get_logger

logger = get_logger(__name__)

MAX_ITERATIONS = 3
MAX_LLM_RETRIES = 3
MAX_PARALLEL_COMMANDS = 4


class NextDecision(BaseModel):
    """Structured output node decide_next"""
    needs_more: bool = Field(description="Se é preciso rodar mais um comando.")
    reason: str = Field(description="Justificativa curta da decisão.")


class AgentState(TypedDict, total=False):
    """Shared state between graph nodes"""
    question: str
    iteration: int
    # history (accumulates across iterations)
    history: Annotated[list[dict], operator.add]
    executed: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]
    analyses: Annotated[list[str], operator.add]   # one per iteration, not per tool
    # fan-out of the current iteration (overwritten each round)
    tools_pending: list[dict]
    checked: list[dict]
    summary: list[dict]
    # control
    should_proceed: bool
    final_answer: str


@dataclass
class DiagnosticResult:
    """Structured output node diagnostic result"""
    question: str
    history: list[dict] = field(default_factory=list)
    analyses: list[str] = field(default_factory=list)
    iteration: int = 0
    final_answer: str = ""
    error: str | None = None


class AgentGraph:
    """Diagnose agent graph"""
    def __init__(
        self,
        max_iterations: int = MAX_ITERATIONS,
        max_llm_retries: int = MAX_LLM_RETRIES,
        max_parallel: int = MAX_PARALLEL_COMMANDS,
    ) -> None:
        self.max_iterations = max_iterations
        self.max_llm_retries = max_llm_retries
        self.max_parallel = max_parallel
        self.llm = get_llm()
        self.tools = build_tools()
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.graph = self._build_graph()

    def _invoke_with_retry(self, runnable: Any, message: list, label: str) -> Any | None:
        """Invoke the LLM retrying on transient backend failures"""
        for attempt in range(1, self.max_llm_retries + 1):
            try:
                return runnable.invoke(message)
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    f"{label}: falha do LLM "
                    f"(tentativa {attempt}/{self.max_llm_retries}): {e}"
                )
        logger.error(f"{label}: LLM falhou em todas as tentativas.")
        return None

    # nodes
    def _n_decide_tool(self, state: AgentState) -> dict:
        """LLM choice the next tools (fan-out)"""
        executed = state.get("executed", [])
        message = [
            SystemMessage(content=SYSTEM_CHOICE),
            HumanMessage(content=mount_human_choice(state["question"], executed))
        ]

        response = self._invoke_with_retry(self.llm_with_tools, message, "decide_tool")
        if response is None:
            return {
                "tools_pending": [],
                "errors": ["O modelo de linguagem não respondeu (falha no Ollama)."]
            }

        tool_calls = response.tool_calls or []
        pending: list[dict] = []
        seen = set(executed)

        for tool in tool_calls:
            name = tool["name"]
            if name in seen:
                continue
            seen.add(name)
            pending.append({"name": name, "args": tool.get("args", {}) or {}})

        if not pending:
            logger.info("decide_tool: nenhuma tool nova escolhida.")
            return {"tools_pending": []}

        logger.info(f"decide_tool: {len(pending)} tool(s) -> {[p['name'] for p in pending]}")

        return {
            "tools_pending": pending,
            "iteration": state.get("iteration", 0) + 1
        }

    def _n_validate(self, state: AgentState) -> dict:
        """security validation"""
        checked: list[dict] = []
        errors: list[str] = []

        for p in state.get("tools_pending", []):
            name, args = p["name"], p.get("args", {})

            if name not in ALLOWED_COMMANDS:
                errors.append(f"Tool '{name}' fora da whitelist.")
                continue

            try:
                command = mount_command(name, args)
            except ValidationError as e:
                logger.warning(f"validate: bloqueado '{name}' - {e}")
                errors.append(f"{name}: {e}")
                continue

            checked.append({"name": name, "comando": command})
        return {"checked": checked, "errors": errors}

    def _execute_one(self, check: dict) -> dict:
        """Run a single validated command and summarize its output."""
        name, command = check["name"], check["comando"]
        cfg = ALLOWED_COMMANDS[name]
        result = execute(command, timeout=cfg.get("timeout"))
        summary = summarize_result(result)
        summary["comando"] = command
        summary["tool"] = name
        return summary

    def _n_execute(self, state: AgentState) -> dict:
        """execute validated commands and summarize the outputs"""
        checked = state.get("checked", [])
        if not checked:
            return {"summary": []}

        if len(checked) == 1:
            return {"summary": [self._execute_one(checked[0])]}

        workers = min(len(checked), self.max_parallel)
        logger.info(f"execute: {len(checked)} comando(s) em {workers} thread(s)")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            summarized = list(pool.map(self._execute_one, checked))
        return {"summary": summarized}

    def _n_analyze(self, state: AgentState) -> dict:
        """the agent interprets the outputs of this round and logs the steps"""
        summaries = state.get("summary", [])
        if not summaries:
            return {}

        steps = [
            {
                "tool": s["tool"],
                "comando": s["comando"],
                "saida": s["text"],
                "alertas": s["alerts"],
            }
            for s in summaries
        ]
        names = [s["tool"] for s in summaries]

        message = [
            SystemMessage(content=SYSTEM_ANALYSIS_MULTI),
            HumanMessage(
                content=mount_human_analysis(
                    state["question"], [_format_to_llm(s) for s in summaries]
                )
            )
        ]
        response = self._invoke_with_retry(self.llm, message, "analyze")
        if response is None:
            # os comandos já rodaram; segue sem a análise em vez de perdê-los
            return {
                "history": steps,
                "executed": names,
                "errors": ["Não foi possível analisar as saídas (falha no modelo)."]
            }

        return {"history": steps, "executed": names, "analyses": [response.content]}

    def _n_decide_next(self, state: AgentState) -> dict:
        """agent decide if need run another command"""
        if state.get("iteration", 0) >= self.max_iterations:
            logger.info("decide_next: limite de iterações atingido")
            return {"should_proceed": False}
        message = [
            SystemMessage(content=SYSTEM_DECIDE_NEXT),
            HumanMessage(
                content=mount_next_human_choice(
                    state["question"],
                    state["history"],
                    state.get("analyses", [])
                )
            )
        ]
        decision = self._invoke_with_retry(
            self.llm.with_structured_output(NextDecision), message, "decide_next"
        )
        if decision is None:
            logger.warning("decide_next: sem decisão do modelo; finalizando.")
            return {"should_proceed": False}

        logger.info(f"decide_next: {decision.needs_more} ({decision.reason})")
        return {"should_proceed": bool(decision.needs_more)}

    def _n_finalize(self, state: AgentState) -> dict:
        """merge the history into the final response"""
        history = state.get("history", [])
        errors = state.get("errors", [])

        if not history:
            if errors:
                return {
                    "final_answer": f"Não consegui investigar: {'; '.join(errors)}"
                }
            return {
                "final_answer": (
                    "Não consegui mapear sua pergunta para um commando de "
                    "diagnostico conhecido. Tente reformular"
                )
            }
        analyses = state.get("analyses", [])
        message = [
            SystemMessage(content=SYSTEM_FINALIZE),
            HumanMessage(
                content=mount_end_human_choice(state["question"], history, analyses)
            )
        ]
        result = self._invoke_with_retry(self.llm, message, "finalize")
        if result is None:
            response = (
                "Não consegui redigir a resposta final (falha no modelo), "
                "mas os comandos abaixo foram executados:\n"
                + "\n".join(f"  $ {s['comando']}" for s in history)
            )
            if analyses:
                response += "\n\n" + "\n".join(analyses)
        else:
            response = result.content

        if errors:
            response = (
                f"{response}\n\n"
                f"[não foi possível executar: {'; '.join(errors)}]"
            )
        return {"final_answer": response}

    # conditionals
    def _route_after_decide_tool(self, state: AgentState) -> str:
        return "validate" if state.get("tools_pending") else "finalize"

    def _route_after_validate(self, state: AgentState) -> str:
        """Runs whatever passed validation; a single blocked tool must not
        abort the other tools of the same fan-out."""
        return "execute" if state.get("checked") else "finalize"

    def _route_after_decide_next(self, state: AgentState) -> str:
        if state.get("should_proceed") and state.get("iteration", 0) < self.max_iterations:
            return "decide_tool"
        return "finalize"

    # build graph
    def _build_graph(self):
        b_graph = StateGraph(AgentState)
        b_graph.add_node("decide_tool", self._n_decide_tool)
        b_graph.add_node("validate", self._n_validate)
        b_graph.add_node("execute", self._n_execute)
        b_graph.add_node("analyze", self._n_analyze)
        b_graph.add_node("decide_next", self._n_decide_next)
        b_graph.add_node("finalize", self._n_finalize)

        b_graph.set_entry_point("decide_tool")
        b_graph.add_conditional_edges(
            "decide_tool",
            self._route_after_decide_tool,
            {"validate": "validate", "finalize": "finalize"}
        )
        b_graph.add_conditional_edges(
            "validate",
            self._route_after_validate,
            {"execute": "execute", "finalize": "finalize"}
        )
        b_graph.add_edge("execute", "analyze")
        b_graph.add_edge("analyze", "decide_next")
        b_graph.add_conditional_edges(
            "decide_next",
            self._route_after_decide_next,
            {"decide_tool": "decide_tool", "finalize": "finalize"}
        )
        b_graph.add_edge("finalize", END)
        return b_graph.compile()

    def diagnose(self, question: str) -> DiagnosticResult:
        initial_state: dict[str, Any] = {
            "question": question,
            "iteration": 0,
            "history": [],
            "executed": [],
            "errors": [],
            "analyses": []
        }
        final = self.graph.invoke(
            initial_state,
            config={"recursion_limit": self.max_iterations * 6 + 5}
        )
        errors = final.get("errors", [])
        return DiagnosticResult(
            question=question,
            history=final.get("history", []),
            analyses=final.get("analyses", []),
            iteration=final.get("iteration", 0),
            final_answer=final.get("final_answer", ""),
            error="; ".join(errors) if errors else None
        )
