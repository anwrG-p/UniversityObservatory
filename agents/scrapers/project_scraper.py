"""
agents/scrapers/project_scraper.py
===================================
ProjectScraperAgent - collects national and international research projects
(funding calls, collaborative research programmes, grant opportunities).
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from agents.base_agent import BaseAgent
from database.db_manager import DatabaseManager


_PROJECT_POOL: List[Dict] = [
    {
        "title":       "Horizon Europe - AI, Data and Robotics Call",
        "description": (
            "EU framework programme funding collaborative research projects in "
            "trustworthy AI, data spaces, and robotics. Consortia of 3+ partners "
            "from different EU member states. Budget: €1.5M-€8M per project."
        ),
        "source":      "European Commission",
        "location":    "European Union",
        "eligibility": "Research consortia (universities, RTOs, SMEs, industry)",
        "url":         "https://ec.europa.eu/info/funding-tenders/opportunities/portal/",
        "type":        "research_project",
    },
    {
        "title":       "ANR Generic Call - Artificial Intelligence",
        "description": (
            "French National Research Agency (ANR) funds 3-4 year research projects "
            "in AI, including foundational ML, AI for science, and AI ethics. "
            "Open to French laboratories and international collaborators."
        ),
        "source":      "Agence Nationale de la Recherche",
        "location":    "France",
        "eligibility": "Public research labs and accredited French institutions",
        "url":         "https://anr.fr/en/",
        "type":        "research_project",
    },
    {
        "title":       "NSF AI Research Institutes Program",
        "description": (
            "Five-year, $20M awards to establish multidisciplinary AI institutes "
            "in the United States. Themes include AI for materials, AI for climate, "
            "and trustworthy AI. Requires multi-university consortia."
        ),
        "source":      "National Science Foundation",
        "location":    "USA",
        "eligibility": "US universities and research institutions",
        "url":         "https://www.nsf.gov/cise/ai.jsp",
        "type":        "research_project",
    },
    {
        "title":       "DFG Priority Programme - Machine Learning",
        "description": (
            "German Research Foundation (DFG) priority programme on theoretical "
            "foundations of deep learning. Six-year programme funding ~30 individual "
            "projects across Germany."
        ),
        "source":      "Deutsche Forschungsgemeinschaft",
        "location":    "Germany",
        "eligibility": "PIs at German universities and Max Planck/Fraunhofer institutes",
        "url":         "https://www.dfg.de/en/research-funding",
        "type":        "research_project",
    },
    {
        "title":       "UKRI AI Hubs - Responsible AI",
        "description": (
            "UK Research and Innovation funds 5-year AI hubs on responsible and "
            "trustworthy AI deployment in healthcare, finance, and the public sector. "
            "Total programme budget: £80M."
        ),
        "source":      "UKRI",
        "location":    "United Kingdom",
        "eligibility": "UK universities with industry/public-sector partners",
        "url":         "https://www.ukri.org/opportunity/",
        "type":        "research_project",
    },
    {
        "title":       "JST CREST - AI for Science",
        "description": (
            "Japan Science and Technology Agency funds 5.5-year team projects "
            "applying AI to scientific discovery: materials, biology, climate. "
            "Budget up to ¥500M per team."
        ),
        "source":      "Japan Science and Technology Agency",
        "location":    "Japan",
        "eligibility": "Researchers at Japanese institutions, international co-PIs allowed",
        "url":         "https://www.jst.go.jp/kisoken/crest/en/",
        "type":        "research_project",
    },
    {
        "title":       "ERC Starting Grant - Computer Science & Informatics",
        "description": (
            "European Research Council awards up to €1.5M over 5 years to early-career "
            "researchers (2-7 years post-PhD) for frontier research projects. "
            "Highly prestigious; bottom-up themes."
        ),
        "source":      "European Research Council",
        "location":    "Europe (host institution)",
        "eligibility": "Researchers 2-7 years post-PhD, any nationality",
        "url":         "https://erc.europa.eu/apply-grant/starting-grant",
        "type":        "research_project",
    },
    {
        "title":       "DARPA AI Exploration (AIE) Program",
        "description": (
            "Fast-track 18-month exploratory research grants up to $1M on novel AI "
            "concepts: neuro-symbolic reasoning, adversarial robustness, machine "
            "common sense. Open to academia and small businesses."
        ),
        "source":      "DARPA",
        "location":    "USA",
        "eligibility": "US-based research organizations and SMEs",
        "url":         "https://www.darpa.mil/work-with-us/ai-next-campaign",
        "type":        "research_project",
    },
    {
        "title":       "CHIST-ERA Call on Trustworthy AI",
        "description": (
            "International call coordinated by 25+ European funding agencies. "
            "Funds transnational research consortia (3+ countries) on explainability, "
            "fairness, and robustness of AI systems."
        ),
        "source":      "CHIST-ERA",
        "location":    "Europe (multinational)",
        "eligibility": "Consortia from 3+ participating CHIST-ERA countries",
        "url":         "https://www.chistera.eu/",
        "type":        "research_project",
    },
    {
        "title":       "NSERC Alliance - AI for Industry",
        "description": (
            "Natural Sciences and Engineering Research Council of Canada co-funds "
            "applied research projects between Canadian universities and industry "
            "partners. 1-5 year projects, $20K-$1M/year."
        ),
        "source":      "NSERC",
        "location":    "Canada",
        "eligibility": "Canadian university researchers with industry partners",
        "url":         "https://www.nserc-crsng.gc.ca/Innovate-Innover/alliance-alliance/",
        "type":        "research_project",
    },
]


class ProjectScraperAgent(BaseAgent):
    """
    Collects national and international research-project funding calls.

    Mock-data mode samples from ``_PROJECT_POOL``. Real-data mode
    delegates to existing Firecrawl/RSS infrastructure when configured
    and falls back to the mock pool if no records are returned.
    """

    def __init__(self, db: DatabaseManager):
        super().__init__("ProjectScraperAgent", db)

    def run(self, force_insert: bool = False, **kwargs) -> Dict[str, Any]:
        import config
        if config.USE_REAL_DATA:
            return self._run_real(force_insert=force_insert)
        return self._run_mock()

    def _run_real(self, force_insert: bool = False) -> Dict[str, Any]:
        try:
            from data_collection.api_agent import ScholarshipRSSAgent
            rss = ScholarshipRSSAgent(self.db).execute(force_insert=force_insert)
            inserted = rss.get("inserted", 0)
            fetched  = rss.get("fetched", 0)
        except Exception as exc:
            self.logger.warning("Real project scrape failed (%s); falling back to mock.", exc)
            return self._run_mock()

        if inserted == 0:
            self.logger.info("Real sources returned 0 project records; running mock fallback.")
            return self._run_mock()

        return {
            "status":   "ok",
            "agent":    self.name,
            "inserted": inserted,
            "fetched":  fetched,
            "source":   "real",
        }

    def _run_mock(self) -> Dict[str, Any]:
        records = random.sample(_PROJECT_POOL, random.randint(5, len(_PROJECT_POOL)))
        existing_urls = {row["url"] for row in self.db.execute("SELECT url FROM opportunities WHERE url IS NOT NULL")}
        inserted = 0
        for rec in records:
            if rec.get("url", "") in existing_urls:
                continue
            rec.setdefault("type", "research_project")
            rec["deadline"] = (datetime.utcnow() + timedelta(days=random.randint(60, 365))).strftime("%Y-%m-%d")
            rec["category"] = rec["type"]
            self.db.insert_opportunity(rec)
            inserted += 1
        self.logger.info("Mock: inserted %d research-project records.", inserted)
        return {"status": "ok", "agent": self.name, "inserted": inserted, "source": "mock"}
