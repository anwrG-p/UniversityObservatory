"""
agents/recommendation/relevance_matcher.py
===========================================
RelevanceMatcherAgent
---------------------
Computes cosine similarity between each user's combined profile text
(interests + skills) and every opportunity description.

Produces a scored list per user which AdvisorAgent then ranks and persists.
"""

from typing import Any, Dict, List, Tuple

from agents.base_agent import BaseAgent
from database.db_manager import DatabaseManager
from models.recommender import ContentBasedRecommender


class RelevanceMatcherAgent(BaseAgent):
    """Matches user profiles to opportunities via cosine similarity."""

    def __init__(self, db: DatabaseManager):
        super().__init__("RelevanceMatcherAgent", db)
        self._recommender = ContentBasedRecommender()

    # ------------------------------------------------------------------
    # BaseAgent contract
    # ------------------------------------------------------------------

    def run(self, **kwargs) -> Dict[str, Any]:
        users         = self.db.get_users()
        opportunities = self.db.get_opportunities()

        if not users or not opportunities:
            self.logger.warning("Empty users or opportunities – skipping matching.")
            return {"status": "ok", "agent": self.name, "matches": 0}

        opp_texts = [
            f"{o['title']} {o['description']} {o.get('eligibility', '')}"
            for o in opportunities
        ]

        # Fit vectoriser on corpus
        self._recommender.fit(opp_texts)

        all_matches: List[Dict] = []
        for user in users:
            user_text = (
                f"{user.get('profile', '')} "
                f"{user.get('interests', '')} "
                f"{user.get('skills', '')}"
            )
            scores: List[Tuple[int, float]] = self._recommender.match(
                user_text, opp_texts
            )
            # Attach opportunity metadata
            for idx, score in scores:
                all_matches.append({
                    "user_id":        user["id"],
                    "opportunity_id": opportunities[idx]["id"],
                    "score":          score,
                    "title":          opportunities[idx]["title"],
                })

        self.logger.info(
            "Generated %d raw matches for %d users.", len(all_matches), len(users)
        )
        return {
            "status":  "ok",
            "agent":   self.name,
            "matches": len(all_matches),
            "data":    all_matches,
        }
