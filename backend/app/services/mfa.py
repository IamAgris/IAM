"""WebAuthn passkey verification and TOTP MFA for website credentials.

IAM does not manufacture passkeys: the browser/platform authenticator creates
them. IAM stores the public key and verifies signed assertions. TOTP secrets
and recovery-code hashes are encrypted/hashed at rest; secrets are shown once.
"""

import base64
import hashlib
import hmac
import json
import secrets
import struct
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mfa import PasskeyCredential, TotpEnrollment, WebAuthnChallenge
from app.models.security import AuditEvent
from app.services.creatorapproval_service import CreatorApprovalService
from app.services.crypto_service import crypto

REGISTER_ACTION = "webauthn.register"
ASSERT_ACTION = "webauthn.assert"
TOTP_ENROLL_ACTION = "totp.enroll"
CHALLENGE_TTL_SECONDS = 300
TOTP_PERIOD = 30
TOTP_DIGITS = 6


class MFAError(PermissionError):
    """Raised when an MFA operation fails policy or verification."""


def totp_code(secret_b32: str, when: Optional[datetime] = None) -> str:
    """RFC 6238 TOTP using SHA-1, 6 digits, 30-second period."""
    padded = secret_b32 + "=" * ((8 - len(secret_b32) % 8) % 8)
    key = base64.b32decode(padded, casefold=True)
    timestamp = (when or datetime.now(timezone.utc)).timestamp()
    counter = int(timestamp // TOTP_PERIOD)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(value % (10**TOTP_DIGITS)).zfill(TOTP_DIGITS)


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


class MFAService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _authority(self, action: str, target: str) -> Dict[str, Any]:
        authority = await CreatorApprovalService(self.db).check_authorization(
            action, requested_level="3", target_ref=target
        )
        if not authority.get("authorized"):
            raise MFAError(f"signed Creator authorization required for {action}")
        return authority

    async def _credential_id(self, website_credential_id: str) -> UUID:
        try:
            return UUID(str(website_credential_id))
        except (ValueError, TypeError) as exc:
            raise MFAError("invalid website credential id") from exc

    async def _challenge(self, challenge_id: str, purpose: str) -> WebAuthnChallenge:
        try:
            identifier = UUID(str(challenge_id))
        except (ValueError, TypeError) as exc:
            raise MFAError("invalid challenge id") from exc
        result = await self.db.execute(select(WebAuthnChallenge))
        row = next(
            (item for item in result.scalars().all() if item.id == identifier),
            None,
        )
        if not row or row.consumed_at or row.purpose != purpose:
            raise MFAError("challenge is unknown, consumed or of the wrong purpose")
        expires = row.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires <= datetime.now(timezone.utc):
            raise MFAError("challenge has expired")
        return row

    async def _audit(self, actor: str, action: str, details: Dict[str, Any]) -> None:
        self.db.add(
            AuditEvent(event_type="mfa_action", actor=actor, target=action, details=details)
        )

    # --- WebAuthn -------------------------------------------------------------

    async def begin_registration(
        self, website_credential_id: str, rp_id: str, actor: str
    ) -> Dict[str, Any]:
        if not rp_id:
            raise MFAError("rp_id is required")
        target = str(await self._credential_id(website_credential_id))
        await self._authority(REGISTER_ACTION, target)
        challenge = secrets.token_urlsafe(32)
        row = WebAuthnChallenge(
            website_credential_id=UUID(target),
            purpose="register",
            challenge=challenge,
            rp_id=rp_id,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=CHALLENGE_TTL_SECONDS),
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit(actor, "webauthn_registration_started", {"rp_id": rp_id})
        await self.db.commit()
        return {
            "challenge_id": str(row.id),
            "challenge": challenge,
            "rp_id": rp_id,
            "expires_in_seconds": CHALLENGE_TTL_SECONDS,
        }

    async def complete_registration(
        self,
        challenge_id: str,
        credential_id: str,
        public_key_pem: str,
        actor: str,
    ) -> Dict[str, Any]:
        challenge = await self._challenge(challenge_id, "register")
        try:
            key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        except Exception as exc:
            raise MFAError("public_key_pem is not a valid public key") from exc
        if not isinstance(key, (ec.EllipticCurvePublicKey, rsa.RSAPublicKey)):
            raise MFAError("only EC and RSA passkeys are supported")
        if not credential_id:
            raise MFAError("credential_id is required")
        existing = await self.db.execute(
            select(PasskeyCredential).where(PasskeyCredential.credential_id == credential_id)
        )
        if existing.scalar_one_or_none():
            raise MFAError("passkey credential_id is already registered")
        passkey = PasskeyCredential(
            website_credential_id=challenge.website_credential_id,
            credential_id=credential_id,
            public_key_pem=public_key_pem,
            rp_id=challenge.rp_id,
            is_active=True,
        )
        self.db.add(passkey)
        challenge.consumed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self.db.flush()
        await self._audit(actor, "webauthn_passkey_registered", {"rp_id": challenge.rp_id})
        await self.db.commit()
        return {
            "id": str(passkey.id),
            "credential_id": credential_id,
            "rp_id": challenge.rp_id,
        }

    async def begin_authentication(self, passkey_id: str, actor: str) -> Dict[str, Any]:
        try:
            identifier = UUID(str(passkey_id))
        except (ValueError, TypeError) as exc:
            raise MFAError("invalid passkey id") from exc
        result = await self.db.execute(
            select(PasskeyCredential).where(PasskeyCredential.id == identifier)
        )
        passkey = result.scalar_one_or_none()
        if not passkey or not passkey.is_active:
            raise MFAError("passkey is unknown or inactive")
        challenge = WebAuthnChallenge(
            website_credential_id=passkey.website_credential_id,
            purpose="authenticate",
            challenge=secrets.token_urlsafe(32),
            rp_id=passkey.rp_id,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=CHALLENGE_TTL_SECONDS),
        )
        self.db.add(challenge)
        await self.db.flush()
        await self.db.commit()
        return {
            "challenge_id": str(challenge.id),
            "challenge": challenge.challenge,
            "rp_id": passkey.rp_id,
        }

    async def verify_assertion(
        self,
        challenge_id: str,
        credential_id: str,
        authenticator_data_b64: str,
        client_data_json: str,
        signature_b64: str,
        actor: str,
    ) -> Dict[str, Any]:
        challenge = await self._challenge(challenge_id, "authenticate")
        try:
            client = json.loads(client_data_json)
        except (ValueError, TypeError) as exc:
            raise MFAError("client_data_json is invalid") from exc
        if client.get("challenge") != challenge.challenge:
            raise MFAError("challenge mismatch in client data")
        if client.get("type") != "webauthn.get":
            raise MFAError("client data is not a WebAuthn assertion")
        result = await self.db.execute(
            select(PasskeyCredential).where(
                PasskeyCredential.credential_id == credential_id,
                PasskeyCredential.website_credential_id == challenge.website_credential_id,
            )
        )
        passkey = result.scalar_one_or_none()
        if not passkey or not passkey.is_active:
            raise MFAError("passkey is unknown or inactive")
        try:
            auth_data = base64.b64decode(authenticator_data_b64, validate=True)
            signature = base64.b64decode(signature_b64, validate=True)
            key = serialization.load_pem_public_key(passkey.public_key_pem.encode("utf-8"))
            client_hash = hashlib.sha256(client_data_json.encode("utf-8")).digest()
            signed_data = auth_data + client_hash
            if isinstance(key, ec.EllipticCurvePublicKey):
                key.verify(signature, signed_data, ec.ECDSA(hashes.SHA256()))
            elif isinstance(key, rsa.RSAPublicKey):
                key.verify(signature, signed_data, padding.PKCS1v15(), hashes.SHA256())
            else:
                raise MFAError("unsupported passkey key type")
        except InvalidSignature as exc:
            raise MFAError("passkey assertion signature is invalid") from exc
        except (ValueError, TypeError) as exc:
            raise MFAError("assertion data is malformed") from exc
        challenge.consumed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        passkey.last_used_at = challenge.consumed_at
        await self._audit(
            actor, "webauthn_assertion_verified", {"credential_id": credential_id}
        )
        await self.db.commit()
        return {"verified": True, "credential_id": credential_id}

    async def passkeys(self, website_credential_id: str) -> List[Dict[str, Any]]:
        target = await self._credential_id(website_credential_id)
        result = await self.db.execute(
            select(PasskeyCredential).where(
                PasskeyCredential.website_credential_id == target
            )
        )
        return [
            {
                "id": str(row.id),
                "credential_id": row.credential_id,
                "rp_id": row.rp_id,
                "is_active": bool(row.is_active),
                "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
            }
            for row in result.scalars().all()
        ]

    # --- TOTP ----------------------------------------------------------------

    async def enroll_totp(
        self, website_credential_id: str, issuer: str, account: str, actor: str
    ) -> Dict[str, Any]:
        target = str(await self._credential_id(website_credential_id))
        await self._authority(TOTP_ENROLL_ACTION, target)
        secret = base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")
        recovery_codes = [secrets.token_hex(5).upper() for _ in range(8)]
        row = TotpEnrollment(
            website_credential_id=UUID(target),
            secret_ciphertext=crypto.encrypt(secret),
            issuer=issuer or "IAM",
            account=account or "iam",
            recovery_hashes=[_hash_code(code) for code in recovery_codes],
            is_active=True,
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit(actor, "totp_enrolled", {})
        await self.db.commit()
        uri = (
            f"otpauth://totp/{row.issuer}:{row.account}?"
            f"secret={secret}&issuer={row.issuer}&algorithm=SHA1&digits=6&period=30"
        )
        return {
            "id": str(row.id),
            "otpauth_uri": uri,
            "recovery_codes": recovery_codes,
            "note": "shown once; store securely",
        }

    async def verify_totp(
        self, website_credential_id: str, code: str, actor: str
    ) -> Dict[str, Any]:
        target = await self._credential_id(website_credential_id)
        result = await self.db.execute(
            select(TotpEnrollment).where(
                TotpEnrollment.website_credential_id == target,
                TotpEnrollment.is_active.is_(True),
            )
        )
        enrollment = result.scalar_one_or_none()
        if not enrollment:
            raise MFAError("no active TOTP enrollment")
        now = datetime.now(timezone.utc)
        secret = crypto.decrypt(enrollment.secret_ciphertext)  # type: ignore[arg-type]
        valid = any(
            hmac.compare_digest(totp_code(secret, now + timedelta(seconds=step * TOTP_PERIOD)), code)
            for step in (-1, 0, 1)
        )
        used_recovery = False
        if not valid:
            digest = _hash_code(code)
            hashes = list(enrollment.recovery_hashes or [])
            if digest in hashes:
                hashes.remove(digest)
                enrollment.recovery_hashes = hashes  # type: ignore[assignment]
                used_recovery = True
                valid = True
        if not valid:
            raise MFAError("TOTP code is invalid")
        await self._audit(actor, "totp_verified", {"recovery_code": used_recovery})
        await self.db.commit()
        return {"verified": True, "recovery_code_used": used_recovery}

    async def disable_totp(self, website_credential_id: str, actor: str) -> Dict[str, Any]:
        target = str(await self._credential_id(website_credential_id))
        await self._authority(TOTP_ENROLL_ACTION, target)
        result = await self.db.execute(
            select(TotpEnrollment).where(
                TotpEnrollment.website_credential_id == UUID(target)
            )
        )
        enrollment = result.scalar_one_or_none()
        if not enrollment:
            raise MFAError("no TOTP enrollment")
        enrollment.is_active = False  # type: ignore[assignment]
        await self._audit(actor, "totp_disabled", {})
        await self.db.commit()
        return {"disabled": True}
