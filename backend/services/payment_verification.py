import hashlib
import hmac


def verify_payment_signature(order_id: str, payment_id: str, signature: str, key_secret: str | None) -> bool:
    if not all((order_id, payment_id, signature, key_secret)):
        return False
    expected = hmac.new(key_secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
