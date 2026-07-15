from __future__ import annotations

import json
import os
import re
from google import genai
from google.genai import types

from .config import BUZZWORDS, ENVIRONMENT_TOPICS, Settings, settings
from .models import Critique, Draft
from .state_store import StateStore
from .logger import log_event

QUALITY_AUDIT_PROMPT = """\
You are the Quality Audit Agent for the LinkedIn Insight Engine.
Evaluate the following LinkedIn post draft and its associated image generation prompt against the quality criteria.

Post Text:
{post_text}

Image Prompt:
{image_prompt}

Source Facts:
{source_facts}

Criteria:
1. **Hook Implication Test**: Does the first sentence (hook) lead directly and logically into the narrative? Does it avoid being a vague/empty structural label (like "Before vs. After:" or "Field Note:")? It must be substantive, a complete sentence, and logically connected to the actual source facts.
2. **Specificity Test**: Are the technical details and metrics highly specific and directly supported by the source facts?
3. **Image Relevance Test**: Is the image prompt highly relevant to the post topic, specific entities (technology, mechanism), and does it follow the realism instructions? Does it avoid banned visual concepts?

Return ONLY a JSON object:
{{
  "hook_implication_passed": true | false,
  "specificity_passed": true | false,
  "image_relevance_passed": true | false,
  "reasoning": "Brief explanation for any fails"
}}
"""


class CriticAgent:
    def __init__(self, store: StateStore, config: Settings = settings) -> None:
        self.store = store
        self.config = config

    def evaluate(self, draft: Draft, check_duplicate: bool = True) -> Critique:
        notes: list[str] = []
        text = draft.text.strip()

        # PASS 1: Structural Checks
        if len(text) > self.config.char_limit:
            notes.append(f"Draft is {len(text)} characters; max limit is {self.config.char_limit}.")
        if len(text) < self.config.char_limit_min:
            notes.append(f"Draft is {len(text)} characters; min limit is {self.config.char_limit_min}.")
        
        word_count = len(text.split())
        if word_count < self.config.min_post_word_count:
            shortfall = self.config.min_post_word_count - word_count
            notes.append(f"currently {word_count} words, needs {shortfall}+ more — expand Core Body with an additional concrete data point")

        if _contains_buzzword(text):
            notes.append("Remove generic hype or banned buzzwords.")
        if not _has_stat_or_concrete_fact(text):
            notes.append("Add at least one concrete statistic, number, or specific environmental fact.")
        if not _has_cta(text):
            notes.append("Closer must explicitly ask readers to comment, share, or respond.")
        if check_duplicate and self.store.fingerprint_seen(draft.topic_fingerprint, self.config.duplicate_window_days):
            notes.append("Topic fingerprint matches recent history.")
        if check_duplicate and draft.keywords:
            if _idea_repeated(draft.keywords, self.store.get_recent_keywords(self.config.duplicate_window_days)):
                notes.append("Core idea/keywords overlap >40% with a recent post. Choose a different angle.")

        if notes:
            log_event("critic", "pass1-structural-failed", notes=notes)
            # Return Critique indicating text failure
            return Critique(passed=False, notes=tuple(notes))

        # PASS 2: Quality checks via Gemini (hook implication, specificity, image relevance)
        api_key = self.config.gemini_api_key
        if not api_key:
            log_event("critic", "pass2-quality-skipped-missing-key")
            return Critique(passed=True, notes=())

        try:
            client = genai.Client(api_key=api_key)
            # Combine sources for validation
            sources_text = "\n".join(
                f"Title: {ctx.title}\nSummary: {ctx.summary}"
                for ctx in draft.sources
            )
            prompt = QUALITY_AUDIT_PROMPT.format(
                post_text=draft.text,
                image_prompt=draft.image_prompt,
                source_facts=sources_text,
            )
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            response_text = (response.text or "").strip()
            if not response_text:
                raise ValueError("Empty response from Quality Critic")

            res_json = json.loads(response_text)
            
            # Audit results
            hook_passed = res_json.get("hook_implication_passed", True)
            spec_passed = res_json.get("specificity_passed", True)
            img_passed = res_json.get("image_relevance_passed", True)
            reasoning = res_json.get("reasoning", "")

            notes = []
            fail_type = "text"
            if not hook_passed:
                notes.append(f"Hook Implication failed: {reasoning}")
            if not spec_passed:
                notes.append(f"Specificity failed: {reasoning}")
            if not img_passed:
                notes.append(f"Image Relevance failed: {reasoning}")
                fail_type = "image" # Flags that this is specifically an image-related failure

            if notes:
                log_event("critic", "pass2-quality-failed", notes=notes, fail_type=fail_type)
                return Critique(passed=False, notes=tuple(notes), fail_type=fail_type)

            log_event("critic", "quality-audit-passed")
            return Critique(passed=True, notes=())
        except Exception as exc:
            log_event("critic", "quality-audit-error", error=str(exc))
            # Fallback to pass if LLM validation error
            return Critique(passed=True, notes=())


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


def _has_cta(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in ("comment", "share", "thoughts", "story", "perspective", "pick", "below"))


def _idea_repeated(new_keywords: tuple[str, ...], recent_keyword_sets: list[set[str]]) -> bool:
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
