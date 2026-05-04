"""
api/routes/users.py
====================
REST endpoints for Users resource.

GET   /api/users       – list all users
POST  /api/users       – create user
GET   /api/users/<id>  – get single user
"""

from flask import Blueprint, jsonify, request, current_app

users_bp = Blueprint("users", __name__)


def _db():
    return current_app.config["DB"]


@users_bp.route("/users", methods=["GET"])
def list_users():
    users = _db().get_users()
    return jsonify({"count": len(users), "users": users})


@users_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id: int):
    user = _db().get_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user)


@users_bp.route("/users", methods=["POST"])
def create_user():
    data = request.get_json(force=True)
    required = ["name", "email"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400
    try:
        new_id = _db().insert_user(data)
        return jsonify({"id": new_id, "message": "User created"}), 201
    except Exception as exc:
        return jsonify({"error": str(exc)}), 409
