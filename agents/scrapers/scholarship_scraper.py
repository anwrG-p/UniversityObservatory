"""
agents/scrapers/scholarship_scraper.py
=======================================
ScholarshipScraperAgent – collects scholarships, fellowships, and grants.
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from agents.base_agent import BaseAgent
from database.db_manager import DatabaseManager


_SCHOLARSHIP_POOL: List[Dict] = [
    {
        "title":       "Google PhD Fellowship – Machine Learning",
        "description": (
            "Supports outstanding PhD students in CS. Fellows receive a stipend, "
            "mentorship from Google researchers, and opportunities to present at "
            "Google conferences. Open to students in accredited PhD programs globally."
        ),
        "source":      "Google Research",
        "location":    "Global",
        "eligibility": "2nd-3rd year PhD students in CS, ML, or related field",
        "url":         "https://research.google/outreach/phd-fellowship/",
        "type":        "scholarship",
    },
    {
        "title":       "Microsoft Research PhD Fellowship",
        "description": (
            "Two-year fellowship for PhD students in computing. Covers tuition, "
            "conference travel, and a competitive stipend. Research areas include "
            "AI, systems, HCI, and programming languages."
        ),
        "source":      "Microsoft Research",
        "location":    "Global",
        "eligibility": "PhD students in accredited universities, nominated by advisor",
        "url":         "https://www.microsoft.com/en-us/research/academic-program/phd-fellowship/",
        "type":        "scholarship",
    },
    {
        "title":       "Marie Skłodowska-Curie Actions – Individual Fellowship",
        "description": (
            "Prestigious EU-funded fellowship for experienced researchers. Supports "
            "interdisciplinary research mobility across Europe. Provides living "
            "allowance, mobility allowance, and family allowance."
        ),
        "source":      "European Commission – Horizon Europe",
        "location":    "European Union",
        "eligibility": "Experienced researchers (PhD + experience) of any nationality",
        "url":         "https://marie-sklodowska-curie-actions.ec.europa.eu/",
        "type":        "fellowship",
    },
    {
        "title":       "CIFAR AI Chairs Program",
        "description": (
            "Supports Canada's world-leading AI researchers at universities and "
            "research institutes. Includes funding for research activities, "
            "postdocs, and graduate students."
        ),
        "source":      "CIFAR",
        "location":    "Canada",
        "eligibility": "Faculty and senior researchers in AI/ML at Canadian institutions",
        "url":         "https://cifar.ca/ai/",
        "type":        "fellowship",
    },
    {
        "title":       "NVIDIA Graduate Fellowship",
        "description": (
            "Annual award for graduate students conducting research using NVIDIA "
            "GPU technology. Awards include a monetary prize, GPU hardware, and "
            "a visit to NVIDIA headquarters."
        ),
        "source":      "NVIDIA Research",
        "location":    "Global",
        "eligibility": "Full-time PhD students in GPU computing, ML, or graphics",
        "url":         "https://research.nvidia.com/graduate-fellowships",
        "type":        "scholarship",
    },
    {
        "title":       "Erasmus+ Scholarship for AI & Data Science",
        "description": (
            "European mobility grant enabling students to study at partner "
            "universities across 35+ countries. Covers tuition fee waivers, "
            "living stipend, and travel grant. Priority given to joint-degree programs."
        ),
        "source":      "Erasmus+ Programme",
        "location":    "Europe",
        "eligibility": "Enrolled students in participating universities, any level",
        "url":         "https://erasmus-plus.ec.europa.eu/",
        "type":        "scholarship",
    },
    {
        "title":       "NSF Graduate Research Fellowship (GRFP)",
        "description": (
            "The NSF GRFP provides three years of stipend and tuition support "
            "for outstanding graduate students in STEM, including CS, AI, and "
            "data science. Highly competitive and prestigious."
        ),
        "source":      "National Science Foundation",
        "location":    "USA",
        "eligibility": "Early-stage graduate students at accredited US institutions",
        "url":         "https://www.nsfgrfp.org/",
        "type":        "fellowship",
    },
    {
        "title":       "DeepMind Scholarship for Underrepresented Groups in AI",
        "description": (
            "Full scholarship covering tuition and living costs for students from "
            "underrepresented backgrounds pursuing Master's degrees in AI or ML "
            "at selected UK universities."
        ),
        "source":      "DeepMind Education",
        "location":    "United Kingdom",
        "eligibility": "Master's applicants from underrepresented backgrounds in AI",
        "url":         "https://deepmind.google/education/",
        "type":        "scholarship",
    },
    {
        "title":       "Fulbright Scholar Program – AI & Technology",
        "description": (
            "The Fulbright Program funds international study, research, and teaching. "
            "Scholars in AI, data science, and technology are eligible for grants "
            "to the USA or from the USA abroad."
        ),
        "source":      "U.S. Department of State",
        "location":    "Global / USA",
        "eligibility": "Graduate students and faculty, open to many nationalities",
        "url":         "https://foreign.fulbrightonline.org/",
        "type":        "fellowship",
    },
    {
        "title":       "Africa Oxford AI Scholarship",
        "description": (
            "Full scholarship for African students to pursue MSc or DPhil in AI, "
            "Machine Learning, or Data Science at the University of Oxford. "
            "Covers tuition, accommodation, and research expenses."
        ),
        "source":      "AfOx – Africa Oxford Initiative",
        "location":    "Oxford, UK",
        "eligibility": "African nationals applying to Oxford MSc/DPhil in AI or CS",
        "url":         "https://www.africaoxford.ox.ac.uk/",
        "type":        "scholarship",
    },
]


class ScholarshipScraperAgent(BaseAgent):
    """
    Collects scholarship and fellowship opportunities.

    Real-data mode  (config.USE_REAL_DATA = True)
    -----------------------------------------------
    Uses ScholarshipFirecrawlAgent to scrape scholars4dev / DAAD.
    Falls back to mock pool if 0 results.

    Mock-data mode  (default, USE_REAL_DATA = False)
    -------------------------------------------------
    Samples from the curated ``_SCHOLARSHIP_POOL`` list.
    """

    def __init__(self, db: DatabaseManager):
        super().__init__("ScholarshipScraperAgent", db)

    # ------------------------------------------------------------------
    # BaseAgent implementation
    # ------------------------------------------------------------------

    def run(self, **kwargs) -> Dict[str, Any]:
        import config
        if config.USE_REAL_DATA:
            return self._run_real()
        return self._run_mock()

    # ------------------------------------------------------------------
    # Real-data path
    # ------------------------------------------------------------------

    def _run_real(self) -> Dict[str, Any]:
        from data_collection.firecrawl_agent import ScholarshipFirecrawlAgent

        fc_result = ScholarshipFirecrawlAgent(self.db).execute()
        total     = fc_result.get("result", {}).get("inserted", 0)

        if total == 0:
            self.logger.info("Real sources returned 0 new records (all were duplicates).")

        fetched = fc_result.get("result", {}).get("candidates", 0)
        return {
            "status": "ok", 
            "agent": self.name, 
            "inserted": total, 
            "fetched": fetched,
            "source": "real"
        }

    # ------------------------------------------------------------------
    # Mock-data path (default)
    # ------------------------------------------------------------------

    def _run_mock(self) -> Dict[str, Any]:
        records  = random.sample(_SCHOLARSHIP_POOL, random.randint(5, len(_SCHOLARSHIP_POOL)))
        inserted = 0
        for rec in records:
            rec.setdefault("type", "scholarship")
            rec["deadline"] = (datetime.utcnow() + timedelta(days=random.randint(45, 240))).strftime("%Y-%m-%d")
            rec["category"] = rec["type"]
            self.db.insert_opportunity(rec)
            inserted += 1
        self.logger.info("Mock: inserted %d scholarship/fellowship records.", inserted)
        return {"status": "ok", "agent": self.name, "inserted": inserted, "source": "mock"}
