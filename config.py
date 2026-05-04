"""
config.py - Central configuration for the University Observatory MAS.
All environment-specific settings live here to follow the Single
Responsibility / Open-Closed principles.
"""
import os
from dotenv import load_dotenv

# Load variables from .env file (if it exists)
load_dotenv()

# ---------------------------------------------------------------------------
# Base paths & Database URL
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# If DATABASE_URL is set in .env (e.g. Postgres), use it. Otherwise, default to local SQLite
DATABASE_PATH = os.getenv("DATABASE_URL", os.path.join(BASE_DIR, "database", "observatory.db"))
SCHEMA_PATH   = os.path.join(BASE_DIR, "database", "schema.sql")
SEED_PATH     = os.path.join(BASE_DIR, "database", "seed_data.sql")
MODEL_DIR     = os.path.join(BASE_DIR, "models", "saved")

# ---------------------------------------------------------------------------
# Flask
# ---------------------------------------------------------------------------
FLASK_HOST  = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT  = int(os.getenv("FLASK_PORT", 5000))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"
SECRET_KEY  = os.getenv("SECRET_KEY", "observatory-secret-key-change-in-prod")

# ---------------------------------------------------------------------------
# AI / ML
# ---------------------------------------------------------------------------
# Classification
CLASSIFIER_MAX_FEATURES   = 5000
CLASSIFIER_NGRAM_RANGE    = (1, 2)
CLASSIFIER_MIN_DF         = 1
OPPORTUNITY_CATEGORIES    = [
    "internship", "scholarship", "course",
    "research_project", "postdoc", "fellowship",
]

# Clustering
N_CLUSTERS               = 5
CLUSTERING_RANDOM_STATE  = 42
CLUSTERING_MAX_FEATURES  = 3000

# Recommendation
RECOMMENDATION_TOP_K     = 10     # opportunities returned per user
SIMILARITY_THRESHOLD     = 0.05   # minimum cosine similarity to include

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
SCRAPE_INTERVAL_MINUTES  = 60     # how often scrapers run automatically
PIPELINE_TIMEZONE        = "UTC"

# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------
MAX_NOTIFICATIONS_PER_RUN = 5     # limit alerts per pipeline cycle

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL  = "INFO"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

# ---------------------------------------------------------------------------
# Firecrawl (self-hosted)  –  https://github.com/firecrawl/firecrawl
# Run locally: docker compose up  (defaults to port 3002)
# ---------------------------------------------------------------------------
FIRECRAWL_URL     = os.getenv("FIRECRAWL_URL",     "http://localhost:3002")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "fc-local")
FIRECRAWL_TIMEOUT = 30           # seconds per scrape request

# Set USE_REAL_DATA=true (env var) or pass --real-data flag to main.py
USE_REAL_DATA = os.getenv("USE_REAL_DATA", "false").lower() == "true"

# ---------------------------------------------------------------------------
# Real scrape targets (Firecrawl will fetch these URLs)
# ---------------------------------------------------------------------------
INTERNSHIP_SCRAPE_URLS = [
    "https://ai-jobs.net/",
    "https://www.euraxess.eu/jobs/search?freeTextKeyword=machine+learning",
]
SCHOLARSHIP_SCRAPE_URLS = [
    "https://www.scholars4dev.com/category/scholarships-by-subject/science-technology/",
    "https://www.daad.de/en/studying-in-germany/scholarships/daad-scholarships/",
]
COURSE_SCRAPE_URLS = [
    "https://ai-jobs.net/certification/",
]

# ---------------------------------------------------------------------------
# API data sources (no scraping needed)
# ---------------------------------------------------------------------------
REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"
ARXIV_API_URL    = "http://export.arxiv.org/api/query"
ARXIV_SEARCH_QUERY = "cat:cs.AI+OR+cat:cs.LG+OR+cat:stat.ML"
ARXIV_MAX_RESULTS   = 15
