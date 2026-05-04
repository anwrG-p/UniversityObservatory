"""
agents/notification/notification_agent.py
==========================================
NotificationAgent
-----------------
After recommendations are generated, creates in-app notifications for
each user highlighting their top new opportunities.  Avoids duplicate
notifications by checking existing records.
"""

from typing import Any, Dict

import config
from agents.base_agent import BaseAgent
from database.db_manager import DatabaseManager


class NotificationAgent(BaseAgent):
    """Creates in-app notifications from the latest recommendations."""

    def __init__(self, db: DatabaseManager):
        super().__init__("NotificationAgent", db)

    # ------------------------------------------------------------------
    # BaseAgent contract
    # ------------------------------------------------------------------

    def run(self, **kwargs) -> Dict[str, Any]:
        users   = self.db.get_users()
        created = 0

        for user in users:
            recs = self.db.get_recommendations(user["id"])
            # Only notify for top-N results of this run
            for rec in recs[: config.MAX_NOTIFICATIONS_PER_RUN]:
                opp_id = rec["opportunity_id"]
                # Check if notification already exists
                existing = self.db.execute(
                    "SELECT id FROM notifications WHERE user_id=? AND opportunity_id=?",
                    (user["id"], opp_id),
                )
                if existing:
                    continue
                msg = (
                    f"New recommendation: \"{rec['title']}\" "
                    f"(score: {rec['score']:.2f}). "
                    f"Deadline: {rec.get('deadline', 'N/A')}."
                )
                self.db.insert_notification(user["id"], opp_id, msg)
                created += 1

        self.logger.info("Created %d new notifications.", created)
        return {"status": "ok", "agent": self.name, "notifications_created": created}
