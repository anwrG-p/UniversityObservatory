"""
api/app.py
===========
Flask application factory.

Usage
-----
    from api.app import create_app
    app = create_app(db)
    app.run(...)
"""

import logging
from flask import Flask
from flask_cors import CORS
from database.db_manager import DatabaseManager
from api.routes.opportunities  import opportunities_bp
from api.routes.users          import users_bp
from api.routes.recommendations import recommendations_bp
from api.routes.notifications  import notifications_bp

logger = logging.getLogger(__name__)


def create_app(db: DatabaseManager = None) -> Flask:
    """
    Application factory - creates and configures the Flask app.

    Parameters
    ----------
    db : DatabaseManager, optional
        Shared database instance injected into all blueprints.
    """
    if db is None:
        db = DatabaseManager()
        
    import config

    app = Flask(
        __name__,
        template_folder="../dashboard/templates",
        static_folder="../dashboard/static",
    )
    app.config["SECRET_KEY"] = config.SECRET_KEY
    CORS(app)

    # Share the db through app context
    app.config["DB"] = db

    # Register blueprints
    app.register_blueprint(opportunities_bp,   url_prefix="/api")
    app.register_blueprint(users_bp,           url_prefix="/api")
    app.register_blueprint(recommendations_bp, url_prefix="/api")
    app.register_blueprint(notifications_bp,   url_prefix="/api")

    # Dashboard route
    from flask import render_template

    @app.route("/")
    def dashboard():
        return render_template("index.html")

    # Pipeline trigger route
    @app.route("/api/run-pipeline", methods=["POST"])
    def run_pipeline():
        from flask import jsonify, request, current_app
        force = request.json.get("force", False) if request.is_json else False
        
        from agents.coordinator import CoordinatorAgent
        coordinator = CoordinatorAgent(current_app.config["DB"])
        result = coordinator.execute(skip_scraping=False, force_insert=force)
        
        # Diagnostic logging for Render console
        print("\n" + "="*40)
        print("PIPELINE DIAGNOSTIC REPORT")
        print("="*40)
        for step, res in result.get("steps", {}).items():
            if isinstance(res, dict):
                status = res.get("status", "unknown")
                inserted = res.get("inserted", 0)
                fetched = res.get("fetched", res.get("candidates", 0))
                source = res.get("source", "N/A")
                print(f"Agent: {step:25} | Status: {status:10} | Found: {fetched:3} | New: {inserted:3} | Source: {source}")
            else:
                print(f"Agent: {step:25} | Result: {res}")
        print("="*40 + "\n")
        
        return jsonify(result)

    # Stats route
    @app.route("/api/stats")
    def stats():
        from flask import jsonify, current_app
        return jsonify(current_app.config["DB"].get_stats())

    logger.info("Flask application created.")
    return app
