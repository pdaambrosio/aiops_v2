import requests

from chromadb.utils.embedding_functions import EmbeddingFunction
from config import OLLAMA_BASE_URL, OLLAMA_EMBEDDINGS_MODEL


class CompactEmbeddingFunctionDMR(EmbeddingFunction):
    def __init__(
            self,
            base_url: str =OLLAMA_BASE_URL,
            model: str = OLLAMA_EMBEDDINGS_MODEL
    ) -> None:
        self.base_url = base_url
        self.model = model

    def __call__(self, input: list[str]) -> list[list[float | int]]:
        response = requests.post(
            f"{self.base_url}/v1/embeddings",
            json={
                "model": self.model,
                "input": input
            },
            timeout=30,
        )

        response.raise_for_status()
        return [item["embedding"] for item in response.json()["data"]]

    @staticmethod
    def name() -> str:
        return "CompactEmbeddingFunctionDMR"

    def get_config(self) -> dict:
        return {"base_url": self.base_url, "model": self.model}

    @staticmethod
    def build_from_config(config: dict) -> "CompactEmbeddingFunctionDMR":
        return CompactEmbeddingFunctionDMR(
            base_url=config["base_url"],
            model=config["model"]
        )