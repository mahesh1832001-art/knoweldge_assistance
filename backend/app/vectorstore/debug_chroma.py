
from app.core.config import settings
from app.services.embedding_service import generate_embedding
import chromadb

client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
collection = client.get_collection("knowledge_documents")

print("ChromaDB path:", settings.CHROMA_PATH)
print("Total stored chunks:", collection.count())

# Inspect stored chunks
if collection.count() > 0:
    data = collection.peek(limit=5)

    print("\nStored document chunks:")
    for i, chunk in enumerate(data.get("documents", [])):
        print(f"\nChunk {i + 1}:")
        print(chunk[:500])

    print("\nStored metadata:")
    print(data.get("metadatas"))

    # Test semantic retrieval independently
    question = input("\nEnter your question: ").strip()
    embedding = generate_embedding(question)

    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(5, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    print("\nTop matching chunks:")
    for i, chunk in enumerate(results["documents"][0]):
        print(f"\nResult {i + 1}")
        print("Distance:", results["distances"][0][i])
        print("Metadata:", results["metadatas"][0][i])
        print("Text:", chunk[:500])
else:
    print("The collection is empty.")
