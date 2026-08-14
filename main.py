import sys
from agents import AgentGraph

from config import show_configs, validate_config
from utils import get_logger

logger = get_logger("aiops_v2")


def _print_result(llm) -> None:
    print()
    for index, step in enumerate(llm.history, 1):
        command = step.get("comando") or step["tool"]
        print(f"Passo {index}: {step['tool']} -> {command}")

        if step.get("alertas"):
            print(f"ALERTAS: {', '.join(step['alertas'])}")

    if llm.error:
        print(f"ERROR: {llm.error}")

    print(f"\n{llm.final_answer}")


def main() -> int:
    show_configs()
    if not validate_config():
        print("Ollama indisponível. Verifique se o serviço está rodando.")
        return 1

    print("Inicializando o Agent...")
    agent = AgentGraph()
    print("Pronto. Faça uma pergunta sobre o servidor (ou 'sair').\n")

    while True:
        try:
            question = input("aiops_v2> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté mais.")
            return 0

        if not question:
            continue
        if question.lower() in {"sair", "exit", "quit", "q"}:
            print("Até mais.")
            return 0

        try:
            result = agent.diagnose(question)
            _print_result(result)
        except Exception as e: # noqa: BLE001
            logger.exception("Erro ao diagnosticar")
            print(f"\nErro inesperado: {e}\n")

if __name__ == "__main__":
    sys.exit(main())