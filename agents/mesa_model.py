"""
agents/mesa_model.py
=====================
Mesa integration for the University Observatory MAS.

The guidelines (Section 6 - "Python Libraries and Tools") explicitly require
Mesa as the multi-agent system framework. This module wraps each
``BaseAgent`` instance in a ``mesa.Agent`` and orchestrates them through a
``mesa.Model`` with a deterministic ``BaseScheduler``, preserving the strict
pipeline order:

    [Scrapers] -> [Classification] -> [Clustering]
              -> [RelevanceMatcher] -> [Advisor] -> [Notification]

Each Mesa step calls the wrapped BaseAgent's ``execute`` method and stores
its result on the model's report dict. This gives us Mesa's standard MAS
semantics (Agents, Model, Scheduler, step()) without losing the existing
agent contracts.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import mesa

from agents.base_agent import BaseAgent

logger = logging.getLogger("MesaMASModel")


class MASAgentWrapper(mesa.Agent):
    """
    Mesa-Agent wrapper around a single ``BaseAgent``.

    On each ``step`` it invokes the inner agent's ``execute`` method,
    forwarding the model-level kwargs and writing the result back to
    the model's pipeline report.
    """

    def __init__(self, unique_id: int, model: "MesaMASModel", inner: BaseAgent):
        super().__init__(unique_id, model)
        self.inner = inner

    def step(self) -> None:
        kwargs = dict(self.model.step_kwargs)
        # Inject the matcher's data into the advisor, mirroring the
        # original coordinator's behavior.
        if self.inner.name == "AdvisorAgent":
            matcher_result = self.model.report["steps"].get("RelevanceMatcherAgent", {})
            if isinstance(matcher_result, dict):
                kwargs["matches"] = matcher_result.get("data", [])

        result = self.inner.execute(**kwargs)
        self.model.report["steps"][self.inner.name] = result


class MesaMASModel(mesa.Model):
    """
    Mesa Model orchestrating the full Observatory MAS.

    Parameters
    ----------
    agents_in_order : list[BaseAgent]
        Agents to step through in pipeline order.
    step_kwargs : dict, optional
        Keyword args forwarded to each agent's ``execute`` call
        (e.g. ``force_insert=True``).
    """

    def __init__(
        self,
        agents_in_order: List[BaseAgent],
        step_kwargs: Optional[Dict[str, Any]] = None,
    ):
        super().__init__()
        self.schedule    = mesa.time.BaseScheduler(self)
        self.step_kwargs = step_kwargs or {}
        self.report: Dict[str, Any] = {"status": "ok", "steps": {}}

        for idx, inner in enumerate(agents_in_order):
            wrapper = MASAgentWrapper(idx, self, inner)
            self.schedule.add(wrapper)

    def step(self) -> None:
        """Advance every wrapped agent by one step (one pipeline stage)."""
        self.schedule.step()

    def run(self) -> Dict[str, Any]:
        """Run a single pipeline pass: one step per agent, in order."""
        for wrapper in list(self.schedule.agents):
            wrapper.step()
        return self.report
