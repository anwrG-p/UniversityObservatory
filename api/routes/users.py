"""
api/routes/users.py
====================
REST endpoints for Users resource.

GET   /api/users       - list all users
POST  /api/users       - create user
GET   /api/users/<id>  - get single user
"""

from flask import Blueprint, jsonify, request, current_app
from api.auth import require_auth

users_bp = Blueprint("users", __name__)


def _db():
    return current_app.config["DB"]


@users_bp.route("/users", methods=["GET"])
@require_auth
def list_users():
    users = _db().get_users()
    return jsonify({"count": len(users), "users": users})


@users_bp.route("/users/<int:user_id>", methods=["GET"])
@require_auth
def get_user(user_id: int):
    user = _db().get_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user)


@users_bp.route("/users", methods=["POST"])
@require_auth
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

@users_bp.route("/users/upload-resume", methods=["POST"])
def upload_resume():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files["file"]
    name = request.form.get("name", "Anonymous")
    email = request.form.get("email", "anonymous@example.com")
    
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF resumes are supported"}), 400
        
    try:
        import pypdf
        reader = pypdf.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + " "
    except Exception as e:
        return jsonify({"error": f"Failed to parse PDF: {str(e)}"}), 500
        
    # Create User
    user_data = {
        "name": name,
        "email": email,
        "profile": text[:2000],
        "interests": "",
        "skills": ""
    }
    
    try:
        user_id = _db().insert_user(user_data)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 409
        
    # Generate recommendations instantly for this user
    try:
        from models.recommender import ContentBasedRecommender
        recommender = ContentBasedRecommender()
        opportunities = _db().get_opportunities()
        
        opp_texts = [
            f"{o['title']} {o['description']} {o.get('eligibility', '')}"
            for o in opportunities
        ]
        
        # We need at least some opportunities to match against
        if opportunities:
            recommender.fit(opp_texts)
            scores = recommender.match(text, opp_texts)
            
            matches_response = []
            for idx, score in scores:
                opp = opportunities[idx]
                _db().insert_recommendation(user_id, opp["id"], float(score), "")
                matches_response.append({
                    "title": opp["title"],
                    "score": round(score * 100, 1),
                    "url": opp["url"],
                    "type": opp["type"]
                })
        else:
            matches_response = []
            
        return jsonify({
            "message": "Resume processed and matched!",
            "user_id": user_id,
            "recommendations": matches_response[:5] # Return top 5
        })
    except Exception as e:
        return jsonify({"error": f"Failed to generate matches: {str(e)}"}), 500
