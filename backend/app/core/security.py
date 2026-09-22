"""
TRINETRA Security Utilities
============================

Central security utilities for the backend.

Current prototype:
    - Password hashing
    - JWT access tokens
    - Token decoding
    - Basic authentication helpers

Future:
    - Role-based access control
    - Investigator permissions
    - Admin permissions
    - Audit logging
    - Case-level authorization
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


# ============================================================
# PASSWORD HASHING
# ============================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


# ============================================================
# JWT CONFIGURATION
# ============================================================

ALGORITHM = "HS256"


# ============================================================
# PASSWORD FUNCTIONS
# ============================================================

def hash_password(
    password: str,
) -> str:
    """
    Hash a password using bcrypt.
    """

    if not password:
        raise ValueError(
            "Password cannot be empty."
        )

    return pwd_context.hash(
        password
    )


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Verify a plain-text password against
    a stored password hash.
    """

    if not plain_password:
        return False

    if not hashed_password:
        return False

    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


# ============================================================
# ACCESS TOKEN
# ============================================================

def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a JWT access token.

    Parameters
    ----------
    subject:
        User identifier.

    expires_delta:
        Optional custom expiration duration.

    extra_claims:
        Additional claims such as role or permissions.
    """

    if not subject:
        raise ValueError(
            "Token subject cannot be empty."
        )

    now = datetime.now(
        timezone.utc
    )

    if expires_delta is None:

        expires_delta = timedelta(
            minutes=(
                settings.access_token_expire_minutes
            )
        )

    expire = now + expires_delta

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
    }

    if extra_claims:

        payload.update(
            extra_claims
        )

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=ALGORITHM,
    )


# ============================================================
# DECODE TOKEN
# ============================================================

def decode_access_token(
    token: str,
) -> dict[str, Any] | None:
    """
    Decode and validate a JWT access token.

    Returns:
        Token payload if valid.
        None if invalid or expired.
    """

    if not token:
        return None

    try:

        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
        )

        return payload

    except JWTError:

        return None


# ============================================================
# GET TOKEN SUBJECT
# ============================================================

def get_token_subject(
    token: str,
) -> str | None:
    """
    Extract the subject/user ID from a JWT.
    """

    payload = decode_access_token(
        token
    )

    if not payload:
        return None

    subject = payload.get(
        "sub"
    )

    if not subject:
        return None

    return str(
        subject
    )


# ============================================================
# TOKEN VALIDATION
# ============================================================

def validate_access_token(
    token: str,
) -> bool:
    """
    Return True if the access token is valid.
    """

    payload = decode_access_token(
        token
    )

    return payload is not None


# ============================================================
# ROLE CHECK
# ============================================================

def token_has_role(
    token: str,
    required_role: str,
) -> bool:
    """
    Check whether a token contains the requested role.

    Example roles:

        investigator
        analyst
        supervisor
        administrator
    """

    if not required_role:
        return False

    payload = decode_access_token(
        token
    )

    if not payload:
        return False

    role = payload.get(
        "role"
    )

    if not role:
        return False

    return (
        str(role).lower()
        == required_role.lower()
    )


# ============================================================
# PERMISSION CHECK
# ============================================================

def token_has_permission(
    token: str,
    required_permission: str,
) -> bool:
    """
    Check whether a token contains a permission.

    Example:

        cases:read
        cases:write
        investigations:read
        investigations:write
        reports:generate
    """

    if not required_permission:
        return False

    payload = decode_access_token(
        token
    )

    if not payload:
        return False

    permissions = payload.get(
        "permissions",
        [],
    )

    if not isinstance(
        permissions,
        list,
    ):

        return False

    return required_permission in permissions