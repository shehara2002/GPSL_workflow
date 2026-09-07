import base64
import hashlib
import hmac
import json
import time
from typing import Optional, Dict, Any
import bcrypt
from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, stored_password: Optional[str]) -> bool:
    """
    Verify a password against stored password.
    Supports bcrypt hash and falls back to plain text comparison for legacy rows.
    """
    if not stored_password:
        return False

    # Check if stored_password is a valid bcrypt hash format
    if stored_password.startswith("$2b$") or stored_password.startswith("$2a$"):
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                stored_password.encode("utf-8")
            )
        except Exception:
            return False

    # Fallback for plain text legacy entries
    return hmac.compare_digest(plain_password, stored_password)


def create_session_token(user_id: int, email: str, expires_in_seconds: Optional[int] = None) -> str:
    """
    Creates an HMAC-SHA256 signed session token containing user_id, email, and expiration time.
    """
    if expires_in_seconds is None:
        expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    payload = {
        "sub": user_id,
        "email": email,
        "exp": int(time.time()) + expires_in_seconds,
        "iat": int(time.time())
    }

    payload_json = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode('utf-8').rstrip('=')

    signature = hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        payload_b64.encode('utf-8'),
        hashlib.sha256
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')

    return f"{payload_b64}.{sig_b64}"


def verify_session_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies an HMAC-SHA256 signed session token. Returns payload dict if valid and unexpired, else None.
    """
    try:
        parts = token.split('.')
        if len(parts) != 2:
            return None

        payload_b64, sig_b64 = parts

        # Verify signature
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode('utf-8'),
            payload_b64.encode('utf-8'),
            hashlib.sha256
        ).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode('utf-8').rstrip('=')

        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            return None

        # Decode payload with padding
        padding = '=' * (4 - (len(payload_b64) % 4)) if len(payload_b64) % 4 != 0 else ''
        payload_json = base64.urlsafe_b64decode((payload_b64 + padding).encode('utf-8'))
        payload = json.loads(payload_json.decode('utf-8'))

        # Check expiration
        if payload.get("exp", 0) < int(time.time()):
            return None

        return payload
    except Exception:
        return None
