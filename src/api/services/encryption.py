"""Encryption utilities for API key storage.

Uses Fernet symmetric encryption to protect API keys at rest.
The encryption key is derived from the application's configured secret.
"""

import base64
import hashlib

from cryptography.fernet import Fernet

from src.shared.config import APISettings


def _get_fernet() -> Fernet:
    """Create a Fernet instance using the configured encryption key.

    Derives a 32-byte key from the ENCRYPTION_KEY setting using SHA-256,
    then base64-encodes it for Fernet compatibility.
    """
    settings = APISettings()
    raw_key = settings.encryption_key.encode()
    # Derive a 32-byte key via SHA-256
    derived = hashlib.sha256(raw_key).digest()
    fernet_key = base64.urlsafe_b64encode(derived)
    return Fernet(fernet_key)


def encrypt_api_key(plaintext: str) -> str:
    """Encrypt an API key for database storage.

    Args:
        plaintext: The raw API key string.

    Returns:
        The encrypted key as a base64-encoded string.
    """
    fernet = _get_fernet()
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    """Decrypt an API key retrieved from the database.

    Args:
        ciphertext: The encrypted key string from the database.

    Returns:
        The original plaintext API key.
    """
    fernet = _get_fernet()
    return fernet.decrypt(ciphertext.encode()).decode()
