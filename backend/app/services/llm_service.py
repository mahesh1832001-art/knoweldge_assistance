
import logging
import random
import time

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)
from google import genai

from app.core.config import settings
from app.core.logging_utils import get_transaction_logger


OPENAI_MODEL = "gpt-4o-mini"
GEMINI_MODEL = "gemini-2.5-flash"

MAX_OPENAI_ATTEMPTS = 3
BASE_RETRY_DELAY = 1.0
MAX_RETRY_DELAY = 8.0
REQUEST_TIMEOUT_SECONDS = 20.0


def _is_retryable_openai_error(error: Exception) -> bool:
    """Identify OpenAI errors that may succeed on retry."""

    if isinstance(
        error,
        (APITimeoutError, APIConnectionError, RateLimitError),
    ):
        return True

    if isinstance(error, APIStatusError):
        return (
            error.status_code in (408, 409, 429)
            or error.status_code >= 500
        )

    return False


def _build_prompt(question: str, context: str) -> str:
    return (
        "Answer the question using only the document context below. "
        "Do not invent facts or use outside knowledge. If the context "
        "does not contain the answer, say so clearly.\n\n"
        f"Document context:\n{context}\n\n"
        f"Question:\n{question}"
    )


def _generate_with_openai(
    prompt: str,
    transaction_id: str,
    logger,
) -> str:
    """Try OpenAI with bounded retries."""

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=0,
    )

    last_error = None

    for attempt in range(1, MAX_OPENAI_ATTEMPTS + 1):
        try:
            logger.info(
                "Calling primary LLM | Provider: OpenAI | "
                "Model: %s | Attempt: %s/%s",
                OPENAI_MODEL,
                attempt,
                MAX_OPENAI_ATTEMPTS,
            )

            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a document-grounded knowledge assistant. "
                            "Use only the provided context."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

            answer = response.choices[0].message.content

            if not answer or not answer.strip():
                raise RuntimeError("OpenAI returned an empty answer")

            logger.info("Primary LLM succeeded | Provider: OpenAI")
            return answer.strip()

        except Exception as error:
            last_error = error
            retryable = _is_retryable_openai_error(error)

            if not retryable or attempt >= MAX_OPENAI_ATTEMPTS:
                logger.warning(
                    "Primary LLM failed | Provider: OpenAI | "
                    "Error type: %s | Retryable: %s",
                    type(error).__name__,
                    retryable,
                )
                raise

            delay = min(
                BASE_RETRY_DELAY * (2 ** (attempt - 1)),
                MAX_RETRY_DELAY,
            )
            delay += random.uniform(0, 0.5)

            logger.warning(
                "OpenAI attempt failed | Attempt: %s/%s | "
                "Error type: %s | Retrying in %.2f seconds",
                attempt,
                MAX_OPENAI_ATTEMPTS,
                type(error).__name__,
                delay,
            )
            time.sleep(delay)

    raise RuntimeError("OpenAI failed") from last_error


def _generate_with_gemini(
    prompt: str,
    transaction_id: str,
    logger,
) -> str:
    """Generate a fallback answer using Google Gemini."""

    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    logger.info(
        "Calling fallback LLM | Provider: Google Gemini | Model: %s",
        GEMINI_MODEL,
    )

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    answer = response.text

    if not answer or not answer.strip():
        raise RuntimeError("Gemini returned an empty answer")

    logger.info("Fallback LLM succeeded | Provider: Google Gemini")
    return answer.strip()


def generate_answer(
    question: str,
    context: str,
    transaction_id: str,
) -> str:
    """
    Try OpenAI first. Retry temporary errors, then fall back to Gemini.

    Raises RuntimeError if neither provider can generate an answer.
    """

    logger = get_transaction_logger(__name__, transaction_id)

    if not question or not question.strip():
        raise ValueError("Question cannot be empty")

    if not context or not context.strip():
        logger.warning("No context available; skipping LLM calls")
        return (
            "I couldn't find relevant information in the available "
            "documents to answer your question."
        )

    prompt = _build_prompt(question.strip(), context.strip())

    # Provider 1: OpenAI
    try:
        answer = _generate_with_openai(
            prompt=prompt,
            transaction_id=transaction_id,
            logger=logger,
        )

        logger.info("Answer generated | Provider: OpenAI")
        logger.info("LLM response: %s", answer)
        return answer

    except Exception:
        logger.exception(
            "OpenAI provider unavailable; switching to Google Gemini"
        )

    # Provider 2: Google Gemini
    try:
        answer = _generate_with_gemini(
            prompt=prompt,
            transaction_id=transaction_id,
            logger=logger,
        )

        logger.info("Answer generated | Provider: Google Gemini")
        logger.info("LLM response: %s", answer)
        return answer

    except Exception as gemini_error:
        logger.exception("Fallback provider failed | Provider: Google Gemini")

        raise RuntimeError(
            "All configured LLM providers failed. Please try again later."
        ) from gemini_error
