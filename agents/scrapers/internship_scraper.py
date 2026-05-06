"""
agents/scrapers/internship_scraper.py
=====================================
InternshipScraperAgent - collects internship listings.

Real-data mode (USE_REAL_DATA=True)
------------------------------------
Delegates to:
  1. InternshipFirecrawlAgent  - scrapes AI job boards via self-hosted Firecrawl
  2. RemotiveAPIAgent          - fetches remote AI/DS jobs from Remotive public API

Mock-data mode (USE_REAL_DATA=False, default)
----------------------------------------------
Samples from the curated pool below so the full pipeline works
without any external dependencies.
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from agents.base_agent import BaseAgent
from database.db_manager import DatabaseManager


# ---------------------------------------------------------------------------
# Simulated source data
# ---------------------------------------------------------------------------

_INTERNSHIP_POOL: List[Dict] = [
    {
        "title":       "Machine Learning Intern - DeepMind",
        "description": (
            "Research internship at Google DeepMind. Work on reinforcement learning, "
            "multi-agent systems, and large-scale model training. Requires Python, "
            "JAX/TensorFlow, and a strong ML foundation."
        ),
        "source":      "DeepMind Careers",
        "location":    "London, UK",
        "eligibility": "PhD or Master students in ML / CS",
        "url":         "https://deepmind.google/careers/",
    },
    {
        "title":       "Data Science Intern - Amazon",
        "description": (
            "Join Amazon's Data Science team to develop predictive models for "
            "supply-chain optimization. You'll use Python, SQL, and AWS SageMaker to "
            "build, train, and deploy models at scale."
        ),
        "source":      "Amazon Jobs",
        "location":    "Seattle, WA, USA",
        "eligibility": "Bachelor or Master students in Data Science, Statistics, CS",
        "url":         "https://www.amazon.jobs/",
    },
    {
        "title":       "AI Research Intern - INRIA",
        "description": (
            "INRIA offers funded research internships in AI, distributed computing, "
            "and formal verification. Work alongside top European researchers and "
            "contribute to open-source projects."
        ),
        "source":      "INRIA Internships",
        "location":    "Paris / Sophia-Antipolis, France",
        "eligibility": "Master or PhD students in CS, Mathematics",
        "url":         "https://www.inria.fr/en/internships",
    },
    {
        "title":       "NLP Engineering Intern - Hugging Face",
        "description": (
            "Develop and fine-tune open-source language models. Contribute to the "
            "Transformers library, build evaluation benchmarks, and publish results. "
            "Strong Python and NLP background required."
        ),
        "source":      "Hugging Face Jobs",
        "location":    "Remote / Paris, France",
        "eligibility": "Master or PhD in NLP, Computational Linguistics, or ML",
        "url":         "https://huggingface.co/jobs",
    },
    {
        "title":       "Computer Vision Intern - Valeo",
        "description": (
            "Work on perception systems for autonomous vehicles. Implement and "
            "evaluate 3D object detection, lane-keeping, and sensor-fusion algorithms "
            "using LiDAR and camera data."
        ),
        "source":      "Valeo Careers",
        "location":    "Paris, France",
        "eligibility": "Master or PhD in Computer Vision, Robotics, or ECE",
        "url":         "https://www.valeo.com/en/careers/",
    },
    {
        "title":       "MLOps Intern - Spotify",
        "description": (
            "Build infrastructure for Spotify's machine learning platform. Design "
            "feature stores, model monitoring pipelines, and CI/CD workflows for ML "
            "models serving millions of users."
        ),
        "source":      "Spotify Careers",
        "location":    "Stockholm, Sweden / Remote",
        "eligibility": "Bachelor or Master students in Software Engineering, ML, or DevOps",
        "url":         "https://www.lifeatspotify.com/jobs",
    },
    {
        "title":       "Bioinformatics AI Intern - Institut Pasteur",
        "description": (
            "Apply deep learning to genomic sequence analysis and protein structure "
            "prediction. Collaborate with biologists and computational scientists. "
            "Experience with PyTorch or TensorFlow preferred."
        ),
        "source":      "Institut Pasteur",
        "location":    "Paris, France",
        "eligibility": "Master or PhD in Bioinformatics, CS, or Biology",
        "url":         "https://research.pasteur.fr/en/jobs/",
    },
    {
        "title":       "Quantitative Research Intern - BNP Paribas",
        "description": (
            "Develop ML-based pricing models for financial derivatives. Work with "
            "time-series data, risk models, and large quantitative datasets. "
            "Strong mathematics and Python skills needed."
        ),
        "source":      "BNP Paribas Careers",
        "location":    "Paris, France",
        "eligibility": "Master or PhD in Applied Mathematics, Finance, or CS",
        "url":         "https://group.bnpparibas/en/careers",
    },
    {
        "title":       "Federated Learning Research Intern - Nokia Bell Labs",
        "description": (
            "Research privacy-preserving ML for edge devices. Design federated "
            "protocols, implement differential privacy guarantees, and benchmark "
            "communication-efficient algorithms."
        ),
        "source":      "Nokia Bell Labs",
        "location":    "Espoo, Finland / Remote",
        "eligibility": "PhD students in ML, Distributed Systems, or Security",
        "url":         "https://www.nokia.com/careers/",
    },
    {
        "title":       "Robotics & RL Intern - Boston Dynamics",
        "description": (
            "Develop reinforcement learning controllers for quadruped and manipulator "
            "robots. Work in simulation (PyBullet / MuJoCo) and transfer policies "
            "to real hardware. C++, Python, and ROS experience valued."
        ),
        "source":      "Boston Dynamics Careers",
        "location":    "Waltham, MA, USA",
        "eligibility": "PhD or Master students in Robotics, ML, or ECE",
        "url":         "https://bostondynamics.com/careers/",
    },
]


class InternshipScraperAgent(BaseAgent):
    """
    Collects internship opportunities.

    Real-data mode  (config.USE_REAL_DATA = True)
    -----------------------------------------------
    1. InternshipFirecrawlAgent scrapes ai-jobs.net / EURAXESS via Firecrawl.
    2. RemotiveAPIAgent fetches remote AI/DS jobs from Remotive public API.
    Falls back to mock pool if both return 0 results.

    Mock-data mode  (default, USE_REAL_DATA = False)
    -------------------------------------------------
    Samples from the curated ``_INTERNSHIP_POOL`` list.
    """

    def __init__(self, db: DatabaseManager):
        super().__init__("InternshipScraperAgent", db)

    # ------------------------------------------------------------------
    # BaseAgent implementation
    # ------------------------------------------------------------------

    def run(self, force_insert: bool = False, **kwargs) -> Dict[str, Any]:
        import config
        if config.USE_REAL_DATA:
            return self._run_real(force_insert=force_insert)
        return self._run_mock()

    # ------------------------------------------------------------------
    # Real-data path
    # ------------------------------------------------------------------

    def _run_real(self, force_insert: bool = False) -> Dict[str, Any]:
        from data_collection.firecrawl_agent import InternshipFirecrawlAgent
        from data_collection.api_agent import RemotiveAPIAgent

        total = 0

        fc_result  = InternshipFirecrawlAgent(self.db).execute(force_insert=force_insert)
        total     += fc_result.get("inserted", 0)

        api_result = RemotiveAPIAgent(self.db).execute(force_insert=force_insert)
        total     += api_result.get("inserted", 0)

        if total == 0:
            self.logger.info("Real sources returned 0 new records (all were duplicates).")

        fetched = fc_result.get("candidates", 0) + api_result.get("fetched", 0)
        return {
            "status": "ok", 
            "agent": self.name, 
            "inserted": total, 
            "fetched": fetched,
            "source": "real"
        }

    # ------------------------------------------------------------------
    # Mock-data path (default)
    # ------------------------------------------------------------------

    def _run_mock(self) -> Dict[str, Any]:
        records  = random.sample(_INTERNSHIP_POOL, random.randint(6, len(_INTERNSHIP_POOL)))
        existing_urls = {row["url"] for row in self.db.execute("SELECT url FROM opportunities WHERE url IS NOT NULL")}
        inserted = 0
        for src in records:
            if src.get("url", "") in existing_urls:
                continue
            rec = dict(src)
            rec["type"]     = "internship"
            rec["deadline"] = (datetime.utcnow() + timedelta(days=random.randint(30, 180))).strftime("%Y-%m-%d")
            rec["category"] = "internship"
            self.db.insert_opportunity(rec)
            inserted += 1
        self.logger.info("Mock: inserted %d internship records.", inserted)
        return {"status": "ok", "agent": self.name, "inserted": inserted, "source": "mock"}

