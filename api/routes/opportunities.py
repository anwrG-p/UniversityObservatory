"""
api/routes/opportunities.py
============================
REST endpoints for Opportunities resource.

GET  /api/opportunities          - list (with optional filters)
GET  /api/opportunities/<id>     - single opportunity
GET  /api/clusters               - list all clusters
GET  /api/clusters/<id>/opportunities - opportunities in cluster
"""

import json
import os

import config
from flask import Blueprint, jsonify, request, current_app
from api.auth import require_auth

opportunities_bp = Blueprint("opportunities", __name__)


def _db():
    return current_app.config["DB"]


@opportunities_bp.route("/opportunities", methods=["GET"])
@require_auth
def list_opportunities():
    opp_type   = request.args.get("type")
    location   = request.args.get("location")
    cluster_id = request.args.get("cluster_id", type=int)
    limit      = request.args.get("limit", default=200, type=int)

    opps = _db().get_opportunities(
        opp_type=opp_type,
        location=location,
        cluster_id=cluster_id,
        limit=limit,
    )
    return jsonify({"count": len(opps), "opportunities": opps})


@opportunities_bp.route("/opportunities/<int:opp_id>", methods=["GET"])
@require_auth
def get_opportunity(opp_id: int):
    opp = _db().get_opportunity(opp_id)
    if not opp:
        return jsonify({"error": "Not found"}), 404
    return jsonify(opp)


@opportunities_bp.route("/clusters", methods=["GET"])
@require_auth
def list_clusters():
    clusters = _db().get_clusters()
    return jsonify({"clusters": clusters})


@opportunities_bp.route("/clusters/pca", methods=["GET"])
@require_auth
def pca_coords():
    pca_path = os.path.join(config.MODEL_DIR, "pca_coords.json")
    if not os.path.exists(pca_path):
        return jsonify({"coords": [], "message": "Pipeline has not run yet"})
    try:
        with open(pca_path, encoding="utf-8") as f:
            coords = json.load(f)
        return jsonify({"coords": coords})
    except Exception as exc:
        return jsonify({"coords": [], "message": f"Error reading PCA data: {exc}"}), 500


@opportunities_bp.route("/clusters/<int:cluster_id>/opportunities", methods=["GET"])
@require_auth
def cluster_opportunities(cluster_id: int):
    opps = _db().get_opportunities(cluster_id=cluster_id)
    return jsonify({"cluster_id": cluster_id, "opportunities": opps})
