"""
api/auth.py
===========
JWT verification decorator for Flask routes.
Validates Supabase-issued JWTs using the RS256 JWK public key.
"""

import logging
import jwt
from jwt.algorithms import RSAAlgorithm
from functools import wraps
from flask import request, jsonify
import config

logger = logging.getLogger(__name__)

# Convert JWK JSON → RSA public key object once at import time
_public_key = None
if config.SUPABASE_JWT_PUBLIC_KEY:
    try:
        _public_key = RSAAlgorithm.from_jwk(config.SUPABASE_JWT_PUBLIC_KEY)
    except Exception as e:
        logger.error("Failed to parse SUPABASE_JWT_PUBLIC_KEY as JWK: %s", e)


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
