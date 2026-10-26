
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging_config import setup_logging

setup_logging()

from app.api.documents import router as documents_router
from app.api.ask import router as ask_router
from app.middleware.rate_limiter import RateLimiter


app = FastAPI(
    title="Knowledge Assistant",
    description="Document-based question answering using RAG",
    version="1.0.0",
)

#enter backend and frontend domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimiter)

app.include_router(documents_router)
app.include_router(ask_router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}
