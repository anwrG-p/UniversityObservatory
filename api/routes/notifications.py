"""
api/routes/notifications.py
============================
GET   /api/notifications/<user_id>          - all notifications for user
PATCH /api/notifications/<id>/read          - mark as read
"""

from flask import Blueprint, jsonify, request, current_app
from api.auth import require_auth

notifications_bp = Blueprint("notifications", __name__)


def _db():
    return current_app.config["DB"]


@notifications_bp.route("/notifications/<int:user_id>", methods=["GET"])
@require_auth
def get_notifications(user_id: int):
    status = request.args.get("status")  # unread | read | None
    notifs = _db().get_notifications(user_id, status=status)
    return jsonify({
        "user_id":       user_id,
        "count":         len(notifs),
        "notifications": notifs,
    })


@notifications_bp.route("/notifications/<int:notif_id>/read", methods=["PATCH"])
@require_auth
def mark_read(notif_id: int):
    _db().mark_notification_read(notif_id)
    return jsonify({"status": "ok", "id": notif_id})
