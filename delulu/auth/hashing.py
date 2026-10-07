import hashlib
import os
import secrets

def hash_password(password: str) -> str:
    """Hashes a password with a cryptographically secure random salt using PBKDF2 HMAC-SHA256."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations=100000
    )
    return f"{salt}:{key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored salt and hash."""
    try:
        salt, stored_hash = hashed_password.split(":")
        new_key = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations=100000
        )
        return secrets.compare_digest(new_key.hex(), stored_hash)
    except Exception:
        return False
