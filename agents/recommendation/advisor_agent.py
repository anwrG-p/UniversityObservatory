"""
agents/recommendation/advisor_agent.py
=======================================
AdvisorAgent
------------
Receives raw match scores from RelevanceMatcherAgent, applies business
rules (deadline proximity boost, level-eligibility boost), ranks the
final list, and persists the top-K recommendations to the database.
"""

import re
from datetime import datetime
from typing import Any, Dict, List

import config
from agents.base_agent import BaseAgent
from database.db_manager import DatabaseManager


class AdvisorAgent(BaseAgent):
    """
    Ranks and persists personalised recommendations.

    Scoring formula
    ---------------
    final_score = cosine_sim * 0.7 + deadline_boost * 0.2 + level_boost * 0.1
    """

    def __init__(self, db: DatabaseManager):
        super().__init__("AdvisorAgent", db)

    # ------------------------------------------------------------------
    # BaseAgent contract
    # ------------------------------------------------------------------

    def run(self, matches: List[Dict] = None, **kwargs) -> Dict[str, Any]:
        if not matches:
            self.logger.warning("No matches received - AdvisorAgent idle.")
            return {"status": "ok", "agent": self.name, "persisted": 0}

        users = {u["id"]: u for u in self.db.get_users()}
        opps  = {o["id"]: o for o in self.db.get_opportunities()}

        # Group by user
        by_user: Dict[int, List[Dict]] = {}
        for m in matches:
            by_user.setdefault(m["user_id"], []).append(m)

        total_persisted = 0
        for user_id, user_matches in by_user.items():
            user = users.get(user_id, {})
            ranked = self._rank(user_matches, user, opps)
            top_k  = ranked[: config.RECOMMENDATION_TOP_K]

            self.db.clear_recommendations(user_id)
            for rec in top_k:
                self.db.insert_recommendation(
                    user_id=user_id,
                    opp_id=rec["opportunity_id"],
                    score=round(rec["final_score"], 4),
                    reason=rec["reason"],
                )
            total_persisted += len(top_k)

        self.logger.info("Persisted %d recommendations.", total_persisted)
        return {"status": "ok", "agent": self.name, "persisted": total_persisted}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _rank(
        self,
        matches: List[Dict],
        user: Dict,
        opps: Dict[int, Dict],
    ) -> List[Dict]:
        scored = []
        for m in matches:
            opp = opps.get(m["opportunity_id"], {})
            cosine        = m["score"]
            deadline_b    = self._deadline_boost(opp.get("deadline", ""))
            level_b       = self._level_boost(user.get("level", ""), opp.get("eligibility", ""))
            final_score   = cosine * 0.7 + deadline_b * 0.2 + level_b * 0.1
            scored.append({
                **m,
                "final_score": final_score,
                "reason": (
                    f"Cosine similarity {cosine:.2f}; "
                    f"deadline boost {deadline_b:.2f}; "
                    f"level match {level_b:.2f}"
                ),
            })
        return sorted(scored, key=lambda x: x["final_score"], reverse=True)

    @staticmethod
    def _deadline_boost(deadline_str: str) -> float:
        """Closer deadlines get a higher urgency boost (0-1)."""
        if not deadline_str:
            return 0.5
        try:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d")
            days_left = (deadline - datetime.utcnow()).days
            if days_left < 0:
                return 0.0
            if days_left <= 30:
                return 1.0
            if days_left <= 90:
                return 0.7
            return 0.4
        except ValueError:
            return 0.5

    @staticmethod
    def _level_boost(user_level: str, eligibility: str) -> float:
        """1.0 if user level keyword found in eligibility text, else 0.3."""
        if not user_level or not eligibility:
            return 0.5
        level_map = {
            "bachelor": ["bachelor", "undergraduate", "bsc"],
            "master":   ["master", "msc", "mres"],
            "phd":      ["phd", "doctoral", "doctor"],
            "postdoc":  ["postdoc", "postdoctoral", "researcher"],
            "professor":["professor", "faculty", "senior"],
        }
        keywords = level_map.get(user_level.lower(), [])
        elig_lower = eligibility.lower()
        return 1.0 if any(kw in elig_lower for kw in keywords) else 0.3
