import sys
from typing import Literal

from agents import DiagnosticAgent
from config import show_configs, validate_config
from utils import get_logger

logger = get_logger("aiops_v2")


def _print_result(llm) -> None:
    print()
    if llm.tool:
        cmd = f"> {llm.command}" if llm.command else ""
        print(f"TOOL: {llm.tool}{cmd}")

    if llm.alerts:
        print(f"ALERTS: {' ,'.join(llm.alerts)}")

    if llm.error:
        print(f"ERROR: {llm.error}")

    print(f"\n\n{llm.analysis}\n\n")


def main() -> Literal[0, 1] | None:
    show_configs()
    if not validate_config():
        print("Ollama indisponível. Verifique se o serviço está rodando.")
        return 1

    print("Inicializando agente...")
    agent = DiagnosticAgent()
    print("Pronto. Faça uma pergunta sobre o servidor (ou 'sair').\n")

    while True:
        try:
            question = input("aiops> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nOk, bye!")
            return 0

        if not question:
            continue

        if question.lower() in {"sair", "exit", "quit", "q"}:
            print("\nOk, bye!")
            return 0

        try:
            result = agent.diagnose(question)
            _print_result(result)
        except Exception as e: # noqa: BLE001
            logger.exception("Erro ao diagnosticar")
            print(f"\nErro ao diagnosticar: {e}\n")


if __name__ == "__main__":
    sys.exit(main())