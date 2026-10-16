
import hashlib
import logging
import re

from sqlalchemy.orm import Session

from app.core.logging_utils import get_transaction_logger
from app.db.models import AnswerCache, QuestionHistory
from app.services.embedding_service import generate_embedding
from app.services.llm_service import generate_answer
from app.vectorstore.chroma_store import search_chunks
from app.core.config import MAX_COSINE_DISTANCE, DEFAULT_TOP_K


logger = logging.getLogger(__name__)


def normalize_question(question: str) -> str:
    """Normalize whitespace and case for question matching."""
    return re.sub(r"\s+", " ", question.strip()).casefold()


def create_cache_key(normalized_question: str) -> str:
    """Create a stable SHA-256 cache key."""
    return hashlib.sha256(
        normalized_question.encode("utf-8")
    ).hexdigest()


def answer_question(
    db: Session,
    question: str,
    transaction_id: str,
) -> dict:
    request_logger = get_transaction_logger(
        __name__,
        transaction_id,
    )

    if not question or not question.strip():
        raise ValueError("Question cannot be empty")

    normalized_question = normalize_question(question)
    cache_key = create_cache_key(normalized_question)

    request_logger.info("Question received: %s", question.strip())

    try:
        # STEP 1: Check the answer cache before embedding or vector search.
        cached = (
            db.query(AnswerCache)
            .filter(AnswerCache.cache_key == cache_key)
            .first()
        )

        if cached:
            request_logger.info(
                "Answer cache HIT | Cache ID: %s | "
                "Embedding and LLM calls skipped",
                cached.id,
            )

            # Preserve the question history even for cache hits.
            history = QuestionHistory(
                question=question.strip(),
                answer=cached.answer,
            )
            db.add(history)
            db.commit()

            return {
                "answer": cached.answer,
                "sources": cached.sources or [],
            }

        request_logger.info(
            "Answer cache MISS | Starting retrieval pipeline"
        )

        # STEP 2: Generate the embedding only on a cache miss.
        query_embedding = generate_embedding(question.strip())

        # STEP 3: Search ChromaDB.
        search_results = search_chunks(
            query_embedding,
            top_k=DEFAULT_TOP_K,
        )

        documents = (search_results.get("documents") or [[]])[0]
        metadatas = (search_results.get("metadatas") or [[]])[0]
        distances = (search_results.get("distances") or [[]])[0]
        result_ids = (search_results.get("ids") or [[]])[0]

        sources = []
        context_parts = []

        for index, chunk_text in enumerate(documents):
            if not chunk_text:
                continue

            metadata = (
                metadatas[index]
                if index < len(metadatas) and metadatas[index]
                else {}
            )

            distance = (
                distances[index]
                if index < len(distances)
                else None
            )

            if distance is not None and distance > MAX_COSINE_DISTANCE:
                continue

            raw_document_id = metadata.get("document_id")
            raw_chunk_id = metadata.get("chunk_id")

            try:
                document_id = (
                    int(raw_document_id)
                    if raw_document_id is not None
                    else None
                )
            except (TypeError, ValueError):
                document_id = None

            if raw_chunk_id is None and index < len(result_ids):
                raw_chunk_id = result_ids[index]

            chunk_id = (
                str(raw_chunk_id)
                if raw_chunk_id is not None
                else None
            )

            title = metadata.get("title") or "Untitled document"

            source = {
                "document_id": document_id,
                "chunk_id": chunk_id,
                "title": title,
                "content": chunk_text,
            }

            sources.append(source)
            context_parts.append(
                f"Document: {title}\nContent: {chunk_text}"
            )

        request_logger.info(
            "Retrieval completed | Sources found: %s",
            len(sources),
        )

        # STEP 4: Generate an answer using the LLM only on a cache miss.
        if context_parts:
            context = "\n\n---\n\n".join(context_parts)

            answer = generate_answer(
                question=question.strip(),
                context=context,
                transaction_id=transaction_id,
            )
        else:
            answer = (
                "I couldn't find relevant information in the available "
                "documents to answer your question."
            )

            request_logger.warning("No relevant chunks found")

        # STEP 5: Save the answer and sources in the cache.
        cache_entry = AnswerCache(
            cache_key=cache_key,
            normalized_question=normalized_question,
            answer=answer,
            sources=sources,
        )

        history = QuestionHistory(
            question=question.strip(),
            answer=answer,
        )

        db.add(cache_entry)
        db.add(history)
        db.commit()
        db.refresh(cache_entry)

        request_logger.info(
            "Answer cached successfully | Cache ID: %s",
            cache_entry.id,
        )

        return {
            "answer": answer,
            "sources": sources,
        }

    except Exception:
        db.rollback()
        request_logger.exception(
            "Question processing or answer caching failed"
        )
        raise
