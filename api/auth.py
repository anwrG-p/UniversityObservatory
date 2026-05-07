"""
api/auth.py
===========
JWT verification decorator for Flask routes.
Fetches Supabase's RS256 public key from the JWKS endpoint at startup —
no manual key management required.
"""

import json
import logging
import requests as _requests
import jwt
from jwt.algorithms import RSAAlgorithm
from functools import wraps
from flask import request, jsonify
import config

logger = logging.getLogger(__name__)


def _load_public_key():
    """Fetch the first RS256 key from Supabase's JWKS endpoint."""
    url = f"{config.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    try:
        resp = _requests.get(url, timeout=10)
        resp.raise_for_status()
        keys = resp.json().get("keys", [])
        if not keys:
            logger.error("JWKS endpoint returned no keys: %s", url)
            return None
        key = RSAAlgorithm.from_jwk(json.dumps(keys[0]))
        logger.info("RS256 public key loaded from Supabase JWKS")
        return key
    except Exception as e:
        logger.error("Failed to load JWKS from %s: %s", url, e)
        return None


_public_key = _load_public_key()


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if _public_key is None:
            logger.warning("SUPABASE_JWT_PUBLIC_KEY is not set or invalid — all authenticated routes will return 401")
            return jsonify({"error": "Unauthorized"}), 401
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized"}), 401
        token = auth_header[len("Bearer "):]
        try:
            jwt.decode(
                token,
                _public_key,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
        except jwt.PyJWTError:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated
