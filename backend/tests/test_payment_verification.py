import hashlib,hmac
from backend.services.payment_verification import verify_payment_signature
def test_valid_signature():
    sig=hmac.new(b"test_secret",b"order_test|pay_test",hashlib.sha256).hexdigest()
    assert verify_payment_signature("order_test","pay_test",sig,"test_secret")
def test_invalid_missing_and_wrong_order_are_rejected():
    assert not verify_payment_signature("order_test","pay_test","bad","test_secret")
    assert not verify_payment_signature("order_test","pay_test","","test_secret")
    sig=hmac.new(b"test_secret",b"order_test|pay_test",hashlib.sha256).hexdigest()
    assert not verify_payment_signature("other_order","pay_test",sig,"test_secret")
