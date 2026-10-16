
import logging
import threading
import time
import uuid
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.config import settings


logger = logging.getLogger(__name__)

token_bucket = defaultdict(
    lambda: {
        "tokens": float(settings.ALLOWED_TOKEN_COUNT),
        "last_refill": time.monotonic(),
    }
)

bucket_lock = threading.Lock()


class RateLimiter(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        # Generate one transaction ID for every incoming request.
        transaction_id = uuid.uuid4().hex
        request.state.trans_id = transaction_id

        request_logger = logging.LoggerAdapter(
            logger,
            {"transaction_id": transaction_id},
        )

        client_ip = (
            request.client.host
            if request.client
            else "unknown"
        )

        request_logger.info(
            "Incoming request | Method: %s | Path: %s | Client: %s",
            request.method,
            request.url.path,
            client_ip,
        )

        # Apply rate limiting only to POST /ask.
        if request.method == "POST" and request.url.path == "/ask":
            allowed, retry_after = self._consume_token(client_ip)

            if not allowed:
                request_logger.warning(
                    "Rate limit exceeded | Client: %s | Retry after: %s seconds",
                    client_ip,
                    retry_after,
                )

                response = JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Please try again later.",
                        "transaction_id": transaction_id,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-Transaction-ID": transaction_id,
                    },
                )

                return response

        return await self.process_request(
            request,
            call_next,
            request_logger,
            transaction_id,
        )

    def _consume_token(self, client_ip: str):
        """
        Refill the client's token bucket and consume one token.

        Returns:
            (True, 0) when allowed.
            (False, retry_after_seconds) when rejected.
        """
        capacity = float(settings.ALLOWED_TOKEN_COUNT)
        refill_rate = float(settings.REFILL_RATE)
        now = time.monotonic()

        with bucket_lock:
            bucket = token_bucket[client_ip]

            elapsed = max(0.0, now - bucket["last_refill"])

            bucket["tokens"] = min(
                capacity,
                bucket["tokens"] + elapsed * refill_rate,
            )
            bucket["last_refill"] = now

            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                return True, 0

            if refill_rate > 0:
                retry_after = max(
                    1,
                    int((1 - bucket["tokens"]) / refill_rate) + 1,
                )
            else:
                retry_after = 60

            return False, retry_after

    async def process_request(
        self,
        request: Request,
        call_next,
        request_logger,
        transaction_id: str,
    ) -> Response:
        """Execute the request and log its status and processing duration."""

        start_time = time.perf_counter()

        try:
            response = await call_next(request)

            duration = time.perf_counter() - start_time

            request_logger.info(
                "Request completed | Status: %s | Duration: %.3f seconds",
                response.status_code,
                duration,
            )

            response.headers["X-Transaction-ID"] = transaction_id

            return response

        except Exception:
            duration = time.perf_counter() - start_time

            request_logger.exception(
                "Request failed | Duration: %.3f seconds",
                duration,
            )
            raise
