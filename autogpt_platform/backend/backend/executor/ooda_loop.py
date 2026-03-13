"""
OODA Loop Framework
====================
Implements the Observe → Orient → Decide → Act (OODA) loop pattern for the
AutoGPT execution engine.

The OODA loop, developed by military strategist John Boyd, provides a principled
framework for adaptive, mission-driven decision-making.  Applied to AI agent
execution it means:

- **Observe**  – collect raw inputs and environmental signals.
- **Orient**   – contextualise observations: enrich, filter, and map to knowledge.
- **Decide**   – select the best next action from oriented understanding.
- **Act**      – execute the decided action and record its outcome.

The loop is *cyclic*: the result of each Act phase feeds back as new observations.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stage definition
# ---------------------------------------------------------------------------


class OODAStage(str, Enum):
    """The four stages of the OODA loop."""

    OBSERVE = "observe"
    ORIENT = "orient"
    DECIDE = "decide"
    ACT = "act"

    @property
    def next_stage(self) -> "OODAStage":
        """Return the next stage in the OODA cycle."""
        cycle = [
            OODAStage.OBSERVE,
            OODAStage.ORIENT,
            OODAStage.DECIDE,
            OODAStage.ACT,
        ]
        idx = cycle.index(self)
        return cycle[(idx + 1) % len(cycle)]

    @property
    def description(self) -> str:
        descriptions = {
            OODAStage.OBSERVE: "Gather raw inputs and environmental signals.",
            OODAStage.ORIENT: "Contextualise observations into actionable understanding.",
            OODAStage.DECIDE: "Select the best next action from oriented understanding.",
            OODAStage.ACT: "Execute the decided action and record its outcome.",
        }
        return descriptions[self]


# ---------------------------------------------------------------------------
# OODA Context model
# ---------------------------------------------------------------------------


class OODAContext(BaseModel):
    """
    Carries OODA loop state through an execution cycle.

    This model is designed to be attached to an ``ExecutionContext`` and updated
    as the execution progresses through the four OODA stages.
    """

    current_stage: OODAStage = Field(
        default=OODAStage.OBSERVE,
        description="The current OODA stage of this execution cycle.",
    )
    cycle_count: int = Field(
        default=0,
        description="Number of completed OODA cycles (loops) in this execution.",
    )
    observations: list[Any] = Field(
        default_factory=list,
        description="Raw data gathered during the Observe stage.",
    )
    orientation: Optional[dict[str, Any]] = Field(
        default=None,
        description="Contextualised model produced during the Orient stage.",
    )
    decision: Optional[str] = Field(
        default=None,
        description="The action selected during the Decide stage.",
    )
    act_results: list[Any] = Field(
        default_factory=list,
        description="Outcomes recorded during the Act stage.",
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the current OODA cycle started.",
    )

    def advance(self) -> "OODAContext":
        """
        Advance to the next OODA stage.

        When the ACT stage completes a full cycle, ``cycle_count`` is incremented
        and stage resets to OBSERVE for the next iteration.
        """
        if self.current_stage == OODAStage.ACT:
            return self.model_copy(
                update={
                    "current_stage": OODAStage.OBSERVE,
                    "cycle_count": self.cycle_count + 1,
                    "observations": [],
                    "orientation": None,
                    "decision": None,
                    "act_results": [],
                    "started_at": datetime.now(timezone.utc),
                }
            )
        return self.model_copy(update={"current_stage": self.current_stage.next_stage})

    def record_observation(self, data: Any) -> "OODAContext":
        """Append a new observation (Observe stage)."""
        return self.model_copy(update={"observations": [*self.observations, data]})

    def set_orientation(self, orientation: dict[str, Any]) -> "OODAContext":
        """Set the orientation model (Orient stage)."""
        return self.model_copy(update={"orientation": orientation})

    def set_decision(self, decision: str) -> "OODAContext":
        """Record the selected action (Decide stage)."""
        return self.model_copy(update={"decision": decision})

    def record_act_result(self, result: Any) -> "OODAContext":
        """Append an action outcome (Act stage)."""
        return self.model_copy(update={"act_results": [*self.act_results, result]})

    def log_stage(self) -> None:
        """Emit a structured log entry for the current stage."""
        logger.debug(
            "OODA[%s] cycle=%d stage=%s",
            id(self),
            self.cycle_count,
            self.current_stage.value,
            extra={
                "ooda_stage": self.current_stage.value,
                "ooda_cycle": self.cycle_count,
            },
        )


# ---------------------------------------------------------------------------
# Stage-to-block-category mapping helpers
# ---------------------------------------------------------------------------


def stage_label(stage: OODAStage) -> str:
    """Return a human-readable label for an OODA stage."""
    return stage.value.capitalize()


OODA_STAGE_ORDER: list[OODAStage] = [
    OODAStage.OBSERVE,
    OODAStage.ORIENT,
    OODAStage.DECIDE,
    OODAStage.ACT,
]
