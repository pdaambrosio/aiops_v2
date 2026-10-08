import chromadb

from functools import lru_cache
from config import (
    CHROMA_COLLECTION,
    CHROMA_DIR,
    PLAYBOOK_MAX_DISTANCE,
    PLAYBOOK_TOP_K,
    PLAYBOOKS_DIR
)
from rag.embeddings import CompactEmbeddingFunctionDMR
from utils import get_logger

logger = get_logger(__name__)


def _load_playbook_files() -> dict[str, str]:
    return {path.stem: path.read_text(encoding="utf-8") for path in sorted(PLAYBOOKS_DIR.glob("*.md"))}


@lru_cache(maxsize=1)
def get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(
        CHROMA_COLLECTION,
        embedding_function=CompactEmbeddingFunctionDMR()
    )

    if collection.count() == 0:
        playbooks = _load_playbook_files()
        if playbooks:
            collection.add(
                ids=list(playbooks.keys()),
                documents=list(playbooks.values())
            )

            logger.info(
                f"playbooks: {len(playbooks)} runbook(s) indexado(s) em {CHROMA_DIR}"
            )

    return collection


def search_playbook(query: str, k: int = PLAYBOOK_TOP_K) -> str | None:
    collection = get_collection()
    if collection.count() == 0:
        return None

    result = collection.query(query_texts=[query], n_results=k)
    documents = result["documents"][0]
    distances = result["distances"][0]

    if not documents or distances[0] > PLAYBOOK_MAX_DISTANCE:
        return None

    logger.info(f"playbooks: melhor match distancia={distances[0]:.4f}")
    return documents[0]
