"""
data_collection/api_agent.py
==============================
Real-data API agents using free, public APIs — no API key required.

Agents
------
RemotiveAPIAgent  – Fetches remote AI/Data Science jobs from remotive.com
ArXivAPIAgent     – Fetches recent AI/ML research papers from arXiv

Both agents normalise results to the same DB schema dict format:
  {title, description, type, category, source, location, eligibility,
   deadline, url}

Design
------
* Both extend BaseAgent so they plug directly into CoordinatorAgent.
* Both have ``run()`` → dict with inserted count (same contract as scrapers).
* Graceful fallback: if the API is unreachable, return status='api_unavailable'.
"""

import re
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from agents.base_agent import BaseAgent
from database.db_manager import DatabaseManager
import config

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Shared deduplication mixin
# ═══════════════════════════════════════════════════════════════════════════

class _DeduplicateMixin:
    """Mixin that provides URL-based deduplication on insert."""

    def _insert_deduped(self, records: List[Dict]) -> int:
        existing_urls = {
            row["url"]
            for row in self.db.execute(
                "SELECT url FROM opportunities WHERE url IS NOT NULL"
            )
        }
        inserted = 0
        seen_titles: set = set()
        for rec in records:
            url   = rec.get("url", "")
            title = rec.get("title", "").lower().strip()
            if url in existing_urls or title in seen_titles:
                continue
            seen_titles.add(title)
            if url:
                existing_urls.add(url)
            self.db.insert_opportunity(rec)
            inserted += 1

        if len(records) > 0 and inserted == 0:
            logger.info("All %d candidates from this source were already in the database.", len(records))
        elif inserted > 0:
            logger.info("Inserted %d new records (%d were duplicates).", inserted, len(records) - inserted)

        return inserted


# ═══════════════════════════════════════════════════════════════════════════
# Remotive API agent  –  remote AI/Data Science jobs
# ═══════════════════════════════════════════════════════════════════════════

