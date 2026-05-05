"""agents/scrapers/__init__.py"""
from .internship_scraper    import InternshipScraperAgent
from .scholarship_scraper   import ScholarshipScraperAgent
from .certification_scraper import CertificationScraperAgent
from .postdoc_scraper       import PostdocScraperAgent
from .project_scraper       import ProjectScraperAgent

__all__ = [
    "InternshipScraperAgent",
    "ScholarshipScraperAgent",
    "CertificationScraperAgent",
    "PostdocScraperAgent",
    "ProjectScraperAgent",
]
