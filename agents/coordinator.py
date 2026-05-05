"""
agents/coordinator.py
======================
CoordinatorAgent – the orchestrator of the entire MAS.

Responsibilities
----------------
1. Instantiate all sub-agents.
2. Execute them in the correct dependency order.
3. Pass outputs between dependent agents (e.g. matcher → advisor).
4. Support optional APScheduler-based periodic execution.
5. Return a full pipeline report.

Pipeline order
--------------
[Scrapers] → [ClassificationAgent] → [ClusteringAgent]
          → [RelevanceMatcherAgent] → [AdvisorAgent]
          → [NotificationAgent]
"""

import logging
from typing import Any, Dict, Optional

from agents.base_agent import BaseAgent
from agents.scrapers import (
    InternshipScraperAgent,
    ScholarshipScraperAgent,
    CertificationScraperAgent,
)
from agents.analysis import ClassificationAgent, ClusteringAgent
from agents.recommendation import RelevanceMatcherAgent, AdvisorAgent
from agents.notification import NotificationAgent
from database.db_manager import DatabaseManager

logger = logging.getLogger("CoordinatorAgent")


class CoordinatorAgent(BaseAgent):
    """
    Orchestrates all agents in the correct execution order.

    Parameters
    ----------
    db : DatabaseManager
        Shared database connection used by all child agents.
    """

    def __init__(self, db: DatabaseManager):
        super().__init__("CoordinatorAgent", db)

        # Observer agents
        self.internship_scraper    = InternshipScraperAgent(db)
        self.scholarship_scraper   = ScholarshipScraperAgent(db)
        self.certification_scraper = CertificationScraperAgent(db)

        # Analysis agents
        self.classification_agent  = ClassificationAgent(db)
        self.clustering_agent      = ClusteringAgent(db)

        # Recommendation agents
        self.relevance_matcher     = RelevanceMatcherAgent(db)
        self.advisor_agent         = AdvisorAgent(db)

        # System agents
        self.notification_agent    = NotificationAgent(db)

        self._pipeline_report: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # BaseAgent contract
    # ------------------------------------------------------------------

    def run(self, skip_scraping: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Execute the full MAS pipeline.

        Parameters
        ----------
        skip_scraping : bool
            Set True to skip data collection (useful when DB already seeded).
        """
        report: Dict[str, Any] = {"status": "ok", "agent": self.name, "steps": {}}

        import requests
        import time
        print("\n" + "-"*40)
        print("NETWORK HEARTBEAT")
        try:
            r = requests.get("https://export.arxiv.org/api/query?search_query=cat:cs.AI&max_results=1", timeout=5)
            status_label = {200: "SUCCESS", 429: "RATE_LIMITED (wait ~10min)", 400: "BAD_REQUEST (query format error)"}.get(r.status_code, f"ERROR_{r.status_code}")
            print(f"  ArXiv API Connection: {status_label} (Status {r.status_code})")
        except Exception as e:
            print(f"  ArXiv API Connection: FAILED -> {e}")
        print("-"*40 + "\n")

        force_insert = kwargs.get("force_insert", False)
        if force_insert:
            logger.info("!!! FORCE_INSERT ENABLED: Skipping deduplication check !!!")


        # ── Step 1-3 : Scraping ──────────────────────────────────────
        if not skip_scraping:
            logger.info("=== STEP 1-3: Scraping ===")
            for agent in (
                self.internship_scraper,
                self.scholarship_scraper,
                self.certification_scraper,
            ):
                result = agent.execute(force_insert=force_insert)
                report["steps"][agent.name] = result
                time.sleep(3)  # Be polite to APIs
        else:
            logger.info("Skipping scraping (skip_scraping=True)")
            report["steps"]["scraping"] = "skipped"

        # ── Step 4 : Classification ──────────────────────────────────
        logger.info("=== STEP 4: Classification ===")
        report["steps"]["ClassificationAgent"] = self.classification_agent.execute()

        # ── Step 5 : Clustering ──────────────────────────────────────
        logger.info("=== STEP 5: Clustering ===")
        report["steps"]["ClusteringAgent"] = self.clustering_agent.execute()

        # ── Step 6 : Relevance matching ──────────────────────────────
        logger.info("=== STEP 6: Relevance Matching ===")
        match_result = self.relevance_matcher.execute()
        report["steps"]["RelevanceMatcherAgent"] = match_result

        # ── Step 7 : Advisor ranks & persists ────────────────────────
        logger.info("=== STEP 7: Advisor ===")
        matches = match_result.get("data", [])
        report["steps"]["AdvisorAgent"] = self.advisor_agent.execute(matches=matches)

        # ── Step 8 : Notifications ───────────────────────────────────
        logger.info("=== STEP 8: Notifications ===")
        report["steps"]["NotificationAgent"] = self.notification_agent.execute()

        self._pipeline_report = report
        logger.info("Pipeline complete.")
        return report

    # ------------------------------------------------------------------
    # Scheduler integration (APScheduler)
    # ------------------------------------------------------------------

    def start_scheduler(self, interval_minutes: int = 60) -> None:
        """Start APScheduler to run the pipeline on a fixed interval."""
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            scheduler = BackgroundScheduler()
            scheduler.add_job(
                func=self.execute,
                trigger="interval",
                minutes=interval_minutes,
                id="mas_pipeline",
                replace_existing=True,
            )
            scheduler.start()
            logger.info(
                "Scheduler started – pipeline runs every %d minutes.", interval_minutes
            )
        except ImportError:
            logger.error("APScheduler not installed. Run: pip install apscheduler")

    def get_pipeline_report(self) -> Dict[str, Any]:
        return self._pipeline_report
