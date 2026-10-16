
from app.services.embedding_service import generate_embedding
from app.vectorstore.chroma_store import add_chunks, search_chunks


def test_vector_search():
    texts = [
        "Customers can request a refund within 30 days.",
        "Employees can apply for annual leave.",
    ]

    embeddings = [generate_embedding(text) for text in texts]

    add_chunks(
        chunk_ids=["test-refund", "test-leave"],
        chunks=texts,
        embeddings=embeddings,
        metadatas=[
            {"document_id": 1, "title": "Refund Policy"},
            {"document_id": 2, "title": "Leave Policy"},
        ],
    )

    query_embedding = generate_embedding(
        "How long do I have to get my money back?"
    )

    results = search_chunks(query_embedding, top_k=1)

    print("Search result:", results["documents"][0])
    print("Metadata:", results["metadatas"][0])


if __name__ == "__main__":
    test_vector_search()
