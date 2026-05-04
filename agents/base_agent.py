"""
agents/base_agent.py
====================
Abstract base class that every agent inherits from.
Enforces the Liskov Substitution Principle and Interface Segregation
by providing a minimal, stable contract.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict

from database.db_manager import DatabaseManager


class BaseAgent(ABC):
    """
    Base contract for all agents in the MAS.

    Subclasses MUST implement :meth:`run`.
    They MAY override :meth:`report` for custom status.
    """

    def __init__(self, name: str, db: DatabaseManager):
        self.name   = name
        self.db     = db
        self.logger = logging.getLogger(self.name)
        self._last_run_duration: float = 0.0
        self._last_result: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @abstractmethod
    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the agent's primary task.

        Returns
        -------
        dict
            At minimum: ``{"status": "ok"|"error", "agent": self.name, ...}``
        """

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Wrapper around :meth:`run` that adds timing and logging."""
        self.logger.info("[%s] Starting …", self.name)
        t0 = time.perf_counter()
        try:
            result = self.run(**kwargs)
            self._last_result = result
        except Exception as exc:          # noqa: BLE001
            self.logger.exception("[%s] Failed: %s", self.name, exc)
            result = {"status": "error", "agent": self.name, "error": str(exc)}
            self._last_result = result
        finally:
            self._last_run_duration = time.perf_counter() - t0
            self.logger.info(
                "[%s] Done in %.2fs", self.name, self._last_run_duration
            )
        return result

    def report(self) -> Dict[str, Any]:
        """Return the last run's status and timing."""
        return {
            "agent":    self.name,
            "duration": round(self._last_run_duration, 3),
            "result":   self._last_result,
        }

    def __repr__(self) -> str:
        return f"<Agent: {self.name}>"
