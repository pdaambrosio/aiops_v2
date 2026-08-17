from functools import lru_cache
from langchain_ollama import ChatOllama
from config import (
    LLM_TEMPERATURE,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_NUM_CTX,
    OLLAMA_NUM_GPU,
)
from utils import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=4)
def get_llm(temperature: float = LLM_TEMPERATURE) -> ChatOllama:
    """Returns a ChatOllama instance (cached per temperature)"""
    logger.info(
        "Inicializando ChatOllama modelo=%s temperature=%s num_ctx=%s num_gpu=%s",
        OLLAMA_MODEL, temperature, OLLAMA_NUM_CTX, OLLAMA_NUM_GPU
    )
    return ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=temperature,
        num_ctx=OLLAMA_NUM_CTX,
        num_gpu=OLLAMA_NUM_GPU
    )
