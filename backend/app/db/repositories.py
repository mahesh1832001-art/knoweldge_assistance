
from sqlalchemy.orm import Session

from app.db.models import Document
from app.schemas.document import DocumentCreate


def create_document(db: Session, data: DocumentCreate) -> Document:
    document = Document(
        title=data.title.strip(),
        content=data.content.strip(),
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


def list_documents(db: Session, skip: int = 0, limit: int = 10):
    return (
        db.query(Document)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
