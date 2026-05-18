import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from app.config.settings import settings

_chroma_client: chromadb.PersistentClient | None = None
_embedding_model: SentenceTransformer | None = None


async def init_chromadb():
    global _chroma_client, _embedding_model
    _chroma_client = chromadb.PersistentClient(
        path=settings.CHROMA_PERSIST_DIR,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
    print(f"ChromaDB initialized at {settings.CHROMA_PERSIST_DIR}")


def get_chroma_client() -> chromadb.PersistentClient:
    if _chroma_client is None:
        raise RuntimeError("ChromaDB not initialized.")
    return _chroma_client


def get_embedding_model() -> SentenceTransformer:
    if _embedding_model is None:
        raise RuntimeError("Embedding model not initialized.")
    return _embedding_model


def get_user_collection(user_id: str):
    """Get or create a ChromaDB collection for a specific user."""
    client = get_chroma_client()
    collection_name = f"{settings.CHROMA_COLLECTION_PREFIX}{user_id}"
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def delete_user_collection(user_id: str):
    """Delete user's vector collection."""
    client = get_chroma_client()
    collection_name = f"{settings.CHROMA_COLLECTION_PREFIX}{user_id}"
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts."""
    model = get_embedding_model()
    return model.encode(texts, normalize_embeddings=True).tolist()