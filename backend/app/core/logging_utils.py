import logging


def get_transaction_logger(name: str, transaction_id: str):
    logger = logging.getLogger(name)
    return logging.LoggerAdapter(
        logger,
        {"transaction_id": transaction_id}
    )