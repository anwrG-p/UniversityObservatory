"""
agents/analysis/classification_agent.py
=========================================
ClassificationAgent
-------------------
Uses a TF-IDF + Logistic Regression pipeline (trained on seeded labeled
data) to classify every un-categorised opportunity in the database into one
of the defined categories: internship | scholarship | fellowship | course |
research_project | postdoc.

Design notes
------------
* The model is lazy-trained on first use and cached on disk.
* Falls back to keyword matching when confidence is low.
* Follows Open/Closed Principle: swap the sklearn pipeline for a
  transformer by subclassing or injecting a different ``_build_pipeline``.
"""

import os
import pickle
import logging
from typing import Any, Dict, List

from agents.base_agent import BaseAgent
from database.db_manager import DatabaseManager
from models.classifier import OpportunityClassifier
import config

logger = logging.getLogger(__name__)


class ClassificationAgent(BaseAgent):
    """Classifies raw opportunities stored in the database."""

    def __init__(self, db: DatabaseManager):
        super().__init__("ClassificationAgent", db)
        self._classifier = OpportunityClassifier()

    # ------------------------------------------------------------------
    # BaseAgent contract
    # ------------------------------------------------------------------

    def run(self, **kwargs) -> Dict[str, Any]:
        opportunities = self.db.get_opportunities()
        if not opportunities:
            self.logger.warning("No opportunities found - skipping classification.")
            return {"status": "ok", "agent": self.name, "classified": 0}

        # Build / load the model
        self._classifier.fit_or_load()

        classified = 0
        for opp in opportunities:
            text = f"{opp['title']} {opp['description']}"
            predicted = self._classifier.predict(text)
            if predicted != opp.get("category", ""):
                self.db.update_opportunity_category(opp["id"], predicted)
                classified += 1

        self.logger.info("Re-classified %d/%d opportunities.", classified, len(opportunities))
        return {
            "status":     "ok",
            "agent":      self.name,
            "total":      len(opportunities),
            "classified": classified,
        }
