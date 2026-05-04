# University Observatory – MAS

> Intelligent Multi-Agent System for Internship, Project, Certification, and Scholarship Management

## Quick Start

```bash
# 1. Activate the conda environment
conda activate HIDE

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run full pipeline + start web server
python main.py

# 4. Open dashboard
# → http://127.0.0.1:5000
```

## CLI Options

| Flag | Description |
|------|-------------|
| `--init` | Seed database with sample data |
| `--pipeline` | Run the full MAS pipeline |
| `--no-scrape` | Skip scraping (use existing DB data) |
| `--serve` | Start the Flask web server |

Running `python main.py` with no flags runs everything.

## Architecture

```
9 Agents across 4 layers:

Observer:       InternshipScraperAgent · ScholarshipScraperAgent · CertificationScraperAgent
Analysis:       ClassificationAgent (TF-IDF + LR) · ClusteringAgent (K-Means)
Recommendation: RelevanceMatcherAgent (cosine sim) · AdvisorAgent (multi-factor ranking)
System:         CoordinatorAgent (orchestrator) · NotificationAgent
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/opportunities` | List opportunities (filterable) |
| GET | `/api/opportunities/<id>` | Single opportunity |
| GET | `/api/users` | List users |
| POST | `/api/users` | Create user |
| GET | `/api/recommendations/<user_id>` | Recommendations per user |
| GET | `/api/notifications/<user_id>` | Notifications per user |
| GET | `/api/clusters` | All clusters |
| GET | `/api/stats` | Dashboard statistics |
| POST | `/api/run-pipeline` | Trigger pipeline |

## Project Structure

```
DCAI/
├── agents/            # 9 MAS agents
│   ├── scrapers/      # Observer agents
│   ├── analysis/      # Classification + Clustering
│   ├── recommendation/# Matcher + Advisor
│   ├── notification/  # NotificationAgent
│   ├── coordinator.py # CoordinatorAgent
│   └── base_agent.py  # Abstract base
├── models/            # ML models (classifier, clusterer, recommender)
├── database/          # Schema, seed data, DB manager
├── api/               # Flask app + REST routes
├── dashboard/         # HTML + CSS + JS frontend
├── config.py          # Central configuration
├── main.py            # Entry point
└── requirements.txt
```
