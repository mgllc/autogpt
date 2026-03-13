"""
GovDOSS Compliance Utilities
=============================
Implements the GovDOSS KIS⁴ and SOA⁴ governance frameworks for the AutoGPT platform.

KIS⁴ – Keep It Simple, Secure, Sustainable, Scalable
SOA⁴ – Subjects, Objects, Authentication, Authorization, Approval, Action
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# KIS⁴ Framework
# ---------------------------------------------------------------------------


class KIS4Dimension(str, Enum):
    """The four KIS⁴ compliance dimensions."""

    SIMPLE = "simple"
    SECURE = "secure"
    SUSTAINABLE = "sustainable"
    SCALABLE = "scalable"


class KIS4Tag(BaseModel):
    """Metadata tag indicating which KIS⁴ dimensions a component satisfies."""

    dimensions: list[KIS4Dimension] = Field(
        default_factory=list,
        description="KIS⁴ dimensions satisfied by this component.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional notes about KIS⁴ compliance for this component.",
    )

    @property
    def is_compliant(self) -> bool:
        """Returns True if all four KIS⁴ dimensions are present."""
        return set(self.dimensions) == set(KIS4Dimension)

    def summary(self) -> str:
        dims = ", ".join(d.value.upper() for d in self.dimensions)
        return f"KIS⁴[{dims}]"


# ---------------------------------------------------------------------------
# SOA⁴ Governance – Audit Event Model
# ---------------------------------------------------------------------------


class SOA4Action(str, Enum):
    """SOA⁴ action types for audit events."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    APPROVE = "approve"
    REJECT = "reject"
    AUTHENTICATE = "authenticate"
    AUTHORIZE = "authorize"


class SOA4AuditEvent(BaseModel):
    """
    SOA⁴ Audit Event – captures all six SOA⁴ governance dimensions for a single
    system action:

    - **Subject**    – Who is performing the action (user_id / service name).
    - **Object**     – What resource is being acted upon (entity type + id).
    - **Authentication** – How the subject was authenticated.
    - **Authorization**  – The permission that was checked.
    - **Approval**       – Whether the action required and received approval.
    - **Action**         – The specific action taken.
    """

    # Subject
    subject_id: str = Field(description="Identifier of the subject (user or service).")
    subject_type: str = Field(
        default="user", description="Type of subject: 'user' or 'service'."
    )

    # Object
    object_type: str = Field(description="Type of the resource being acted upon.")
    object_id: Optional[str] = Field(
        default=None, description="Identifier of the resource being acted upon."
    )

    # Authentication
    auth_method: Optional[str] = Field(
        default=None,
        description="Authentication method used (e.g. 'jwt', 'api_key', 'oauth2').",
    )

    # Authorization
    permission: Optional[str] = Field(
        default=None,
        description="Permission / scope that was checked (e.g. 'graph:execute').",
    )

    # Approval
    required_approval: bool = Field(
        default=False,
        description="Whether the action required human-in-the-loop approval.",
    )
    approved: Optional[bool] = Field(
        default=None,
        description="Approval outcome when required_approval is True.",
    )

    # Action
    action: SOA4Action = Field(description="The SOA⁴ action that was performed.")
    action_detail: Optional[str] = Field(
        default=None, description="Additional context about the action."
    )

    # Metadata
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the event.",
    )
    outcome: str = Field(
        default="success",
        description="Outcome of the action: 'success', 'failure', or 'pending'.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional structured metadata for the event.",
    )

    def log(self) -> None:
        """Emit the audit event to the structured logger."""
        logger.info(
            "SOA4_AUDIT subject=%s(%s) object=%s/%s action=%s outcome=%s",
            self.subject_type,
            self.subject_id,
            self.object_type,
            self.object_id or "-",
            self.action.value,
            self.outcome,
            extra={
                "govdoss_audit": True,
                "soa4": self.model_dump(mode="json"),
            },
        )


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def record_execution_audit(
    *,
    user_id: str,
    graph_id: str,
    graph_exec_id: str,
    action: SOA4Action = SOA4Action.EXECUTE,
    outcome: str = "success",
    detail: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> SOA4AuditEvent:
    """Create and log a SOA⁴ audit event for a graph execution step."""
    event = SOA4AuditEvent(
        subject_id=user_id,
        subject_type="user",
        object_type="graph_execution",
        object_id=graph_exec_id,
        action=action,
        action_detail=detail or f"graph={graph_id}",
        outcome=outcome,
        metadata=metadata or {},
    )
    event.log()
    return event
