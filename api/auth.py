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
_jwk_raw = config.SUPABASE_JWT_PUBLIC_KEY
if not _jwk_raw:
    logger.error("SUPABASE_JWT_PUBLIC_KEY is empty or not set in environment")
else:
    logger.info("SUPABASE_JWT_PUBLIC_KEY found, length=%d, starts_with=%r", len(_jwk_raw), _jwk_raw[:20])
    try:
        _public_key = RSAAlgorithm.from_jwk(_jwk_raw)
        logger.info("RSA public key parsed successfully")
    except Exception as e:
        logger.error("Failed to parse SUPABASE_JWT_PUBLIC_KEY as JWK: %s | raw value starts: %r", e, _jwk_raw[:50])


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
