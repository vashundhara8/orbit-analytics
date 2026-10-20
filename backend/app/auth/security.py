"""Cryptographic token generation and verification for tenant authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from backend.app.auth.models import AuthenticatedUser, TokenData, UserRole
from backend.app.config import settings


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _base64url_decode(data_str: str) -> bytes:
    padding = "=" * (4 - (len(data_str) % 4)) if len(data_str) % 4 != 0 else ""
    return base64.urlsafe_b64decode(data_str + padding)


def create_access_token(user: AuthenticatedUser) -> str:
    """Create an HMAC-SHA256 signed bearer JWT carrying verified tenant claims."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    exp = now + (settings.access_token_expire_minutes * 60)

    payload = {
        "sub": user.user_id,
        "email": user.email,
        "tenant_id": user.tenant_id,
        "role": user.role.value,
        "org_name": user.organization_name,
        "iat": now,
        "exp": exp,
    }

    header_bytes = json.dumps(header, separators=(",", ":")).encode()
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()

    encoded_header = _base64url_encode(header_bytes)
    encoded_payload = _base64url_encode(payload_bytes)

    signing_input = f"{encoded_header}.{encoded_payload}".encode()
    signature = hmac.new(
        settings.secret_key.encode(),
        signing_input,
        hashlib.sha256,
    ).digest()
    encoded_signature = _base64url_encode(signature)

    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def verify_access_token(token: str) -> TokenData | None:
    """Verify cryptographic signature, expiration, and tenant claims from bearer token."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        encoded_header, encoded_payload, encoded_signature = parts
        signing_input = f"{encoded_header}.{encoded_payload}".encode()

        expected_sig = hmac.new(
            settings.secret_key.encode(),
            signing_input,
            hashlib.sha256,
        ).digest()

        provided_sig = _base64url_decode(encoded_signature)
        if not hmac.compare_digest(expected_sig, provided_sig):
            return None

        payload_bytes = _base64url_decode(encoded_payload)
        payload = json.loads(payload_bytes.decode("utf-8"))

        now = int(time.time())
        if payload.get("exp", 0) < now:
            return None

        return TokenData(
            sub=payload["sub"],
            email=payload["email"],
            tenant_id=payload["tenant_id"],
            role=UserRole(payload["role"]),
            org_name=payload.get("org_name", settings.default_tenant_name),
            exp=payload["exp"],
        )
    except Exception:
        return None
