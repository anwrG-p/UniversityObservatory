"""
main.py – University Observatory MAS Entry Point
=================================================
Usage
-----
    # 1. Initialize database and seed sample data, then run full pipeline:
    conda run -n HIDE python main.py --init --pipeline

    # 2. Start only the web server (pipeline must have run at least once):
    conda run -n HIDE python main.py --serve

    # 3. Full: init + pipeline + serve
    conda run -n HIDE python main.py --init --pipeline --serve

    # 4. Run pipeline without re-scraping (DB already seeded):
    conda run -n HIDE python main.py --pipeline --no-scrape
"""

import argparse
import logging
import os
import sys

# ── Add project root to path ──────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config

# ── Logging setup ─────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format=config.LOG_FORMAT,
)
logger = logging.getLogger("main")


def setup_dirs():
    """Create required directories."""
    if not str(config.DATABASE_PATH).startswith(("postgres", "http")):
        os.makedirs(os.path.dirname(config.DATABASE_PATH), exist_ok=True)
    os.makedirs(config.MODEL_DIR, exist_ok=True)


def initialize(db):
    """Seed database with schema and sample data."""
    logger.info("Seeding database…")
    db.seed_from_file(config.SEED_PATH)
    logger.info("Database ready.")


def run_pipeline(db, skip_scraping: bool = False):
    """Execute the full MAS pipeline via CoordinatorAgent."""
    from agents.coordinator import CoordinatorAgent
    coordinator = CoordinatorAgent(db)
    report = coordinator.execute(skip_scraping=skip_scraping)
    steps  = report.get("steps", {})
    logger.info("─" * 60)
    logger.info("PIPELINE REPORT")
    logger.info("─" * 60)
    for agent, result in steps.items():
        if isinstance(result, dict):
            status = result.get("status", "?")
            logger.info("  %-35s  [%s]", agent, status.upper())
        else:
            logger.info("  %-35s  [%s]", agent, str(result))
    logger.info("─" * 60)
    return report


def serve(db):
    """Start the Flask web server."""
    from api.app import create_app
    app = create_app(db)
    logger.info("Dashboard available at → http://127.0.0.1:%d", config.FLASK_PORT)
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
        use_reloader=False,
    )


def main():
    parser = argparse.ArgumentParser(
        description="University Observatory MAS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--init",      action="store_true", help="Seed database with sample data")
    parser.add_argument("--pipeline",  action="store_true", help="Run the full MAS pipeline")
    parser.add_argument("--no-scrape", action="store_true", help="Skip scraping in pipeline")
    parser.add_argument("--reset",     action="store_true", help="Wipe all data from the database")
    parser.add_argument("--serve",     action="store_true", help="Start the Flask web server")
    parser.add_argument("--real-data", action="store_true", help="Use real scraping/APIs instead of mock data")
    args = parser.parse_args()

    # Default: if no flag given, do everything
    if not any([args.init, args.pipeline, args.serve, args.reset]):
        args.init     = True
        args.pipeline = True
        args.serve    = True

    if args.real_data:
        config.USE_REAL_DATA = True

    setup_dirs()

    from database.db_manager import DatabaseManager
    db = DatabaseManager(config.DATABASE_PATH)

    if args.reset:
        db.clear_all_data()

    if args.init:
        initialize(db)

    if args.pipeline:
        run_pipeline(db, skip_scraping=args.no_scrape)

    if args.serve:
        serve(db)


if __name__ == "__main__":
    main()
