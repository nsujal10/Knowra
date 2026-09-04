from abc import ABC, abstractmethod
import structlog
from typing import List

logger = structlog.get_logger(__name__)

class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        pass

class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            logger.info("Local Embedding Model loaded", model_name=model_name)
        except ImportError:
            logger.error("sentence_transformers not installed. Install via worker requirements.")
            raise

    def embed_query(self, text: str) -> List[float]:
        try:
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error("Embed query failed", error=str(e))
            raise

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        try:
            embeddings = self.model.encode(texts)
            return embeddings.tolist()
        except Exception as e:
            logger.error("Embed documents failed", error=str(e))
            raise
