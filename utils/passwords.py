"""Hash y verificación de contraseñas con scrypt de la librería estándar.

Formato guardado: ``scrypt$n$r$p$sal_hex$hash_hex``. Cada contraseña lleva su
propia sal aleatoria, así dos usuarios con la misma clave no comparten hash.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SALT_BYTES = 16
KEY_BYTES = 32
MIN_LENGTH = 4


def hash_password(password: str) -> str:
    if len(password) < MIN_LENGTH:
        raise ValueError(f"La contraseña debe tener al menos {MIN_LENGTH} caracteres.")
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _derive(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = _derive(password, bytes.fromhex(salt_hex), int(n), int(r), int(p))
        return hmac.compare_digest(digest, bytes.fromhex(digest_hex))
    except (ValueError, TypeError):
        return False


def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=KEY_BYTES)
