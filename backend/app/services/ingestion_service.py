
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk
from app.services.chunking_service import split_text
from app.services.embedding_service import generate_embeddings
from app.vectorstore.chroma_store import add_chunks


def ingest_document(
    db: Session,
    title: str,
    content: str,
) -> Document:
    # 1. Split the document into chunks
    chunks = split_text(content)

    if not chunks:
        raise ValueError("Document content cannot be empty")

    # 2. Generate embeddings for all chunks
    embeddings = generate_embeddings(chunks)

    document = Document(
        title=title.strip(),
        content=content.strip(),
    )

    try:
        # 3. Save the document and chunks in MySQL
        db.add(document)
        db.flush()  # Generate the document ID without committing

        db_chunks = []

        for index, chunk_text in enumerate(chunks):
            db_chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                chunk_text=chunk_text,
            )
            db.add(db_chunk)
            db_chunks.append(db_chunk)

        db.flush()

        # 4. Index chunks in ChromaDB using MySQL chunk IDs
        add_chunks(
            chunk_ids=[str(chunk.id) for chunk in db_chunks],
            chunks=chunks,
            embeddings=embeddings,
            metadatas=[
                {
                    "document_id": document.id,
                    "chunk_id": chunk.id,
                    "title": document.title,
                    "chunk_index": chunk.chunk_index,
                }
                for chunk in db_chunks
            ],
        )

        # 5. Commit the database transaction
        db.commit()
        db.refresh(document)

        return document

    except Exception:
        db.rollback()
        raise
