import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import jwt
from jwt import PyJWKClient
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
    PyJWTError,
)

from app.core.config import settings
from app.core.exceptions import UnauthorizedException

logger = logging.getLogger("flowstate.security")

# Cached JWKS client for asymmetric key verification (ES256, RS256)
_jwks_client: Optional[PyJWKClient] = None


def get_jwks_client() -> Optional[PyJWKClient]:
    """Retrieves or initializes the PyJWKClient using the configured Supabase URL."""
    global _jwks_client
    if _jwks_client is None and settings.SUPABASE_URL and settings.SUPABASE_URL.strip():
        jwks_url = f"{settings.SUPABASE_URL.strip().rstrip('/')}/auth/v1/.well-known/jwks.json"
        try:
            _jwks_client = PyJWKClient(jwks_url, cache_keys=True, max_cached_keys=10)
        except Exception as e:
            logger.warning("Could not initialize PyJWKClient for %s: %s", jwks_url, e)
            _jwks_client = None
    return _jwks_client


def decode_supabase_jwt(token: str) -> Dict[str, Any]:
    """
    Decodes and cryptographically verifies a Supabase Auth JWT token.
    Supports both:
    1. Modern Supabase Asymmetric ECDSA / RSA signatures (ES256 / RS256 via JWKS).
    2. Legacy / local Symmetric HMAC-SHA256 signatures (HS256 via JWT secret).

    Validates signature, expiration (exp), audience (aud), and subject (sub).
    
    Raises:
        UnauthorizedException: with specific error codes for expired, invalid,
        or malformed tokens.
    """
    if not token or not token.strip():
        raise UnauthorizedException("Empty or missing authentication token.", code="MISSING_TOKEN")

    stripped_token = token.strip()

    # 1. Inspect unverified header to detect algorithm and Key ID (kid)
    try:
        header = jwt.get_unverified_header(stripped_token)
    except Exception as e:
        logger.warning("Malformed JWT header: %s", e)
        raise UnauthorizedException("Could not validate authentication token.", code="INVALID_TOKEN") from e

    alg = header.get("alg", "HS256")
    kid = header.get("kid")

    # 2. Configure verification options
    options: Dict[str, Any] = {
        "verify_signature": True,
        "verify_exp": True,
        "require": ["exp", "sub"],
    }

    audience = settings.SUPABASE_JWT_AUDIENCE if settings.SUPABASE_JWT_AUDIENCE else None
    if not audience:
        options["verify_aud"] = False

    issuer = None
    if settings.SUPABASE_URL and settings.SUPABASE_URL.strip():
        issuer = f"{settings.SUPABASE_URL.strip().rstrip('/')}/auth/v1"
        # Only enforce issuer if the token actually provides one
        options["verify_iss"] = False
    else:
        options["verify_iss"] = False

    # 3. Resolve signing key based on algorithm
    signing_key: Any = None
    algorithms: List[str] = [alg]

    # Asymmetric verification via Supabase JWKS (ES256, RS256)
    if (kid or alg in ["ES256", "RS256"]) and (jwks_client := get_jwks_client()):
        try:
            jwk = jwks_client.get_signing_key_from_jwt(stripped_token)
            signing_key = jwk.key
            algorithms = [alg]
        except Exception as e:
            logger.debug("JWKS resolution failed or not found: %s", e)
            # If asymmetric key lookup fails, fall back to symmetric secret
            signing_key = settings.jwt_secret
            algorithms = [alg, "HS256"]
    else:
        # Symmetric HMAC verification (HS256)
        signing_key = settings.jwt_secret
        algorithms = [alg, settings.SUPABASE_JWT_ALGORITHM, "HS256"]

    try:
        payload = jwt.decode(
            stripped_token,
            signing_key,
            algorithms=algorithms,
            audience=audience,
            issuer=issuer,
            options=options,
        )
        return payload
    except ExpiredSignatureError as e:
        logger.warning("JWT verification failed: Token has expired.")
        raise UnauthorizedException("Authentication token has expired.", code="TOKEN_EXPIRED") from e
    except InvalidSignatureError as e:
        logger.warning("JWT verification failed: Invalid signature.")
        raise UnauthorizedException("Invalid token signature.", code="INVALID_SIGNATURE") from e
    except InvalidAudienceError as e:
        logger.warning("JWT verification failed: Invalid audience.")
        raise UnauthorizedException("Invalid token audience.", code="INVALID_AUDIENCE") from e
    except InvalidIssuerError as e:
        logger.warning("JWT verification failed: Invalid issuer.")
        raise UnauthorizedException("Invalid token issuer.", code="INVALID_ISSUER") from e
    except (DecodeError, PyJWTError) as e:
        logger.warning("JWT verification failed: Malformed or undecodable token: %s", type(e).__name__)
        raise UnauthorizedException("Could not validate authentication token.", code="INVALID_TOKEN") from e


def create_jwt_token(
    sub: str | uuid.UUID,
    email: str,
    role: str = "authenticated",
    exp_delta: Optional[timedelta] = None,
    aud: Optional[str] = "authenticated",
    iss: Optional[str] = None,
    secret: Optional[str] = None,
    algorithm: Optional[str] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Utility to mint JWT tokens matching Supabase Auth specifications.
    Used for local testing, integration workflows, and mock environments.
    """
    now = datetime.now(timezone.utc)
    delta = exp_delta if exp_delta is not None else timedelta(hours=1)
    exp = now + delta

    payload: Dict[str, Any] = {
        "sub": str(sub),
        "email": email,
        "role": role,
        "aud": aud or settings.SUPABASE_JWT_AUDIENCE or "authenticated",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    if iss or settings.SUPABASE_URL:
        payload["iss"] = iss or f"{settings.SUPABASE_URL.strip().rstrip('/')}/auth/v1"

    if extra_claims:
        payload.update(extra_claims)

    signing_secret = secret or settings.jwt_secret
    signing_algo = algorithm or settings.SUPABASE_JWT_ALGORITHM

    return jwt.encode(payload, signing_secret, algorithm=signing_algo)
