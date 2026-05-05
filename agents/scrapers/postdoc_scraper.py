"""
agents/scrapers/postdoc_scraper.py
===================================
PostdocScraperAgent - collects postdoctoral and visiting professor positions.
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from agents.base_agent import BaseAgent
from database.db_manager import DatabaseManager


_POSTDOC_POOL: List[Dict] = [
    {
        "title":       "Postdoctoral Researcher - MIT CSAIL",
        "description": (
            "Two-year postdoc position at MIT CSAIL on foundation models, "
            "reasoning, and program synthesis. Collaborate with leading faculty "
            "and contribute to top-tier publications (NeurIPS, ICML, ICLR)."
        ),
        "source":      "MIT CSAIL",
        "location":    "Cambridge, MA, USA",
        "eligibility": "PhD in CS, ML, or related field (defended within 3 years)",
        "url":         "https://www.csail.mit.edu/careers",
        "type":        "postdoc",
    },
    {
        "title":       "Postdoctoral Fellow - ETH Zurich AI Center",
        "description": (
            "Three-year postdoc on trustworthy and interpretable machine learning. "
            "Includes generous research budget, conference travel, and access to "
            "ETH's HPC infrastructure."
        ),
        "source":      "ETH Zurich",
        "location":    "Zurich, Switzerland",
        "eligibility": "Recent PhD in ML, statistics, or applied mathematics",
        "url":         "https://ai.ethz.ch/postdoc",
        "type":        "postdoc",
    },
    {
        "title":       "Visiting Professor - University of Oxford (Dept. of CS)",
        "description": (
            "Six-month to one-year visiting professor position. Deliver an advanced "
            "course in AI/ML and pursue collaborative research with Oxford's AI groups. "
            "Office space, library access, and competitive stipend provided."
        ),
        "source":      "University of Oxford",
        "location":    "Oxford, UK",
        "eligibility": "Tenured/tenure-track faculty in AI, ML, or theoretical CS",
        "url":         "https://www.cs.ox.ac.uk/visitors/",
        "type":        "visiting_professor",
    },
    {
        "title":       "Postdoc - Max Planck Institute for Intelligent Systems",
        "description": (
            "Postdoc on autonomous learning, robotics, and embodied AI. Work in "
            "world-class labs alongside Schölkopf and Black groups. Three-year "
            "contract with funded conference travel."
        ),
        "source":      "Max Planck Institute",
        "location":    "Tübingen, Germany",
        "eligibility": "PhD in ML, robotics, or computer vision",
        "url":         "https://is.mpg.de/jobs",
        "type":        "postdoc",
    },
    {
        "title":       "Postdoctoral Researcher - INRIA Paris",
        "description": (
            "Two-year funded postdoc on federated learning and privacy-preserving AI. "
            "Collaborate with industrial partners (Orange, Thales) and publish in "
            "top venues. EU citizenship not required."
        ),
        "source":      "INRIA",
        "location":    "Paris, France",
        "eligibility": "Recent PhD in ML, distributed systems, or cryptography",
        "url":         "https://jobs.inria.fr/",
        "type":        "postdoc",
    },
    {
        "title":       "Visiting Scholar - Stanford HAI",
        "description": (
            "Stanford Institute for Human-Centered AI invites visiting scholars to "
            "pursue research on AI ethics, policy, and societal impact. One-year "
            "term with stipend, housing assistance, and seminar series."
        ),
        "source":      "Stanford HAI",
        "location":    "Stanford, CA, USA",
        "eligibility": "Faculty or senior researchers in AI, policy, or social sciences",
        "url":         "https://hai.stanford.edu/people/visiting-scholars",
        "type":        "visiting_professor",
    },
    {
        "title":       "Postdoc - Mila Quebec AI Institute",
        "description": (
            "Two-year postdoc with Yoshua Bengio's group on causal representation "
            "learning and AI safety. Mila offers a vibrant research community with "
            "1000+ AI researchers and strong industrial ties."
        ),
        "source":      "Mila",
        "location":    "Montreal, Canada",
        "eligibility": "PhD in ML, statistics, or neuroscience",
        "url":         "https://mila.quebec/en/careers/",
        "type":        "postdoc",
    },
    {
        "title":       "Visiting Researcher - Alan Turing Institute",
        "description": (
            "Three-to-twelve month visiting researcher positions in data science "
            "and AI. Access to UK's national institute, collaboration with 13 partner "
            "universities, and funded research programmes."
        ),
        "source":      "Alan Turing Institute",
        "location":    "London, UK",
        "eligibility": "Established researchers in data science, AI, or statistics",
        "url":         "https://www.turing.ac.uk/work-turing",
        "type":        "visiting_professor",
    },
    {
        "title":       "Postdoctoral Associate - KAUST AI Initiative",
        "description": (
            "Fully funded postdoc on large language models and Arabic NLP. "
            "Tax-free salary, free housing, and access to Shaheen-III supercomputer. "
            "Two-year renewable contract."
        ),
        "source":      "KAUST",
        "location":    "Thuwal, Saudi Arabia",
        "eligibility": "Recent PhD in NLP, ML, or HPC",
        "url":         "https://www.kaust.edu.sa/en/work/postdoctoral-fellows",
        "type":        "postdoc",
    },
    {
        "title":       "Postdoc - DeepMind Research Scientist (early-career)",
        "description": (
            "Research scientist track for early-career postdocs. Work on "
            "reinforcement learning, multi-agent systems, or science applications "
            "of AI. Competitive salary plus equity."
        ),
        "source":      "Google DeepMind",
        "location":    "London, UK / Remote",
        "eligibility": "PhD in ML or related; strong publication record",
        "url":         "https://deepmind.google/careers/",
        "type":        "postdoc",
    },
]


class PostdocScraperAgent(BaseAgent):
    """
    Collects postdoctoral and visiting-professor opportunities.

    Mock-data mode samples from ``_POSTDOC_POOL``. The real-data path
    delegates to existing Firecrawl/RSS infrastructure when available
    and falls back gracefully to the mock pool otherwise.
    """

    def __init__(self, db: DatabaseManager):
        super().__init__("PostdocScraperAgent", db)

    def run(self, force_insert: bool = False, **kwargs) -> Dict[str, Any]:
        import config
        if config.USE_REAL_DATA:
            return self._run_real(force_insert=force_insert)
        return self._run_mock()

    def _run_real(self, force_insert: bool = False) -> Dict[str, Any]:
        try:
            from data_collection.firecrawl_agent import InternshipFirecrawlAgent
            fc = InternshipFirecrawlAgent(self.db).execute(force_insert=force_insert)
            inserted = fc.get("inserted", 0)
            fetched  = fc.get("candidates", 0)
        except Exception as exc:
            self.logger.warning("Real postdoc scrape failed (%s); falling back to mock.", exc)
            return self._run_mock()

        if inserted == 0:
            self.logger.info("Real sources returned 0 postdoc records; running mock fallback.")
            return self._run_mock()

        return {
            "status":   "ok",
            "agent":    self.name,
            "inserted": inserted,
            "fetched":  fetched,
            "source":   "real",
        }

    def _run_mock(self) -> Dict[str, Any]:
        records = random.sample(_POSTDOC_POOL, random.randint(5, len(_POSTDOC_POOL)))
        existing_urls = {row["url"] for row in self.db.execute("SELECT url FROM opportunities WHERE url IS NOT NULL")}
        inserted = 0
        for rec in records:
            if rec.get("url", "") in existing_urls:
                continue
            rec.setdefault("type", "postdoc")
            rec["deadline"] = (datetime.utcnow() + timedelta(days=random.randint(60, 270))).strftime("%Y-%m-%d")
            rec["category"] = rec["type"]
            self.db.insert_opportunity(rec)
            inserted += 1
        self.logger.info("Mock: inserted %d postdoc/visiting records.", inserted)
        return {"status": "ok", "agent": self.name, "inserted": inserted, "source": "mock"}
