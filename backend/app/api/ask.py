
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from openai import APIError, RateLimitError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.question import QuestionRequest, QuestionResponse
from app.services.retrieval_service import answer_question


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Questions"])


@router.post("/ask", response_model=QuestionResponse)
def ask_question(
    data: QuestionRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    transaction_id = getattr(
        request.state,
        "trans_id",
        "missing-transaction-id",
    )

    request_logger = logging.LoggerAdapter(
        logger,
        {"transaction_id": transaction_id},
    )

    question = data.question.strip()

    request_logger.info("Question endpoint called")

    if not question:
        raise HTTPException(
            status_code=422,
            detail="Question cannot be empty",
        )

    request_logger.info("Processing question: %s", question)

    try:
        result = answer_question(
            db=db,
            question=question,
            transaction_id=transaction_id,
        )

        request_logger.info("Question answered successfully")
        return result

    except RateLimitError as error:
        request_logger.exception("AI provider rate limit encountered")

        raise HTTPException(
            status_code=503,
            detail="The AI provider is temporarily rate-limited. Try again later.",
            headers={"Retry-After": "5"},
        ) from error

    except APIError as error:
        request_logger.exception("AI provider request failed")

        raise HTTPException(
            status_code=502,
            detail="The AI provider request failed",
        ) from error

    except HTTPException:
        raise

    except Exception as error:
        request_logger.exception("Question answering failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to process the question",
        ) from error
