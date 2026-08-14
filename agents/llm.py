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


@lru_cache(maxsize=1)
def get_llm() -> ChatOllama:
    """Returns a ChatOllama instance"""
    logger.info(
        "Inicializando ChatOllama modelo=%s num_ctx=%s num_gpu=%s",
        OLLAMA_MODEL, OLLAMA_NUM_CTX, OLLAMA_NUM_GPU
    )
    return ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=LLM_TEMPERATURE,
        num_ctx=OLLAMA_NUM_CTX,
        num_gpu=OLLAMA_NUM_GPU
    )
