
import logging
import threading
from datetime import datetime
from pathlib import Path


# backend/app/core/logging_config.py -> backend/
BASE_DIR = Path(__file__).resolve().parents[2]
LOG_DIR = BASE_DIR / "logs"

_config_lock = threading.Lock()


class TransactionFormatter(logging.Formatter):
    def format(self, record):
        timestamp = datetime.now().astimezone().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        transaction_id = getattr(record, "transaction_id", "-")

        return (
            f"[{timestamp}]"
            f"[{transaction_id}] "
            f"[{record.levelname}] "
            f"{record.getMessage()}"
        )


class DailyDirectoryHandler(logging.Handler):
    def __init__(self, log_directory: Path):
        super().__init__()

        self.log_directory = Path(log_directory)
        self.current_date = None
        self.file_handler = None
        self.file_lock = threading.RLock()

    def emit(self, record):
        try:
            with self.file_lock:
                log_date = datetime.now().astimezone().date()

                if log_date != self.current_date:
                    if self.file_handler:
                        self.file_handler.close()
                        self.file_handler = None

                    directory = (
                        self.log_directory
                        / f"{log_date.year:04d}"
                        / f"{log_date.month:02d}"
                        / f"{log_date.day:02d}"
                    )

                    directory.mkdir(parents=True, exist_ok=True)

                    log_file = directory / "knowledge_assistant.log"

                    self.file_handler = logging.FileHandler(
                        log_file,
                        encoding="utf-8",
                    )
                    self.file_handler.setFormatter(self.formatter)
                    self.current_date = log_date

                self.file_handler.emit(record)

        except Exception:
            self.handleError(record)

    def close(self):
        with self.file_lock:
            if self.file_handler:
                self.file_handler.close()
                self.file_handler = None

        super().close()


def setup_logging():
    with _config_lock:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        if getattr(root_logger, "_knowledge_logging_configured", False):
            return

        formatter = TransactionFormatter()

        file_handler = DailyDirectoryHandler(LOG_DIR)
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        root_logger._knowledge_logging_configured = True

        # This startup message also creates today's log file.
        root_logger.info(
            "Logging initialized | Log directory: %s",
            LOG_DIR,
        )
