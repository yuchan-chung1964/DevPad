"""Identify the caller from a bearer JWT, rate-limit them, and expose them as `CurrentUser`."""
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError

from app import config, models
from app.db import DB
from app.ratelimit import limiter

_bearer = HTTPBearer(auto_error=False)
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(config.JWT_JWKS_URL, cache_keys=True)


def _decode(token: str) -> dict:
    if config.JWT_JWKS_URL:
        key, algorithms = _jwks_client().get_signing_key_from_jwt(token).key, ["RS256", "ES256"]
    elif config.JWT_SECRET:
        key, algorithms = config.JWT_SECRET, ["HS256"]
    else:
        raise HTTPException(503, "Authentication is not configured")
    return jwt.decode(
        token,
        key,
        algorithms=algorithms,  # fixed list: the token's own `alg` header is never trusted
        audience=config.JWT_AUDIENCE,
        issuer=config.JWT_ISSUER,
        options={"require": ["exp", "sub"], "verify_aud": bool(config.JWT_AUDIENCE)},
    )


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def current_user(
    request: Request,
    db: DB,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> models.User:
    # Throttle by IP before doing any token work, so bad-token floods are cheap to reject.
    if creds is None:
        limiter.check(f"anon:{_client_ip(request)}", config.RATE_LIMIT_ANON)
        raise HTTPException(401, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = _decode(creds.credentials)
    except jwt.PyJWKClientConnectionError:
        raise HTTPException(503, "Could not reach the identity provider")
    except jwt.InvalidTokenError:
        limiter.check(f"anon:{_client_ip(request)}", config.RATE_LIMIT_ANON)
        raise HTTPException(401, "Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})

    user_id = str(claims["sub"])
    if request.method in _SAFE_METHODS:
        limiter.check(f"user:{user_id}:read", config.RATE_LIMIT_READ)
    else:
        limiter.check(f"user:{user_id}:write", config.RATE_LIMIT_WRITE)

    user = db.get(models.User, user_id)
    if user is None:  # first request from this identity
        try:
            with db.begin_nested():
                user = models.User(id=user_id)
                db.add(user)
        except IntegrityError:  # lost a race with a concurrent first request
            user = db.get(models.User, user_id)
    return user


CurrentUser = Annotated[models.User, Depends(current_user)]
