"""
models/classifier.py
=====================
OpportunityClassifier
---------------------
TF-IDF + Logistic Regression pipeline for multi-class opportunity
classification.

Categories
----------
internship | scholarship | fellowship | course | research_project | postdoc

Training strategy
-----------------
The model is trained on a curated in-code labeled dataset the first time
it is used, then pickled to disk.  Subsequent calls load from the pickle
(``models/saved/classifier.pkl``).

Extending
---------
Replace ``_build_pipeline()`` to plug in any sklearn-compatible estimator
(e.g., SVM, transformer feature extractor).
"""

import os
import pickle
import logging
from typing import List, Optional, Tuple

import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-code labeled training corpus (diverse enough for robust classification)
# ---------------------------------------------------------------------------

_TRAINING_DATA: List[Tuple[str, str]] = [
    # internship
    ("Machine learning engineering intern Python TensorFlow deep learning research lab", "internship"),
    ("Software engineering intern data science SQL Python summer program", "internship"),
    ("Research intern NLP transformers language model fine-tuning", "internship"),
    ("Data engineer intern ETL pipelines cloud AWS big data analytics", "internship"),
    ("Computer vision intern autonomous driving LiDAR perception real-time", "internship"),
    ("AI internship reinforcement learning robotics control systems Python", "internship"),
    ("MLOps intern model deployment Kubernetes Docker CI/CD pipeline monitoring", "internship"),
    ("Bioinformatics intern genomics sequence analysis deep learning protein", "internship"),

    # scholarship
    ("PhD fellowship machine learning stipend full funding university research", "scholarship"),
    ("Graduate scholarship data science tuition waiver academic excellence award", "scholarship"),
    ("Master scholarship artificial intelligence European university grant", "scholarship"),
    ("Research grant funding AI project proposal university support", "scholarship"),
    ("Academic award excellence computer science bachelor tuition support", "scholarship"),
    ("Doctoral scholarship STEM women diversity funding program", "scholarship"),

    # fellowship
    ("Postdoctoral fellowship AI research institute funding two years", "fellowship"),
    ("Research fellowship visiting scientist laboratory exchange program", "fellowship"),
    ("Policy fellowship AI governance technology regulation government", "fellowship"),
    ("Innovation fellowship startup incubator AI data science entrepreneur", "fellowship"),
    ("Teaching fellowship university professor AI course curriculum", "fellowship"),

    # course
    ("Online course deep learning neural networks Python Coursera certification", "course"),
    ("Data science bootcamp Python pandas scikit-learn machine learning certificate", "course"),
    ("MOOC artificial intelligence edX MIT online learning modules", "course"),
    ("Professional certification cloud machine learning AWS SageMaker exam", "course"),
    ("Workshop NLP text classification transformers BERT hands-on training", "course"),
    ("Webinar data visualization matplotlib seaborn interactive dashboard", "course"),
    ("Tutorial reinforcement learning OpenAI gym policy gradient", "course"),
    ("Training program SQL databases analytics business intelligence BI", "course"),

    # research_project
    ("Open source contribution GitHub machine learning library scikit-learn", "research_project"),
    ("Research project climate change AI prediction model satellite data", "research_project"),
    ("Collaborative research federated learning privacy healthcare hospitals", "research_project"),
    ("Academic project graph neural networks social network analysis", "research_project"),
    ("Research initiative explainable AI interpretability SHAP LIME", "research_project"),
    ("Lab project computer vision medical imaging segmentation MRI", "research_project"),

    # postdoc
    ("Postdoctoral researcher position large language model alignment safety", "postdoc"),
    ("Postdoc computer vision autonomous systems ETH Zurich 2 year contract", "postdoc"),
    ("Visiting professor artificial intelligence summer research exchange", "postdoc"),
    ("Assistant professor AI machine learning tenure track university hiring", "postdoc"),
    ("Research scientist position deep learning publication record required", "postdoc"),
    ("Junior faculty position data science department teaching research", "postdoc"),
]


class OpportunityClassifier:
    """TF-IDF + Logistic Regression text classifier for opportunities."""

    _SAVE_PATH = os.path.join(config.MODEL_DIR, "classifier.pkl")

    def __init__(self):
        self._pipeline: Optional[Pipeline] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit_or_load(self) -> None:
        """Load from disk if available, otherwise train and save."""
        if self._pipeline is not None:
            return
        if os.path.exists(self._SAVE_PATH):
            self._load()
        else:
            self._train()
            self._save()

    def predict(self, text: str) -> str:
        """Return the predicted category for a single text string."""
        if self._pipeline is None:
            self.fit_or_load()
        return self._pipeline.predict([text])[0]

    def predict_proba(self, text: str) -> dict:
        """Return per-class probabilities."""
        if self._pipeline is None:
            self.fit_or_load()
        proba = self._pipeline.predict_proba([text])[0]
        classes = self._pipeline.classes_
        return dict(zip(classes, proba.tolist()))

    def score_cv(self, cv: int = 5) -> float:
        """Return mean cross-validated accuracy on training data."""
        X = [t for t, _ in _TRAINING_DATA]
        y = [l for _, l in _TRAINING_DATA]
        scores = cross_val_score(self._build_pipeline(), X, y, cv=cv, scoring="accuracy")
        return float(scores.mean())

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _train(self) -> None:
        logger.info("Training OpportunityClassifier on %d samples …", len(_TRAINING_DATA))
        X = [t for t, _ in _TRAINING_DATA]
        y = [l for _, l in _TRAINING_DATA]
        self._pipeline = self._build_pipeline()
        self._pipeline.fit(X, y)
        logger.info("Classifier trained. Classes: %s", list(self._pipeline.classes_))

    @staticmethod
    def _build_pipeline() -> Pipeline:
        return Pipeline([
            ("tfidf", TfidfVectorizer(
                max_features=config.CLASSIFIER_MAX_FEATURES,
                ngram_range=config.CLASSIFIER_NGRAM_RANGE,
                min_df=config.CLASSIFIER_MIN_DF,
                stop_words="english",
                sublinear_tf=True,
            )),
            ("clf", LogisticRegression(
                solver="lbfgs",
                max_iter=1000,
                C=5.0,
                random_state=42,
            )),
        ])

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._SAVE_PATH), exist_ok=True)
        with open(self._SAVE_PATH, "wb") as f:
            pickle.dump(self._pipeline, f)
        logger.info("Classifier saved to %s", self._SAVE_PATH)

    def _load(self) -> None:
        with open(self._SAVE_PATH, "rb") as f:
            self._pipeline = pickle.load(f)
        logger.info("Classifier loaded from %s", self._SAVE_PATH)
