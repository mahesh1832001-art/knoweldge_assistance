
import uuid


def generate_transaction_id() -> str:
    return uuid.uuid4().hex
