from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class ApprovalDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"


class PostStatus(str, Enum):
    DRAFTED = "drafted"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    NEEDS_REWRITE = "needs_rewrite"
    PUBLISH_FAILED = "publish_failed"


@dataclass(frozen=True)
class SourceContext:
    title: str
    summary: str
    url: str = ""


@dataclass(frozen=True)
class Draft:
    text: str
    topic_fingerprint: str
    sources: tuple[SourceContext, ...] = ()
    image_path: str = ""
    keywords: tuple[str, ...] = ()
    idea_summary: str = ""


@dataclass(frozen=True)
class Critique:
    passed: bool
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class PendingApproval:
    id: str
    token: str
    draft: Draft
    status: PostStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ApprovalCheck:
    name: str
    emoji: str
    passed: bool
    reasoning: str


@dataclass(frozen=True)
class ApprovalReport:
    checks: tuple[ApprovalCheck, ...]
    overall_passed: bool
    summary: str


def new_token() -> str:
    return uuid4().hex
