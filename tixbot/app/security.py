import base64
import hashlib
import hmac
import time


def sign_admin_link(secret: str, raffle_code: str, tg_id: int, ttl_seconds: int = 24 * 3600) -> str:
    exp = int(time.time()) + ttl_seconds
    msg = f"{raffle_code}:{tg_id}:{exp}".encode()
    sig = hmac.new(secret.encode(), msg, hashlib.sha256).digest()
    tok = base64.urlsafe_b64encode(sig).decode().rstrip("=")
    return f"{raffle_code}.{tg_id}.{exp}.{tok}"


def verify_admin_link(secret: str, token: str) -> tuple[str, int]:
    parts = token.split(".")
    if len(parts) != 4:
        raise ValueError("bad token")
    raffle_code, tg_id_s, exp_s, sig = parts
    tg_id = int(tg_id_s)
    exp = int(exp_s)
    if exp < int(time.time()):
        raise ValueError("expired")
    msg = f"{raffle_code}:{tg_id}:{exp}".encode()
    expected = hmac.new(secret.encode(), msg, hashlib.sha256).digest()
    expected_sig = base64.urlsafe_b64encode(expected).decode().rstrip("=")
    if not hmac.compare_digest(expected_sig, sig):
        raise ValueError("bad signature")
    return raffle_code, tg_id
