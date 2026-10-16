
import chromadb

from app.core.config import settings

client = chromadb.PersistentClient(
    path=settings.CHROMA_PATH
)

collection = client.get_or_create_collection(
    name="knowledge_documents",
    metadata={"hnsw:space": "cosine"},
)


def add_chunks(
    chunk_ids: list[str],
    chunks: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
) -> None:
    if not chunk_ids:
        return

    collection.upsert(
        ids=chunk_ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def search_chunks(
    query_embedding: list[float],
    top_k: int = 3,
) -> dict:
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
