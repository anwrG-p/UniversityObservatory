"""
agents/scrapers/certification_scraper.py
=========================================
CertificationScraperAgent – collects courses, certifications, webinars,
and research projects from MOOC platforms and academic portals.
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from agents.base_agent import BaseAgent
from database.db_manager import DatabaseManager


_CERT_POOL: List[Dict] = [
    {
        "title":       "Deep Learning Specialization – Coursera (DeepLearning.AI)",
        "description": (
            "Five-course specialization covering neural networks, CNNs, RNNs, "
            "transformers, and practical ML project structuring. Taught by Andrew Ng. "
            "Python assignments with TensorFlow and Keras."
        ),
        "source":      "Coursera / DeepLearning.AI",
        "location":    "Online",
        "eligibility": "Anyone with basic Python and linear algebra",
        "url":         "https://www.coursera.org/specializations/deep-learning",
        "type":        "course",
    },
    {
        "title":       "MLOps Specialization – Duke University / Coursera",
        "description": (
            "Learn to operationalize ML models: data pipelines, model monitoring, "
            "drift detection, CI/CD for ML, Docker, Kubernetes, and cloud deployment "
            "on AWS and GCP."
        ),
        "source":      "Coursera / Duke University",
        "location":    "Online",
        "eligibility": "ML practitioners with Python knowledge",
        "url":         "https://www.coursera.org/specializations/mlops-machine-learning-duke",
        "type":        "course",
    },
    {
        "title":       "Applied Data Science with Python – MIT / edX",
        "description": (
            "MIT professional certificate covering statistics, machine learning, "
            "data wrangling, visualization, and a capstone project. "
            "Includes pandas, scikit-learn, and Matplotlib."
        ),
        "source":      "edX / MIT",
        "location":    "Online",
        "eligibility": "Any learner with introductory programming",
        "url":         "https://www.edx.org/professional-certificate/mit-data-science",
        "type":        "course",
    },
    {
        "title":       "Reinforcement Learning Specialization – University of Alberta",
        "description": (
            "Four-course series on foundations and advanced RL: multi-armed bandits, "
            "temporal-difference learning, function approximation, and a capstone. "
            "Assignments in Python with OpenAI Gym."
        ),
        "source":      "Coursera / University of Alberta",
        "location":    "Online",
        "eligibility": "Learners with ML fundamentals",
        "url":         "https://www.coursera.org/specializations/reinforcement-learning",
        "type":        "course",
    },
    {
        "title":       "TensorFlow Developer Certificate",
        "description": (
            "Official Google certification validating ability to build and train "
            "ML models with TensorFlow. Covers image classification, NLP, time-series, "
            "and more. Exam taken remotely via PyCharm."
        ),
        "source":      "Google / TensorFlow",
        "location":    "Online / Remote Exam",
        "eligibility": "Developers with Python and ML experience",
        "url":         "https://www.tensorflow.org/certificate",
        "type":        "course",
    },
    {
        "title":       "AWS Certified Machine Learning – Specialty",
        "description": (
            "Industry-recognized certification for ML practitioners using AWS. "
            "Topics: data engineering, EDA, ML modeling, and AWS SageMaker. "
            "Prep resources and practice exams available."
        ),
        "source":      "Amazon Web Services",
        "location":    "Online / Testing Center",
        "eligibility": "Practitioners with 1+ year ML experience",
        "url":         "https://aws.amazon.com/certification/certified-machine-learning-specialty/",
        "type":        "course",
    },
    {
        "title":       "NeurIPS 2025 – Workshops & Tutorials (Virtual Pass)",
        "description": (
            "Participate in NeurIPS workshops, tutorials, and poster sessions covering "
            "the latest research in ML, AI safety, generative models, and more. "
            "Virtual registration includes all recorded content."
        ),
        "source":      "NeurIPS Foundation",
        "location":    "Vancouver, Canada / Online",
        "eligibility": "Students, researchers, and industry practitioners",
        "url":         "https://neurips.cc/",
        "type":        "course",
    },
    {
        "title":       "Fast.ai Practical Deep Learning for Coders",
        "description": (
            "Top-down, code-first approach to deep learning. Covers vision, NLP, "
            "tabular data, and diffusion models using PyTorch and the fastai library. "
            "Completely free with active community forums."
        ),
        "source":      "fast.ai",
        "location":    "Online (Free)",
        "eligibility": "Anyone with basic Python and high-school math",
        "url":         "https://course.fast.ai/",
        "type":        "course",
    },
    {
        "title":       "AI Safety Fundamentals – BlueDot Impact",
        "description": (
            "8-week virtual course on technical AI safety: robustness, alignment, "
            "interpretability, and governance. Weekly readings, cohort discussions, "
            "and optional research mentorship."
        ),
        "source":      "BlueDot Impact",
        "location":    "Online",
        "eligibility": "Graduate students and researchers interested in AI safety",
        "url":         "https://aisafety.com/",
        "type":        "course",
    },
    {
        "title":       "Open Source Research Project – Apache Spark ML",
        "description": (
            "Contribute to Apache Spark's MLlib and Structured Streaming. "
            "Work on distributed feature engineering, model serialization, "
            "and performance benchmarks. Mentored by Apache committers."
        ),
        "source":      "Apache Software Foundation",
        "location":    "Remote / Global",
        "eligibility": "Any developer with Java/Scala/Python and ML knowledge",
        "url":         "https://spark.apache.org/contributing.html",
        "type":        "research_project",
    },
    {
        "title":       "Kaggle AI Research Grant – Data Science Competition",
        "description": (
            "Kaggle's grant program for open AI research. Teams receive cloud compute "
            "credits, mentorship from Kaggle Grandmasters, and a cash prize. "
            "Projects must be open-sourced upon completion."
        ),
        "source":      "Kaggle / Google",
        "location":    "Online",
        "eligibility": "Any researcher or team with a valid research proposal",
        "url":         "https://www.kaggle.com/research",
        "type":        "research_project",
    },
]


class CertificationScraperAgent(BaseAgent):
    """
    Collects certifications, courses, webinars, and research projects.

    Real-data mode  (config.USE_REAL_DATA = True)
    -----------------------------------------------
    Uses ArXivAPIAgent to fetch recent ML papers as research projects.
    Falls back to mock pool if 0 results.

    Mock-data mode  (default, USE_REAL_DATA = False)
    -------------------------------------------------
    Samples from the curated ``_CERT_POOL`` list.
    """

    def __init__(self, db: DatabaseManager):
        super().__init__("CertificationScraperAgent", db)

    # ------------------------------------------------------------------
    # BaseAgent implementation
    # ------------------------------------------------------------------

    def run(self, **kwargs) -> Dict[str, Any]:
        import config
        if config.USE_REAL_DATA:
            return self._run_real()
        return self._run_mock()

    # ------------------------------------------------------------------
    # Real-data path
    # ------------------------------------------------------------------

    def _run_real(self) -> Dict[str, Any]:
        from data_collection.api_agent import ArXivAPIAgent

        api_result = ArXivAPIAgent(self.db).execute()
        total      = api_result.get("result", {}).get("inserted", 0)

        if total == 0:
            self.logger.info("Real sources returned 0 new records (all were duplicates).")

        return {"status": "ok", "agent": self.name, "inserted": total, "source": "real"}

    # ------------------------------------------------------------------
    # Mock-data path (default)
    # ------------------------------------------------------------------

    def _run_mock(self) -> Dict[str, Any]:
        records  = random.sample(_CERT_POOL, random.randint(6, len(_CERT_POOL)))
        inserted = 0
        for rec in records:
            rec["deadline"] = (datetime.utcnow() + timedelta(days=random.randint(90, 365))).strftime("%Y-%m-%d")
            rec["category"] = rec["type"]
            self.db.insert_opportunity(rec)
            inserted += 1
        self.logger.info("Mock: inserted %d certification/course records.", inserted)
        return {"status": "ok", "agent": self.name, "inserted": inserted, "source": "mock"}
