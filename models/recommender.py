"""
models/recommender.py
======================
ContentBasedRecommender
------------------------
Content-based filtering via TF-IDF + cosine similarity.

Workflow
--------
1. ``fit(corpus)``        – Vectorise all opportunity texts.
2. ``match(query, corpus)`` – Score query (user profile) against corpus.
3. Returns ranked (index, score) pairs above the similarity threshold.
"""

import logging
from typing import List, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import config

logger = logging.getLogger(__name__)


class ContentBasedRecommender:
    """
    TF-IDF cosine-similarity recommendation engine.

    Parameters
    ----------
    top_k : int
        Maximum number of recommendations per user query.
    threshold : float
        Minimum cosine similarity score to include a result.
    """

    def __init__(
        self,
        top_k: int       = config.RECOMMENDATION_TOP_K,
        threshold: float = config.SIMILARITY_THRESHOLD,
    ):
        self.top_k     = top_k
        self.threshold = threshold
        self._vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            stop_words="english",
            sublinear_tf=True,
        )
        self._corpus_matrix = None  # shape (n_docs, n_features)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self, corpus: List[str]) -> None:
        """
        Fit the TF-IDF vectoriser on the opportunity corpus.

        Parameters
        ----------
        corpus : list of str
            One string per opportunity (title + description + eligibility).
        """
        self._corpus_matrix = self._vectorizer.fit_transform(corpus)
        logger.debug("Recommender fitted on %d documents.", len(corpus))

    def match(
        self, query: str, corpus: List[str]
    ) -> List[Tuple[int, float]]:
        """
        Score ``query`` against the pre-fitted corpus.

        Parameters
        ----------
        query  : str   – user profile text (interests + skills)
        corpus : list  – same list used in ``fit`` (for consistency)

        Returns
        -------
        List of (index, score) tuples, sorted descending, length ≤ top_k.
        """
        if self._corpus_matrix is None:
            logger.error("Recommender not fitted. Call fit() first.")
            return []

        query_vec = self._vectorizer.transform([query])
        sims      = cosine_similarity(query_vec, self._corpus_matrix)[0]

        # Filter by threshold and rank
        ranked = [
            (int(idx), float(score))
            for idx, score in enumerate(sims)
            if score >= self.threshold
        ]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[: self.top_k]

    def explain(self, query: str, document: str, top_n: int = 5) -> List[str]:
        """
        Return the top-N overlapping terms between query and document.
        Useful for generating human-readable recommendation reasons.
        """
        q_vec = self._vectorizer.transform([query])
        d_vec = self._vectorizer.transform([document])

        features  = self._vectorizer.get_feature_names_out()
        q_nonzero = set(features[q_vec.nonzero()[1]])
        d_nonzero = set(features[d_vec.nonzero()[1]])

        overlap   = sorted(q_nonzero & d_nonzero)
        return overlap[:top_n]
