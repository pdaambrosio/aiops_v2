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

    instalados = {m["name"] for m in resp.json().get("models", [])}
    if OLLAMA_MODEL not in instalados:
        return f"Modelo {OLLAMA_MODEL} não está instalado (ollama pull {OLLAMA_MODEL})"

    return None
