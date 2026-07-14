from __future__ import annotations

import re

from .config import BUZZWORDS, ENVIRONMENT_TOPICS, Settings, settings, POLITICAL_KEYWORDS
from .models import Critique, Draft
from .state_store import StateStore


class CriticAgent:
    def __init__(self, store: StateStore, config: Settings = settings) -> None:
        self.store = store
        self.config = config

    def evaluate(self, draft: Draft, check_duplicate: bool = True) -> Critique:
        notes: list[str] = []
        text = draft.text.strip()

        if len(text) > self.config.char_limit:
            notes.append(f"Draft is {len(text)} characters; max limit is {self.config.char_limit}.")
        if len(text) < self.config.char_limit_min:
            notes.append(f"Draft is {len(text)} characters; min limit is {self.config.char_limit_min}.")
        if _contains_buzzword(text):
            notes.append("Remove generic hype or banned buzzwords.")
        if not _has_stat_or_concrete_fact(text):
            notes.append("Add at least one concrete statistic, number, or specific environmental fact.")
        if not _has_question(text):
            notes.append("Closer must include a question.")
        if not _has_cta(text):
            notes.append("Closer must explicitly ask readers to comment, share, or respond.")
        if not _has_hashtags(text):
            notes.append("Post must include 3-5 relevant hashtags at the end.")
        if _contains_political_content(text):
            notes.append("Post contains political keywords or government appraisal terms which are strictly banned.")
        if not _is_environment_topic(text):
            notes.append("Post must be about environment, nature, climate, or sustainability topics.")
        if not _is_india_focused(text):
            notes.append("Post must explicitly relate the topic to India or an Indian context.")
        if not _has_personal_pronouns(text):
            notes.append("Post must use personal pronouns (I, We, My, Our) to build an authentic connection.")
        if _has_bullets_or_lists(text):
            notes.append("Post must be written as a narrative story, without bullet points or numbered lists.")
        if _has_links(text):
            notes.append("Post must not contain URLs or links.")
        if not _has_hook(text):
            notes.append("Post must start with a short, punchy hook (under 150 characters) to grab attention.")
        if check_duplicate and self.store.fingerprint_seen(draft.topic_fingerprint, self.config.duplicate_window_days):
            notes.append("Topic fingerprint matches recent history.")
        if check_duplicate and draft.keywords:
            if _idea_repeated(draft.keywords, self.store.get_recent_keywords(self.config.duplicate_window_days)):
                notes.append("Core idea/keywords overlap >40% with a recent post. Choose a different angle.")

        return Critique(passed=not notes, notes=tuple(notes))


def _contains_buzzword(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in BUZZWORDS)


def _has_stat_or_concrete_fact(text: str) -> bool:
    return bool(re.search(
        r"\b\d+(?:[.,]\d+)?(?:\s*(?:%|x|degrees?|°C|°F|ppm|GtCO2|hectares?|km²|species|tons?|tonnes?"
        r"|million|billion|GW|MW|kWh|liters?|litres?|gallons?|acres?|meters?|metres?|feet|miles?)\b|\b)",
        text,
        re.IGNORECASE,
    ))


def _has_question(text: str) -> bool:
    return "?" in text


def _has_cta(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in ("comment", "share", "thoughts", "story", "perspective", "pick", "below"))


def _has_hashtags(text: str) -> bool:
    return text.count("#") >= 3


def _is_environment_topic(text: str) -> bool:
    """Check if the body (excluding hashtags) is about environment/nature topics."""
    # Strip hashtags
    body = re.sub(r"#\w+", "", text).lower()
    matches = sum(1 for topic in ENVIRONMENT_TOPICS if topic in body)
    return matches >= 2


def _contains_political_content(text: str) -> bool:
    lowered = text.lower()
    # Check for direct political keywords
    return any(f" {word} " in f" {lowered} " or f"\n{word} " in f" {lowered} " for word in POLITICAL_KEYWORDS)


def _is_india_focused(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in (
        "india", "indian", "delhi", "mumbai", "bengaluru", "chennai", "kolkata",
        "himalaya", "ganges", "monsoon", "bharat"
    ))


def _idea_repeated(new_keywords: tuple[str, ...], recent_keyword_sets: list[set[str]]) -> bool:
    """Check if the new draft's keywords overlap >40% with any recent post."""
    if not new_keywords or not recent_keyword_sets:
        return False
    new_set = set(new_keywords)
    for old_set in recent_keyword_sets:
        if not old_set:
            continue
        overlap = len(new_set & old_set)
        max_possible = max(len(new_set), len(old_set))
        if max_possible > 0 and overlap / max_possible > 0.4:
            return True
    return False


def _has_personal_pronouns(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in [" i ", " we ", " my ", " our ", "i've", "we've", "i'm", "we're"])


def _has_bullets_or_lists(text: str) -> bool:
    has_bullets = "\n-" in text or "\n•" in text
    has_numbers = bool(re.search(r"\n\s*\d+\.", text))
    return has_bullets or has_numbers


def _has_links(text: str) -> bool:
    lowered = text.lower()
    return "http" in lowered or "www." in lowered


def _has_hook(text: str) -> bool:
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return False
    return len(lines[0]) < 150
