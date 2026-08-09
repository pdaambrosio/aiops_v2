import operator
from dataclasses import dataclass, field
from typing import Annotated, Any, TypedDict
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from agents.llm import get_llm
from agents.prompts import (
    SYSTEM_ANALYSIS,
    SYSTEM_DECIDE_NEXT,
    SYSTEM_CHOICE,
    SYSTEM_FINALIZE,
    setup_human_analysis,
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


class NextDecision(BaseModel):
    """Structured output node decide_next"""
    needs_more: bool = Field(description="Se é preciso rodar mais um comando.")
    reason: str = Field(description="Justificativa curta da decisão.")


class AgentState(TypedDict, total=False):
    """Shared state between graph nodes"""
    question: str
    iteration: int
    # history
    history: Annotated[list[dict], operator.add]
    executed: Annotated[list[str], operator.add]
    # current fields
    current_tool: str | None
    current_args: dict
    current_command: str | None
    current_observation: str
    current_summary: dict
    # control
    should_proceed: bool
    error: str | None
    final_answer: str


@dataclass
class DiagnosticResult:
    """Structured output node diagnostic result"""
    question: str
    history: list[dict] = field(default_factory=list)
    iteration: int = 0
    final_answer: str = ""
    error: str | None = None


class AgentGraph:
    """Diagnose agent graph"""
    def __init__(self, max_iterations: int = MAX_ITERATIONS) -> None:
        self.max_iterations = max_iterations
        self.llm = get_llm()
        self.tools = build_tools()
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.graph = self._build_graph()

    # nodes
    def _n_decide_tool(self, state: AgentState) -> dict:
        """LLM choice the next tool"""
        executed: list[str] | list[Any] = state.get("executed", [])
        messages = [
            SystemMessage(content=SYSTEM_CHOICE),
            HumanMessage(content=mount_human_choice(state["question"], executed))
        ]
        response = self.llm_with_tools.invoke(messages)
        tool_calls = response.tool_calls or []
        if not tool_calls:
            logger.info("decide_tool: LLM não escolheu tool.")
            return {"tool_atual": None}
        choice = tool_calls[0]
        name = choice["name"]
        args = choice.get("args", {}) or {}
        logger.info(f"decide_tool: tool={name}, args={args}")
        return {
            "current_tool": name,
            "current_args": args,
            "iteration": state.get("iteration", 0) + 1
        }

    def _n_validate(self, state: AgentState) -> dict:
        """security validation"""
        name = state["current_tool"]
        args = state.get("current_args", {})
        if name not in ALLOWED_COMMANDS:
            return {"erro": f"Tool '{name}' fora da whitelist.", "comando_atual": None}
        try:
            command = mount_command(name, args)
        except ValidationError as e:
            logger.warning(f"validate: bloqueado - {e}")
            return {"erro": str(e), "comando_atual": None}
        return {"comando_atual": command, "erro": None}

    def _n_execute(self, state: AgentState) -> dict:
        """execute validate command and summarize the output"""
        name = state["current_tool"]
        cfg = ALLOWED_COMMANDS[name]
        result = execute(state["current_command"], timeout=cfg.get("timeout"))
        summary = summarize_result(result)
        summary["comando"] = state["current_command"]
        summary["tool"] = name
        return {
            "resumido_atual": summary,
            "observacao_atual": _format_to_llm(summary)
        }

    def _n_analyze(self, state: AgentState) -> dict:
        """the agent interprets the output of this command and logs the step"""
        name = state["current_tool"]
        summary = state["current_summary"]
        message = [
            SystemMessage(content=SYSTEM_ANALYSIS),
            HumanMessage(
                content=setup_human_analysis(
                    state["question"],
                    name,
                    state["current_observation"]
                )
            )
        ]
        analysis = self.llm.invoke(message).content
        step = {
            "tool": name,
            "comando": summary["comando"],
            "saida": summary["texto"],
            "alertas": summary["alertas"],
            "analise": analysis
        }
        return {"history": [step], "executed": [name]}

    def _n_decide_next(self, state: AgentState) -> dict:
        """agent decide if need run another command"""
        if state.get("iteration", 0) >= self.max_iterations:
            logger.info("decide_next: limite de iterações atingido")
            return {"continuar": False}
        message = [
            SystemMessage(content=SYSTEM_DECIDE_NEXT),
            HumanMessage(
                content=mount_next_human_choice(
                    state["question"],
                    state["history"]
                )
            )
        ]
        try:
            decision = self.llm.with_structured_output(NextDecision).invoke(message)
            logger.info(
                f"decide_next: precisa_main={decision.needs_more} ({decision.reason})"
            )
            return {"should_proceed": bool(decision.needs_more)}
        except Exception as e: # noqa: BLE001
            logger.warning(f"decide_next: falha na saída estruturada {e}; finalizando.")
            return {"should_proceed": False}

    def _n_finalize(self, state: AgentState) -> dict:
        """merge the history into the final response"""
        history = state.get("history", [])
        if not history:
            error = state.get("error")
            if error:
                return {
                    "resposta_final": f"Não consegui investigar: {error}"
                }
            return {
                "resposta_final": (
                    "Não consegui mapear sua pergunta para um commando de "
                    "diagnostico conhecido. Tente reformular"
                )
            }
        message = [
            SystemMessage(content=SYSTEM_FINALIZE),
            HumanMessage(
                content=mount_end_human_choice(state["question"], history)
            )
        ]
        response = self.llm.invoke(message).content
        return {"final_answer": response}

    # conditionals
    def _route_after_decide_tool(self, state: AgentState) -> str:
        return "validate" if state.get("current_tool") else "finalize"

    def _route_after_validate(self, state: AgentState) -> str:
        return "finalize" if state.get("error") else "execute"

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
            "executed": []
        }
        final = self.graph.invoke(
            initial_state,
            config={"recursion_limit": self.max_iterations * 6 + 5}
        )
        return DiagnosticResult(
            question=question,
            history=final.get("history", []),
            iteration=final.get("iteration", 0),
            final_answer=final.get("final_answer", ""),
            error=final.get("error")
        )

