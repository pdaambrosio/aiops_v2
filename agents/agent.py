from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import get_llm
from agents.prompts import SYSTEM_ANALYSIS, SYSTEM_CHOICE, setup_human_analysis
from agents.tools import build_tools, execute_tool_command, _format_to_llm
from config import ALLOWED_COMMANDS
from core import ValidationError
from utils import get_logger

logger = get_logger(__name__)


@dataclass
class DiagnosticResult:
    """Complete diagnostic result"""
    question: str
    tool: str | None = None
    parameter: dict = field(default_factory=dict)
    command: str | None = None
    output: str | None = None
    alerts: list[str] = field(default_factory=list)
    analysis: str = ""
    error: str | None = None


class DiagnosticAgent:
    """Agent class for diagnostics"""
    def __init__(self):
        self.llm = get_llm()
        self.tools = build_tools()
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    def _select_tool(self, question: str) -> str | list[str | dict[Any, Any]]:
        """LLM select tool"""
        message = [
            SystemMessage(content=SYSTEM_CHOICE),
            HumanMessage(content=question)
        ]
        return self.llm.invoke(message).content

    def _analyze(self, question: str, tool: str, observation: str) -> str | list[str | dict[Any, Any]]:
        """LLM analyze tool command"""
        message = [
            SystemMessage(content=SYSTEM_ANALYSIS),
            HumanMessage(content=setup_human_analysis(question, tool, observation))
        ]
        return self.llm.invoke(message).content

    def diagnose(self, question: str) -> DiagnosticResult:
        """LLM diagnose tool command"""
        result = DiagnosticResult(question=question)

        tool_calls = self._select_tool(question)
        if not tool_calls:
            result.error = (
                "O modelo não escolheu nenhuma ferramenta para esta pergunta."
            )
            result.analysis = (
                "Não consegui mapear sua pergunta para um comando de diagnóstico "
                "conhecido. Tente reformular (ex.: disco, memória, nginx, docker)."
            )
            return result

        choice = tool_calls[0]
        name = choice["name"]
        args = choice.get("args", {}) or {}
        result.tool = name
        result.parameter = args
        logger.info(f"LLM escolheu a tool: {name} {args}")

        if name not in ALLOWED_COMMANDS:
            result.error = f"Tool {name} fora da whitelist"
            result.analysis = "A ferramenta escolhida não é permitida."
            return result

        try:
            resume = execute_tool_command(name, args)
        except ValidationError as e:
            logger.warning(f"Validação bloqueou a execução da tool: {e}")
            result.error = str(e)
            result.analysis = "A ferramenta escolhida não é permitida."
            return result

        result.command = resume["command"]
        result.output = resume["output"]
        result.alerts = resume["alerts"]

        observation = _format_to_llm(resume)
        result.analysis = self._analyze(question, name, observation)
        return result
