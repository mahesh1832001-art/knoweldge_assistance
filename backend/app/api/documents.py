
import logging
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    Query,
    status,
)
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.repositories import list_documents
from app.schemas.document import DocumentCreate, DocumentResponse
from app.services.ingestion_service import ingest_document


router = APIRouter(prefix="/documents", tags=["Documents"])

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".pdf", ".txt"}

BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BASE_DIR / "uploads"


def extract_text(file_path: Path, extension: str) -> str:
    """Extract and validate text from a PDF or TXT file."""

    try:
        if extension == ".txt":
            text = file_path.read_text(encoding="utf-8-sig")

        elif extension == ".pdf":
            reader = PdfReader(str(file_path), strict=True)

            if not reader.pages:
                raise ValueError("The PDF file contains no pages.")

            text = "\n".join(
                page.extract_text() or ""
                for page in reader.pages
            )

        else:
            raise ValueError(
                "Only PDF and TXT files are supported."
            )

    except UnicodeDecodeError as error:
        raise ValueError(
            "The TXT file must contain valid UTF-8 text."
        ) from error

    except PdfReadError as error:
        raise ValueError(
            "The PDF file is invalid or corrupted."
        ) from error

    text = text.strip()

    if not text:
        raise ValueError(
            "The file is empty or contains no readable text. "
            "Scanned PDFs require OCR, which is not supported."
        )

    return text


@router.post("", status_code=status.HTTP_201_CREATED)
def add_document(
    data: DocumentCreate,
    db: Session = Depends(get_db),
):
    """Existing JSON endpoint — preserved."""

    try:
        document = ingest_document(
            db=db,
            title=data.title,
            content=data.content,
        )

        return {
            "document_id": document.id,
            "title": document.title,
            "status": "indexed",
        }

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    except Exception as error:
        logger.exception("JSON document ingestion failed")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document ingestion failed",
        ) from error


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Validate, save, extract, and ingest a PDF/TXT upload."""

    transaction_id = getattr(
        request.state,
        "trans_id",
        "missing-transaction-id",
    )

    original_name = Path(file.filename or "").name
    extension = Path(original_name).suffix.lower()

    if not original_name or extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF and TXT files are supported.",
        )

    safe_transaction_id = "".join(
        character
        for character in str(transaction_id)
        if character.isalnum() or character in ("-", "_")
    ) or "unknown"

    # Save the original file with its transaction ID.
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    safe_filename = f"{safe_transaction_id}_{original_name}"
    file_path = UPLOAD_DIR / safe_filename

    try:
        # Read one byte beyond the limit to detect oversized files.
        content_bytes = await file.read(MAX_FILE_SIZE + 1)

        if not content_bytes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The uploaded file is empty.",
            )

        if len(content_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size must not exceed 10 MB.",
            )

        # Validate basic file signatures.
        if extension == ".pdf":
            if not content_bytes.startswith(b"%PDF-"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="The uploaded file is not a valid PDF.",
                )

        elif extension == ".txt":
            try:
                content_bytes.decode("utf-8-sig")
            except UnicodeDecodeError as error:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="The TXT file must use UTF-8 encoding.",
                ) from error

        # Save the uploaded file before extracting its text.
        file_path.write_bytes(content_bytes)

        text = extract_text(file_path, extension)

        # Reuse the existing MySQL and ChromaDB ingestion process.
        document = ingest_document(
            db=db,
            title=Path(original_name).stem[:255],
            content=text,
        )

        logger.info(
            "File uploaded and indexed: transaction_id=%s document_id=%s",
            transaction_id,
            document.id,
        )

        return {
            "document_id": document.id,
            "title": document.title,
            "status": "indexed",
            "message": "Document uploaded and indexed successfully.",
            "transaction_id": transaction_id,
        }

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    except Exception as error:
        logger.exception(
            "File ingestion failed: transaction_id=%s",
            transaction_id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document ingestion failed",
        ) from error

    finally:
        await file.close()


@router.get("", response_model=list[DocumentResponse])
def get_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List uploaded and indexed documents."""

    return list_documents(db, skip=skip, limit=limit)
