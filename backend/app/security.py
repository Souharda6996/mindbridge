"""Encryption at rest for anything a user writes (chat text, journal notes).

Uses Fernet (AES-128-CBC + HMAC-SHA256) from the `cryptography` package.
The key is generated on first run and stored in backend/data/secret.key.
Deleting that file makes all stored text unreadable (crypto-shredding).
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from . import config

_fernet: Fernet | None = None


def _get() -> Fernet:
    global _fernet
    if _fernet is None:
        if not config.KEY_PATH.exists():
            config.KEY_PATH.write_bytes(Fernet.generate_key())
        _fernet = Fernet(config.KEY_PATH.read_bytes())
    return _fernet


def encrypt(text: str | None) -> str | None:
    if text is None:
        return None
    return _get().encrypt(text.encode("utf-8")).decode("ascii")


def decrypt(token: str | None) -> str | None:
    if token is None:
        return None
    try:
        return _get().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return "[unreadable - encryption key changed]"


def reset_key() -> None:
    """Used by 'delete all my data': rotate the key so old ciphertext is gone."""
    global _fernet
    config.KEY_PATH.write_bytes(Fernet.generate_key())
    _fernet = None
