"""
Phase 26 – Enterprise Secret Encryption Service

Provides authenticated symmetric encryption (Fernet / AES) for webhook secrets,
OAuth tokens, and third-party API keys so no credentials are stored in plain text.
"""

from __future__ import annotations

import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class SecretEncryptionService:
    """
    Encrypts and decrypts sensitive integration tokens using a key derived from JWT_SECRET_KEY.
    """

    def __init__(self, master_secret: Optional[str] = None) -> None:
        raw_key = master_secret or getattr(settings, "JWT_SECRET_KEY", "default-integration-secret-key-32b")
        # Derive standard 32-byte URL-safe base64 key
        derived = hashlib.sha256(raw_key.encode("utf-8")).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(derived))

    def encrypt(self, plain_text: str) -> str:
        """Encrypts plain text secret into an authenticated ciphertext string."""
        if not plain_text:
            return ""
        return self._fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")

    def decrypt(self, cipher_text: str) -> str:
        """Decrypts authenticated ciphertext string back into plain text."""
        if not cipher_text:
            return ""
        try:
            return self._fernet.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
        except Exception as e:
            logger.error("Failed to decrypt integration secret", error=str(e))
            raise ValueError("Invalid ciphertext or corrupted encryption key.") from e
