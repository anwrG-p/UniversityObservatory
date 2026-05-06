"""
agents/coordinator.py
======================
CoordinatorAgent - the orchestrator of the entire MAS.

Responsibilities
----------------
1. Instantiate all sub-agents.
2. Execute them in the correct dependency order.
3. Pass outputs between dependent agents (e.g. matcher -> advisor).
4. Return a full pipeline report.

Pipeline order
--------------
[Scrapers] -> [ClassificationAgent] -> [ClusteringAgent]
          -> [RelevanceMatcherAgent] -> [AdvisorAgent]
          -> [NotificationAgent]
"""

import logging
from typing import Any, Dict

from agents.base_agent import BaseAgent
from agents.scrapers import (
    InternshipScraperAgent,
    ScholarshipScraperAgent,
    CertificationScraperAgent,
    PostdocScraperAgent,
    ProjectScraperAgent,
)
from agents.analysis import ClassificationAgent, ClusteringAgent
from agents.recommendation import RelevanceMatcherAgent, AdvisorAgent
from agents.notification import NotificationAgent
from agents.mesa_model import MesaMASModel
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
        self.postdoc_scraper       = PostdocScraperAgent(db)
        self.project_scraper       = ProjectScraperAgent(db)

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

        force_insert = kwargs.get("force_insert", False)
        if force_insert:
            logger.info("!!! FORCE_INSERT ENABLED: Skipping deduplication check !!!")


        # Build the Mesa MAS model. Per project guidelines (Section 6 -
        # Python Libraries and Tools), Mesa is the MAS framework: each
        # BaseAgent is wrapped in a mesa.Agent and stepped via Mesa's
        # BaseScheduler in strict pipeline order.
        scrapers = [
            self.internship_scraper,
            self.project_scraper,
            self.scholarship_scraper,
            self.certification_scraper,
            self.postdoc_scraper,
        ]

        if skip_scraping:
            logger.info("Skipping scraping (skip_scraping=True)")
            report["steps"]["scraping"] = "skipped"
            pipeline_agents = [
                self.classification_agent,
                self.clustering_agent,
                self.relevance_matcher,
                self.advisor_agent,
                self.notification_agent,
            ]
        else:
            pipeline_agents = scrapers + [
                self.classification_agent,
                self.clustering_agent,
                self.relevance_matcher,
                self.advisor_agent,
                self.notification_agent,
            ]

        logger.info("=== Running Mesa-orchestrated MAS pipeline ===")
        mesa_model = MesaMASModel(
            agents_in_order=pipeline_agents,
            step_kwargs={"force_insert": force_insert},
        )
        mesa_report = mesa_model.run()
        report["steps"].update(mesa_report["steps"])

        self._pipeline_report = report
        logger.info("Pipeline complete.")
        return report

