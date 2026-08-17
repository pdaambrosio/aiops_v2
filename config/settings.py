import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
CORE_DIR = PROJECT_ROOT / "core"
AGENT_DIR = PROJECT_ROOT / "agent"
UTILS_DIR = PROJECT_ROOT / "utils"
TESTS_DIR = PROJECT_ROOT / "tests"

# Model LLM base (local)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_TOOL_TEMPERATURE = float(os.getenv("LLM_TOOL_TEMPERATURE", "0.0"))
OLLAMA_NUM_GPU = int(os.getenv("OLLAMA_NUM_GPU", "8"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))

# Command executor
COMMAND_TIMEOUT = int(os.getenv("COMMAND_TIMEOUT", "30"))
MAX_OUTPUT_LENGTH = int(os.getenv("MAX_OUTPUT_LENGTH", "5000"))
MAX_ERROR_LENGTH = int(os.getenv("MAX_ERROR_LENGTH", "1000"))

# Logs
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"

# Debug
DEBUG = os.getenv("DEBUG", "false").lower() == "true"


def validate_config() -> bool:
    """validate config"""
    try:
        import requests

        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if resp.status_code != 200:
            print(f"Ollama respondeu com status {resp.status_code} em {OLLAMA_BASE_URL}")
            return False
        return True
    except Exception as e:
        print(f"Não foi possível conectar ao Ollama em {OLLAMA_BASE_URL}: {e}")
        return False


def show_configs() -> None:
    """show configs"""
    print("\nCONFIGURAÇÕES")
    print(f"  Ollama URL : {OLLAMA_BASE_URL}")
    print(f"  Modelo     : {OLLAMA_MODEL}")
    print(f"  Contexto   : {OLLAMA_NUM_CTX} tokens")
    print(f"  Timeout    : {COMMAND_TIMEOUT}s")
    print(f"  Max output : {MAX_OUTPUT_LENGTH} chars")
    print(f"  Log level  : {LOG_LEVEL}")
    print(f"  Debug      : {DEBUG}\n")
