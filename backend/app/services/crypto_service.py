"""Field-level encryption for stored conversation content.

Uses AES-GCM with the configured 32-byte key. Legacy plaintext rows are read
transparently, so enabling this never loses existing data. New writes are always
encrypted.
"""

import base64
import hashlib
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

PREFIX = "enc:v1:"
PLACEHOLDERS = ("change-me", "change-this")


class CryptoService:
    def __init__(self, key: Optional[str] = None):
        raw = key if key is not None else settings.encryption_key
        self.key_is_secure = False
        try:
            decoded = base64.b64decode(raw, validate=True)
            if len(decoded) == 32:
                self._key = decoded
                self.key_is_secure = not any(p in raw.lower() for p in PLACEHOLDERS)
            else:
                raise ValueError
        except Exception:
            # Development fallback. Production must supply a real base64 key;
            # deployment preflight flags this as a blocker.
            self._key = hashlib.sha256((raw or "iam-dev-key").encode("utf-8")).digest()
        self._aead = AESGCM(self._key)

    def encrypt(self, text: Optional[str]) -> str:
        if text is None:
            return ""
        if str(text).startswith(PREFIX):
            return str(text)
        nonce = os.urandom(12)
        ciphertext = self._aead.encrypt(nonce, str(text).encode("utf-8"), None)
        return PREFIX + base64.b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, value: Optional[str]) -> str:
        if value is None:
            return ""
        text = str(value)
        if not text.startswith(PREFIX):
            return text  # legacy plaintext
        try:
            blob = base64.b64decode(text[len(PREFIX):], validate=True)
            nonce, ciphertext = blob[:12], blob[12:]
            return self._aead.decrypt(nonce, ciphertext, None).decode("utf-8")
        except Exception:
            return "[unable to decrypt message]"


crypto = CryptoService()
