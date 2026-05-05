"""
agents/analysis/clustering_agent.py
=====================================
ClusteringAgent
---------------
Applies K-Means clustering to the TF-IDF vector space of all opportunity
descriptions and writes cluster assignments back to the database.

Each cluster is labelled by its top-N TF-IDF terms (centroid inspection).
A PCA-reduced 2-D representation is also stored for the dashboard scatter
plot.
"""

from typing import Any, Dict

from agents.base_agent import BaseAgent
from database.db_manager import DatabaseManager
from models.clusterer import OpportunityClusterer


class ClusteringAgent(BaseAgent):
    """Groups opportunities into thematic clusters via K-Means."""

    def __init__(self, db: DatabaseManager):
        super().__init__("ClusteringAgent", db)
        self._clusterer = OpportunityClusterer()

    # ------------------------------------------------------------------
    # BaseAgent contract
    # ------------------------------------------------------------------

    def run(self, **kwargs) -> Dict[str, Any]:
        opportunities = self.db.get_opportunities()
        if len(opportunities) < 2:
            self.logger.warning("Too few opportunities for clustering.")
            return {"status": "ok", "agent": self.name, "clusters_found": 0}

        ids   = [o["id"] for o in opportunities]
        texts = [f"{o['title']} {o['description']}" for o in opportunities]

        labels, cluster_meta = self._clusterer.fit_predict(texts)

        # Persist cluster metadata
        for cid, meta in cluster_meta.items():
            self.db.upsert_cluster(cid + 1, meta["name"], meta["keywords"])

        # Assign cluster ids to opportunities
        for opp_id, label in zip(ids, labels):
            self.db.update_opportunity_cluster(opp_id, int(label) + 1)  # 1-indexed in DB

        self.logger.info(
            "Clustered %d opportunities into %d clusters.",
            len(opportunities), len(cluster_meta),
        )
        return {
            "status":        "ok",
            "agent":         self.name,
            "total":         len(opportunities),
            "clusters_found": len(cluster_meta),
            "cluster_sizes": {
                str(int(k) + 1): int((labels == k).sum()) for k in set(labels)
            },
        }
