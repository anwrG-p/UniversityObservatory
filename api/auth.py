"""
api/auth.py
===========
JWT verification decorator for Flask routes.
Validates Supabase-issued JWTs using the RS256 public key.
"""

import logging
import jwt
from functools import wraps
from flask import request, jsonify
import config

logger = logging.getLogger(__name__)


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not config.SUPABASE_JWT_PUBLIC_KEY:
            logger.warning("SUPABASE_JWT_PUBLIC_KEY is not set — all authenticated routes will return 401")
            return jsonify({"error": "Unauthorized"}), 401
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized"}), 401
        token = auth_header[len("Bearer "):]
        try:
            jwt.decode(
                token,
                config.SUPABASE_JWT_PUBLIC_KEY,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
        except jwt.PyJWTError:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated
