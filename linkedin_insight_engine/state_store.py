from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from .models import Draft, PendingApproval, PostStatus, SourceContext, new_token


class StateStore(Protocol):
    def fingerprint_seen(self, fingerprint: str, window_days: int) -> bool:
        ...

    def record_pending_approval(self, draft: Draft) -> PendingApproval:
        ...

    def get_pending_by_token(self, token: str) -> PendingApproval | None:
        ...

    def record_decision(self, token: str, status: PostStatus) -> PendingApproval:
        ...

    def record_publish(self, approval_id: str, response_status: int) -> None:
        ...

    def get_recent_keywords(self, window_days: int) -> list[set[str]]:
        ...


class InMemoryStateStore:
    """In-memory state store for testing."""

    def __init__(self) -> None:
        self._history: list[tuple[str, datetime]] = []
        self._pending: dict[str, PendingApproval] = {}
        self._idea_keywords: dict[str, list[str]] = {}

    def fingerprint_seen(self, fingerprint: str, window_days: int) -> bool:
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        return any(value == fingerprint and created_at >= cutoff for value, created_at in self._history)

    def record_pending_approval(self, draft: Draft) -> PendingApproval:
        approval = PendingApproval(
            id=str(uuid4()),
            token=new_token(),
            draft=draft,
            status=PostStatus.PENDING_APPROVAL,
        )
        self._pending[approval.token] = approval
        self._history.append((draft.topic_fingerprint, approval.created_at))
        if draft.keywords:
            self._idea_keywords[approval.id] = list(draft.keywords)
        return approval

    def get_pending_by_token(self, token: str) -> PendingApproval | None:
        return self._pending.get(token)

    def record_decision(self, token: str, status: PostStatus) -> PendingApproval:
        existing = self._pending[token]
        updated = PendingApproval(
            id=existing.id,
            token=existing.token,
            draft=existing.draft,
            status=status,
            created_at=existing.created_at,
            metadata=existing.metadata,
        )
        self._pending[token] = updated
        return updated

    def record_publish(self, approval_id: str, response_status: int) -> None:
        for token, approval in list(self._pending.items()):
            if approval.id == approval_id:
                status = PostStatus.PUBLISHED if 200 <= response_status < 300 else PostStatus.PUBLISH_FAILED
                self._pending[token] = PendingApproval(
                    id=approval.id,
                    token=approval.token,
                    draft=approval.draft,
                    status=status,
                    created_at=approval.created_at,
                    metadata={**approval.metadata, "publish_response_status": response_status},
                )
                return

    def get_recent_keywords(self, window_days: int) -> list[set[str]]:
        return [set(kws) for kws in self._idea_keywords.values()]


class JsonFileStateStore:
    """State store backed by a local JSON file. Designed for GitHub Actions workflows."""

    def __init__(self, path: str | Path | None = None) -> None:
        if path is None:
            path = Path(os.getenv("STATE_FILE", "data/state.json"))
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"pending": {}, "history": [], "idea_keywords": {}}

    def _save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, default=str)

    def fingerprint_seen(self, fingerprint: str, window_days: int) -> bool:
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        for entry in self._data["history"]:
            if entry["fingerprint"] == fingerprint:
                created = datetime.fromisoformat(entry["created_at"])
                if created >= cutoff:
                    return True
        return False

    def record_pending_approval(self, draft: Draft) -> PendingApproval:
        approval = PendingApproval(
            id=str(uuid4()),
            token=new_token(),
            draft=draft,
            status=PostStatus.PENDING_APPROVAL,
        )
        self._data["pending"][approval.token] = {
            "id": approval.id,
            "token": approval.token,
            "status": approval.status.value,
            "created_at": approval.created_at.isoformat(),
            "metadata": approval.metadata,
            "draft": {
                "text": draft.text,
                "topic_fingerprint": draft.topic_fingerprint,
                "image_path": draft.image_path,
                "keywords": list(draft.keywords),
                "idea_summary": draft.idea_summary,
                "sources": [
                    {"title": s.title, "summary": s.summary, "url": s.url}
                    for s in draft.sources
                ],
            },
        }
        self._data["history"].append({
            "id": approval.id,
            "fingerprint": draft.topic_fingerprint,
            "created_at": approval.created_at.isoformat(),
            "keywords": list(draft.keywords),
            "idea_summary": draft.idea_summary,
            "status": approval.status.value,
        })
        if draft.keywords:
            self._data["idea_keywords"][approval.id] = list(draft.keywords)
        self._save()
        return approval

    def get_pending_by_token(self, token: str) -> PendingApproval | None:
        entry = self._data["pending"].get(token)
        if entry is None:
            return None
        return _json_to_approval(entry)

    def record_decision(self, token: str, status: PostStatus) -> PendingApproval:
        entry = self._data["pending"].get(token)
        if entry is None:
            raise KeyError(token)
        entry["status"] = status.value
        for hist in self._data["history"]:
            if hist["id"] == entry["id"]:
                hist["status"] = status.value
                break
        self._save()
        return _json_to_approval(entry)

    def record_publish(self, approval_id: str, response_status: int) -> None:
        status = PostStatus.PUBLISHED if 200 <= response_status < 300 else PostStatus.PUBLISH_FAILED
        for token, entry in self._data["pending"].items():
            if entry["id"] == approval_id:
                entry["status"] = status.value
                entry["metadata"] = {**entry.get("metadata", {}), "publish_response_status": response_status}
                break
        for hist in self._data["history"]:
            if hist["id"] == approval_id:
                hist["status"] = status.value
                break
        self._save()

    def get_recent_keywords(self, window_days: int) -> list[set[str]]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        result: list[set[str]] = []
        for entry in self._data["history"]:
            created = datetime.fromisoformat(entry["created_at"])
            if created >= cutoff and entry.get("keywords"):
                result.append(set(entry["keywords"]))
        return result


def _json_to_approval(entry: dict[str, Any]) -> PendingApproval:
    draft_data = entry.get("draft", {})
    sources = tuple(
        SourceContext(
            title=s.get("title", ""),
            summary=s.get("summary", ""),
            url=s.get("url", ""),
        )
        for s in draft_data.get("sources", [])
    )
    created_at = entry.get("created_at")
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    elif created_at is None:
        created_at = datetime.now(timezone.utc)

    return PendingApproval(
        id=entry["id"],
        token=entry["token"],
        draft=Draft(
            text=draft_data.get("text", ""),
            topic_fingerprint=draft_data.get("topic_fingerprint", ""),
            image_path=draft_data.get("image_path", ""),
            keywords=tuple(draft_data.get("keywords", [])),
            idea_summary=draft_data.get("idea_summary", ""),
            sources=sources,
        ),
        status=PostStatus(entry["status"]),
        created_at=created_at,
        metadata=entry.get("metadata", {}),
    )


def get_state_store() -> StateStore:
    """Return the appropriate state store based on environment."""
    state_file = os.getenv("STATE_FILE", "data/state.json")
    if state_file:
        return JsonFileStateStore(state_file)
    return InMemoryStateStore()
