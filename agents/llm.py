from functools import lru_cache
from langchain_ollama import ChatOllama
from config import LLM_TEMPERATURE, OLLAMA_BASE_URL, OLLAMA_MODEL
from utils import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_llm() -> ChatOllama:
    """Returns a ChatOllama instance"""
    logger.info("Inicializando ChatOllama modelo=%s", OLLAMA_MODEL)
    return ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=LLM_TEMPERATURE
    )
