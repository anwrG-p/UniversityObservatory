"""
models/clusterer.py
====================
OpportunityClusterer
--------------------
K-Means clustering on TF-IDF vectors.

Outputs
-------
* Integer cluster label per document.
* Per-cluster metadata: name derived from top TF-IDF centroid terms.
* PCA 2-D coordinates for dashboard scatter plot.
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA

import config

logger = logging.getLogger(__name__)

# Human-readable names mapped from centroid keywords at runtime.
# Fallback if name cannot be derived automatically.
_CLUSTER_NAME_FALLBACK = {
    0: "Machine Learning & AI",
    1: "Data Science & Analytics",
    2: "NLP & Language Models",
    3: "Vision & Robotics",
    4: "Scholarships & Funding",
}


class OpportunityClusterer:
    """K-Means clustering for opportunity documents."""

    def __init__(self, n_clusters: Optional[int] = None):
        self.n_clusters = n_clusters
        self._vectorizer: TfidfVectorizer = TfidfVectorizer(
            max_features=config.CLUSTERING_MAX_FEATURES,
            ngram_range=(1, 2),
            stop_words="english",
            sublinear_tf=True,
        )
        self._model: KMeans = KMeans(
            n_clusters=self.n_clusters or config.N_CLUSTERS,
            random_state=config.CLUSTERING_RANDOM_STATE,
            n_init=10,
        )
        self._pca: PCA = PCA(n_components=2, random_state=42)
        self.pca_coords: List[Dict] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit_predict(
        self, texts: List[str]
    ) -> Tuple[np.ndarray, Dict[int, Dict]]:
        """
        Vectorise texts, cluster them, and return labels + cluster metadata.

        Parameters
        ----------
        texts : list of str
            Raw opportunity texts (title + description).

        Returns
        -------
        labels : np.ndarray, shape (n_docs,)
        cluster_meta : dict  {cluster_id (0-indexed): {"name": ..., "keywords": ...}}
        """
        # Dynamic cluster count estimation if not explicitly forced
        num_docs = len(texts)
        if self.n_clusters is None: 
            estimated_k = int(np.sqrt(num_docs / 2))
            actual_k = max(2, min(12, estimated_k))
            self._model.set_params(n_clusters=actual_k)
        elif num_docs < self.n_clusters:
            # Reduce clusters to avoid empty-cluster errors
            self._model.set_params(n_clusters=max(2, num_docs // 2))

        X = self._vectorizer.fit_transform(texts)
        labels = self._model.fit_predict(X)

        cluster_meta = self._extract_cluster_meta()
        self._store_pca(X, labels)

        logger.info(
            "K-Means: %d docs → %d clusters", len(texts), self._model.n_clusters
        )
        return labels, cluster_meta

    def get_pca_coords(self) -> List[Dict]:
        """Return PCA-reduced 2-D coordinates (for dashboard scatter)."""
        return self.pca_coords

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_cluster_meta(self) -> Dict[int, Dict]:
        """Build human-readable cluster names from centroid terms."""
        feature_names = self._vectorizer.get_feature_names_out()
        centroids     = self._model.cluster_centers_
        meta = {}
        seen_names = set()
        for idx, centroid in enumerate(centroids):
            top_indices = centroid.argsort()[-8:][::-1]
            top_terms   = [feature_names[i] for i in top_indices]
            base_name = self._name_from_terms(idx, top_terms)
            
            name = base_name
            counter = 2
            while name in seen_names:
                name = f"{base_name} {counter}"
                counter += 1
            seen_names.add(name)
            
            meta[idx] = {
                "name":     name,
                "keywords": ", ".join(top_terms),
            }
        return meta

    @staticmethod
    def _name_from_terms(idx: int, terms: List[str]) -> str:
        """Heuristic: map dominant term to a cluster name via scoring."""
        joined = " ".join(terms).lower()
        
        rules = {
            "Scholarships & Funding": ["scholarship", "fellowship", "grant", "funding", "stipend", "bursary"],
            "NLP & LLMs":             ["nlp", "language", "text", "bert", "transformers", "gpt", "llm", "semantic", "parsing"],
            "Computer Vision & AI":   ["vision", "image", "robotic", "autonomous", "lidar", "perception", "3d", "detection"],
            "Data Science & BI":      ["data", "analytics", "sql", "pandas", "visualization", "bi", "tableau", "statistics"],
            "Deep Learning & ML":     ["deep learning", "machine learning", "neural", "pytorch", "tensorflow", "cnn", "rnn", "gradient"],
            "Courses & MOOCs":        ["course", "mooc", "certification", "edx", "coursera", "udemy", "workshop", "tutorial"],
            "Research & Academia":    ["research", "paper", "arxiv", "conference", "abstract", "publication", "lab", "scientific"],
            "Robotics & Control":     ["robotic", "control", "autonomous", "drone", "actuator", "sensor", "path planning"],
            "Cybersecurity & Net":    ["security", "cyber", "network", "cryptography", "encryption", "threat", "vulnerability"],
            "Bio-Tech & Health":      ["bio", "medical", "health", "genome", "protein", "clinic", "healthcare", "pharma"]
        }
        
        scores = {cat: 0 for cat in rules}
        for cat, keywords in rules.items():
            for kw in keywords:
                if kw in joined:
                    # Specific/phrase matches get more points
                    scores[cat] += 2 if " " in kw else 1
        
        # Get category with highest score
        best_cat = max(scores, key=scores.get)
        if scores[best_cat] > 0:
            return best_cat
            
        # Final Fallback: Construct name from top 3 keywords
        top_k = [t.capitalize() for t in terms[:3]]
        if len(top_k) >= 2:
            return " & ".join(top_k)
            
        return _CLUSTER_NAME_FALLBACK.get(idx, f"Cluster {idx + 1}")

    def _store_pca(self, X, labels: np.ndarray) -> None:
        """Reduce to 2-D and store alongside labels for scatter plot."""
        try:
            X_dense = X.toarray()
            coords2d = self._pca.fit_transform(X_dense)
            self.pca_coords = [
                {"x": float(coords2d[i, 0]), "y": float(coords2d[i, 1]),
                 "cluster": int(labels[i]) + 1}
                for i in range(len(labels))
            ]
        except Exception as exc:
            logger.warning("PCA failed: %s", exc)
            self.pca_coords = []