class RemotiveAPIAgent(_DeduplicateMixin, BaseAgent):
    """
    Fetches remote tech jobs from the Remotive public API.

    API docs: https://remotive.com/api/remote-jobs
    No authentication required.

    Categories used
    ---------------
    data           → internship/job
    data-science   → internship/job
    machine-learning → internship/job
    """

    _CATEGORIES = ["data", "data-science", "machine-learning"]
    _API_URL    = config.REMOTIVE_API_URL

    def __init__(self, db: DatabaseManager):
        super().__init__("RemotiveAPIAgent", db)

    # ------------------------------------------------------------------
    # BaseAgent contract
    # ------------------------------------------------------------------

    def run(self, **kwargs) -> Dict[str, Any]:
        all_records: List[Dict] = []

        for category in self._CATEGORIES:
            jobs = self._fetch_category(category)
            self.logger.info("Remotive[%s] → %d jobs", category, len(jobs))
            all_records.extend(jobs)

        if not all_records:
            return {
                "status":   "api_unavailable",
                "agent":    self.name,
                "inserted": 0,
            }

        inserted = self._insert_deduped(all_records)
        self.logger.info("Remotive: inserted %d/%d records.", inserted, len(all_records))
        return {
            "status":     "ok",
            "agent":      self.name,
            "fetched":    len(all_records),
            "inserted":   inserted,
            "source":     "remotive_api",
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_category(self, category: str) -> List[Dict]:
        """Fetch one Remotive category and normalise to DB format."""
        try:
            resp = requests.get(
                self._API_URL,
                params={"category": category, "limit": 20},
                timeout=15,
            )
            resp.raise_for_status()
            jobs = resp.json().get("jobs", [])
            return [self._normalise(j) for j in jobs]
        except requests.exceptions.RequestException as exc:
            self.logger.warning("Remotive API error (%s): %s", category, exc)
            return []

    @staticmethod
    def _normalise(job: Dict) -> Dict:
        """Convert a Remotive job dict → observatory opportunity dict."""
        # Strip HTML tags from description
        desc_html = job.get("description", "")
        desc      = re.sub(r'<[^>]+>', ' ', desc_html)
        desc      = re.sub(r'\s{2,}', ' ', desc).strip()
        desc      = desc[:1200] if len(desc) > 1200 else desc

        # Map job type
        salary = job.get("salary", "")
        candidate_type = (
            "internship" if "intern" in job.get("job_type", "").lower()
            else "internship"   # treat all remote tech jobs as internship-equiv
        )

        return {
            "title":       job.get("title", "Untitled"),
            "description": desc or "Remote AI/Data Science position.",
            "type":        candidate_type,
            "category":    candidate_type,
            "source":      "Remotive.com",
            "location":    job.get("candidate_required_location") or "Remote / Global",
            "eligibility": f"Company: {job.get('company_name', 'N/A')}. "
                           f"Type: {job.get('job_type', 'full-time')}.",
            "deadline":    (datetime.utcnow() + timedelta(days=60)).strftime("%Y-%m-%d"),
            "url":         job.get("url", "https://remotive.com"),
        }


# ═══════════════════════════════════════════════════════════════════════════
# ArXiv API agent  –  recent AI/ML research papers → research_project opps
# ═══════════════════════════════════════════════════════════════════════════

class ArXivAPIAgent(_DeduplicateMixin, BaseAgent):
    """
    Fetches recent preprints from arXiv (cs.AI, cs.LG, stat.ML) and
    converts them into 'research_project' opportunities.

    API: https://export.arxiv.org/api/query (Atom/XML, no auth required)

    Value for the MAS
    -----------------
    Each paper represents an active research area. Users who match its
    abstract will be recommended to explore or cite it.
    """

    _ATOM_NS = "{http://www.w3.org/2005/Atom}"

    def __init__(self, db: DatabaseManager):
        super().__init__("ArXivAPIAgent", db)

    # ------------------------------------------------------------------
    # BaseAgent contract
    # ------------------------------------------------------------------

    def run(self, **kwargs) -> Dict[str, Any]:
        papers = self._fetch_papers()

        if not papers:
            return {
                "status":   "api_unavailable",
                "agent":    self.name,
                "inserted": 0,
            }

        inserted = self._insert_deduped(papers)
        self.logger.info("ArXiv: fetched %d, inserted %d new.", len(papers), inserted)
        return {
            "status":   "ok",
            "agent":    self.name,
            "fetched":  len(papers),
            "inserted": inserted,
            "source":   "arxiv_api",
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_papers(self) -> List[Dict]:
        """Call arXiv Atom API and parse XML."""
        params = {
            "search_query": config.ARXIV_SEARCH_QUERY,
            "start":        0,
            "max_results":  config.ARXIV_MAX_RESULTS,
            "sortBy":       "submittedDate",
            "sortOrder":    "descending",
        }
        try:
            resp = requests.get(config.ARXIV_API_URL, params=params, timeout=20)
            resp.raise_for_status()
            
            # Raw debug log for Render
            self.logger.info("ArXiv Raw Response (first 150 chars): %s", resp.text[:150].replace("\n", " "))
            
            return self._parse_atom(resp.text)
        except requests.exceptions.RequestException as exc:
            self.logger.warning("ArXiv API error: %s", exc)
            return []

    def _parse_atom(self, xml_text: str) -> List[Dict]:
        """Parse Atom XML response into opportunity dicts."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            self.logger.error("ArXiv XML parse error: %s", exc)
            return []

        ns   = self._ATOM_NS
        entries = root.findall(f"{ns}entry")
        self.logger.info("ArXiv XML: found %d <entry> tags.", len(entries))
        
        opps = []
        for entry in entries:
            title_el   = entry.find(f"{ns}title")
            summary_el = entry.find(f"{ns}summary")
            id_el      = entry.find(f"{ns}id")
            pub_el     = entry.find(f"{ns}published")

            title   = self._clean_text(title_el.text if title_el is not None else "")
            summary = self._clean_text(summary_el.text if summary_el is not None else "")
            url     = (id_el.text or "https://arxiv.org").strip()
            # Convert ArXiv abstract URL to PDF-friendly URL
            url     = url.replace("http://", "https://")

            # Published date → use as "deadline" (when the paper was posted)
            deadline = ""
            if pub_el is not None and pub_el.text:
                try:
                    pub_date = datetime.fromisoformat(pub_el.text[:10])
                    deadline = pub_date.strftime("%Y-%m-%d")
                except ValueError:
                    pass

            if not title or not summary:
                continue

            # Extract authors
            authors = [
                (a.find(f"{ns}name").text or "")
                for a in entry.findall(f"{ns}author")
                if a.find(f"{ns}name") is not None
            ]
            author_str = ", ".join(authors[:3])
            if len(authors) > 3:
                author_str += f" et al. ({len(authors)} authors)"

            opps.append({
                "title":       f"[ArXiv] {title}",
                "description": (
                    f"{summary}\n\nAuthors: {author_str}"
                ),
                "type":        "research_project",
                "category":    "research_project",
                "source":      "arXiv.org",
                "location":    "Remote / Global",
                "eligibility": "Open to all researchers and practitioners",
                "deadline":    deadline,
                "url":         url,
            })

        return opps

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""
        cleaned = re.sub(r'\s+', ' ', text).strip()
        return cleaned[:1200] if len(cleaned) > 1200 else cleaned
