
from pydantic import BaseModel, ConfigDict, Field


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class SourceResponse(BaseModel):
    document_id: int | None = None
    chunk_id: str | None = None
    title: str
    content: str


class QuestionResponse(BaseModel):
    answer: str
    sources: list[SourceResponse] = []
