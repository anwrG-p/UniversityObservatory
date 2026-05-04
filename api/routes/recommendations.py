"""
api/routes/recommendations.py
==============================
GET /api/recommendations/<user_id>  – ranked recommendations for a user
"""

from flask import Blueprint, jsonify, current_app

recommendations_bp = Blueprint("recommendations", __name__)


def _db():
    return current_app.config["DB"]


@recommendations_bp.route("/recommendations/<int:user_id>", methods=["GET"])
def get_recommendations(user_id: int):
    user = _db().get_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    recs = _db().get_recommendations(user_id)
    return jsonify({
        "user_id":        user_id,
        "user_name":      user["name"],
        "count":          len(recs),
        "recommendations": recs,
    })
