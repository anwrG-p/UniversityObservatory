"""
data_collection/firecrawl_agent.py
====================================
Firecrawl-based scraper agents using a **self-hosted** Firecrawl instance.

Self-hosting
------------
  git clone https://github.com/firecrawl/firecrawl
  cd firecrawl
  cp apps/api/.env.example apps/api/.env  # add OPENAI_API_KEY if you want LLM extract
  docker compose up                        # starts on http://localhost:3002

These agents call /v1/scrape and /v1/batch/scrape REST endpoints.
No third-party SDK is required — only the `requests` library.

Architecture
------------
FirecrawlClient          – thin HTTP wrapper (reusable)
FirecrawlScraperBase     – BaseAgent subclass with shared markdown parser
InternshipFirecrawlAgent – targets AI/tech job listing pages
ScholarshipFirecrawlAgent– targets scholarship listing pages
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

from agents.base_agent import BaseAgent
from database.db_manager import DatabaseManager
import config

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Firecrawl HTTP client
# ═══════════════════════════════════════════════════════════════════════════

class FirecrawlClient:
    """
    Minimal HTTP client for a self-hosted Firecrawl instance.

    Endpoints used
    --------------
    POST /v1/scrape        – single URL → markdown
    POST /v1/batch/scrape  – multiple URLs (sequential fallback)

    Parameters
    ----------
    base_url : str
        URL of the self-hosted Firecrawl server (default: localhost:3002).
    api_key : str
        Bearer token.  For self-hosted instances any non-empty string works
        unless you added auth to your .env.
    timeout : int
        Per-request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        timeout: int = None,
    ):
        self.base_url = (base_url or config.FIRECRAWL_URL).rstrip("/")
        self.api_key  = api_key or config.FIRECRAWL_API_KEY
        self.timeout  = timeout or config.FIRECRAWL_TIMEOUT
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
        })

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True if the Firecrawl instance is reachable."""
        if "api.firecrawl.dev" in self.base_url:
            return True
        try:
            r = self._session.get(f"{self.base_url}/health", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Single URL scrape
    # ------------------------------------------------------------------

    def scrape(
        self,
        url: str,
        only_main_content: bool = True,
        wait_for: int = 1500,
        formats: List[str] = None,
    ) -> Optional[str]:
        """
        Scrape one URL and return its markdown text, or None on failure.

        Parameters
        ----------
        url               : target page
        only_main_content : strip nav/footer/ads (default True)
        wait_for          : milliseconds to wait for JS rendering
        formats           : list of output formats; we only need 'markdown'
        """
        payload = {
            "url":             url,
            "formats":         formats or ["markdown"],
            "onlyMainContent": only_main_content,
            "waitFor":         wait_for,
        }
        try:
            r = self._session.post(
                f"{self.base_url}/v1/scrape",
                json=payload,
                timeout=self.timeout,
            )
            r.raise_for_status()
            resp = r.json()
            # Firecrawl v1 response: {"success": true, "data": {"markdown": "..."}}
            data = resp.get("data") or resp
            return data.get("markdown") or data.get("content", "")
        except requests.exceptions.Timeout:
            logger.warning("Firecrawl timeout scraping: %s", url)
        except requests.exceptions.HTTPError as exc:
            logger.warning("Firecrawl HTTP %s scraping: %s", exc.response.status_code, url)
        except Exception as exc:
            logger.warning("Firecrawl error scraping %s: %s", url, exc)
        return None

    # ------------------------------------------------------------------
    # Batch scrape (sequential under the hood for self-hosted)
    # ------------------------------------------------------------------

    def batch_scrape(
        self,
        urls: List[str],
        only_main_content: bool = True,
        wait_for: int = 1500,
    ) -> List[Tuple[str, Optional[str]]]:
        """
        Scrape multiple URLs.

        Returns a list of (url, markdown_or_None) tuples.
        First tries the native /v1/batch/scrape endpoint; if that fails,
        falls back to sequential individual scrapes.
        """
        # Try native batch endpoint
        try:
            payload = {
                "urls":            urls,
                "formats":         ["markdown"],
                "onlyMainContent": only_main_content,
                "waitFor":         wait_for,
            }
            r = self._session.post(
                f"{self.base_url}/v1/batch/scrape",
                json=payload,
                timeout=self.timeout * len(urls),
            )
            if r.status_code == 200:
                batch_data = r.json().get("data", [])
                results = []
                for i, item in enumerate(batch_data):
                    url = urls[i] if i < len(urls) else ""
                    md  = item.get("markdown") or item.get("content", "")
                    results.append((url, md or None))
                return results
        except Exception as exc:
            logger.debug("Batch endpoint unavailable (%s), falling back to sequential.", exc)

        # Sequential fallback
        return [(url, self.scrape(url, only_main_content=only_main_content, wait_for=wait_for))
                for url in urls]


# ═══════════════════════════════════════════════════════════════════════════
# Markdown → opportunity record parser
# ═══════════════════════════════════════════════════════════════════════════

class MarkdownParser:
    """
    Heuristic parser that converts Firecrawl markdown output into a list
    of structured opportunity dicts compatible with the DB schema.

    Strategy
    --------
    1. Split markdown into "blocks" separated by H2/H3 headings.
    2. Each block → one opportunity candidate.
    3. Extract URL, date, location from text via regex.
    4. Filter out blocks that are too short to be real listings.
    """

    # Regex patterns
    _URL_RE      = re.compile(r'https?://[^\s\)\]"\']+')
    _DATE_RE     = re.compile(
        r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|'
        r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
        r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|'
        r'Dec(?:ember)?)\s+\d{1,2},?\s+\d{4})\b',
        re.IGNORECASE,
    )
    _LOCATION_KW = re.compile(
        r'\b(remote|online|global|usa|uk|canada|france|germany|europe|'
        r'switzerland|usa|australia|worldwide|international|'
        r'london|paris|berlin|munich|zurich|toronto|new york|'
        r'san francisco|boston|cambridge|oxford)\b',
        re.IGNORECASE,
    )
    _HEADING_RE  = re.compile(r'^#{1,4}\s+(.+)$', re.MULTILINE)
    _MIN_DESC_LEN = 60   # discard blocks shorter than this

    @classmethod
    def _is_valid_block(cls, block: str) -> bool:
        """Heuristic: must have a header-like line OR contains keywords + minimum length"""
        lines = block.split("\n")
        has_header = any(line.strip().startswith(("#", "**", "__")) for line in lines[:2])
        has_keywords = any(k in block.lower() for k in ["internship", "scholarship", "fellowship", "award", "program"])
        return (has_header or has_keywords) and len(block) > cls._MIN_DESC_LEN

    @classmethod
    def parse(cls, markdown: str, source_url: str, default_type: str) -> List[Dict]:
        """
        Parse markdown into a list of opportunity dicts.

        Parameters
        ----------
        markdown     : raw markdown string from Firecrawl
        source_url   : page URL (used as fallback link)
        default_type : 'internship' | 'scholarship' | 'course' | etc.
        """
        if not markdown:
            return []

        blocks = cls._split_into_blocks(markdown)
        records = []
        seen_titles: set = set()

        for title, body in blocks:
            if not cls._is_valid_block(body):
                logger.debug("  Skipping block '%s' (too short or irrelevant)", title[:30])
                continue
            norm_title = title.strip().lower()
            if not norm_title or norm_title in seen_titles:
                logger.debug("  Skipping block '%s' (duplicate title in this page)", title[:30])
                continue
            seen_titles.add(norm_title)

            url      = cls._extract_url(body) or source_url
            deadline = cls._extract_deadline(body)
            location = cls._extract_location(body) or "Global / Online"
            desc     = cls._clean_desc(body)

            records.append({
                "title":       title.strip(),
                "description": desc,
                "type":        default_type,
                "category":    default_type,
                "source":      cls._domain(source_url),
                "location":    location,
                "eligibility": "",
                "deadline":    deadline,
                "url":         url,
            })

        return records

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @classmethod
    def _split_into_blocks(cls, md: str) -> List[Tuple[str, str]]:
        """Split markdown by H1–H3 headings → list of (title, body)."""
        parts   = cls._HEADING_RE.split(md)
        # parts[0] = text before first heading (discard)
        # then alternating: title, body, title, body …
        blocks  = []
        i = 1
        while i + 1 < len(parts):
            title = parts[i].strip()
            body  = parts[i + 1].strip()
            blocks.append((title, body))
            i += 2
        return blocks

    @classmethod
    def _extract_url(cls, text: str) -> Optional[str]:
        urls = cls._URL_RE.findall(text)
        # Prefer non-image, non-social URLs
        for u in urls:
            if any(skip in u for skip in ["twitter", "facebook", "linkedin", "instagram", ".png", ".jpg", ".svg"]):
                continue
            return u.rstrip(")")
        return None

    @classmethod
    def _extract_deadline(cls, text: str) -> str:
        m = cls._DATE_RE.search(text)
        if m:
            raw = m.group(0)
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%B %d, %Y", "%B %d %Y"):
                try:
                    return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    pass
            return raw
        # No date found → rolling deadline
        return (datetime.utcnow() + timedelta(days=90)).strftime("%Y-%m-%d")

    @classmethod
    def _extract_location(cls, text: str) -> Optional[str]:
        m = cls._LOCATION_KW.search(text)
        return m.group(0).title() if m else None

    @classmethod
    def _clean_desc(cls, text: str) -> str:
        """Remove markdown links/images and trim to reasonable length."""
        cleaned = re.sub(r'!\[.*?\]\(.*?\)', '', text)          # images
        cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', cleaned)  # links
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)             # excess newlines
        cleaned = cleaned.strip()
        return cleaned[:1200] if len(cleaned) > 1200 else cleaned

    @staticmethod
    def _domain(url: str) -> str:
        m = re.search(r'https?://(?:www\.)?([^/]+)', url)
        return m.group(1) if m else url


# ═══════════════════════════════════════════════════════════════════════════
# Base Firecrawl scraper agent
# ═══════════════════════════════════════════════════════════════════════════

class FirecrawlScraperBase(BaseAgent):
    """
    Abstract base for Firecrawl-powered scraper agents.

    Subclasses set:
    - ``_TARGET_URLS``  : list of pages to scrape
    - ``_OPPORTUNITY_TYPE`` : DB type string
    """

    _TARGET_URLS: List[str]       = []
    _OPPORTUNITY_TYPE: str        = "internship"

    def __init__(self, name: str, db: DatabaseManager):
        super().__init__(name, db)
        self._client = FirecrawlClient()
        self._parser = MarkdownParser()

    # ------------------------------------------------------------------
    # BaseAgent contract
    # ------------------------------------------------------------------

    def run(self, **kwargs) -> Dict[str, Any]:
        if not self._client.is_available():
            self.logger.warning(
                "Firecrawl not available at %s — returning empty result. "
                "Start Firecrawl with: docker compose up (in the firecrawl repo).",
                config.FIRECRAWL_URL,
            )
            return {
                "status": "firecrawl_unavailable",
                "agent":  self.name,
                "inserted": 0,
            }

        self.logger.info("Scraping %d URLs via Firecrawl…", len(self._TARGET_URLS))
        scraped_pages = self._client.batch_scrape(self._TARGET_URLS)

        all_records: List[Dict] = []
        for url, markdown in scraped_pages:
            if not markdown:
                self.logger.warning("No content from %s", url)
                continue
            records = MarkdownParser.parse(markdown, url, self._OPPORTUNITY_TYPE)
            if not records:
                self.logger.info("  %s → 0 candidates found (check page structure)", url)
            else:
                self.logger.info("  %s → %d candidates extracted", url, len(records))
            all_records.extend(records)

        inserted = self._insert_deduped(all_records)
        return {
            "status":       "ok",
            "agent":        self.name,
            "urls_scraped": len(self._TARGET_URLS),
            "candidates":   len(all_records),
            "inserted":     inserted,
            "source":       "firecrawl",
        }

    # ------------------------------------------------------------------
    # Deduplication helper
    # ------------------------------------------------------------------

    def _insert_deduped(self, records: List[Dict]) -> int:
        """Insert records, skipping those whose URL already exists in DB."""
        existing_urls = {
            row["url"]
            for row in self.db.execute("SELECT url FROM opportunities WHERE url IS NOT NULL")
        }
        inserted = 0
        seen: set = set()
        for rec in records:
            url = rec.get("url", "")
            title_key = rec.get("title", "").lower().strip()
            if url in existing_urls or title_key in seen:
                continue
            seen.add(title_key)
            if url:
                existing_urls.add(url)
            self.db.insert_opportunity(rec)
            inserted += 1
        
        if len(records) > 0 and inserted == 0:
            logger.info("All %d candidates were already in the database (deduplicated).", len(records))
        elif inserted > 0:
            logger.info("Successfully inserted %d new records (%d were duplicates).", inserted, len(records) - inserted)
            
        return inserted


# ═══════════════════════════════════════════════════════════════════════════
# Concrete agents
# ═══════════════════════════════════════════════════════════════════════════

class InternshipFirecrawlAgent(FirecrawlScraperBase):
    """
    Scrapes AI/tech internship and job listings using Firecrawl.

    Targets
    -------
    - ai-jobs.net          : clean job listings, JS-light
    - euraxess.ec.europa.eu: EU research positions (JS-rendered → Firecrawl handles it)
    """

    _TARGET_URLS      = config.INTERNSHIP_SCRAPE_URLS
    _OPPORTUNITY_TYPE = "internship"

    def __init__(self, db: DatabaseManager):
        super().__init__("InternshipFirecrawlAgent", db)


class ScholarshipFirecrawlAgent(FirecrawlScraperBase):
    """
    Scrapes scholarship and fellowship listings using Firecrawl.

    Targets
    -------
    - scholars4dev.com: scholarship aggregator for developing-country students
    - daad.de         : German Academic Exchange Service scholarships
    """

    _TARGET_URLS      = config.SCHOLARSHIP_SCRAPE_URLS
    _OPPORTUNITY_TYPE = "scholarship"

    def __init__(self, db: DatabaseManager):
        super().__init__("ScholarshipFirecrawlAgent", db)
