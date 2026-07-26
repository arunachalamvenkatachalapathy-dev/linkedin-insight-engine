"""
Repetition Agent for EcoPulse LinkedIn automation pipeline.
Uses BOTH deterministic keyword fingerprinting AND LLM semantic check
to prevent content repetition.
"""

import json
import logging
import re
from collections import Counter
from llm import call_agent

log = logging.getLogger("ecopulse")

# Stop-words to ignore in fingerprinting
STOP_WORDS = frozenset([
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "and", "but", "or",
    "not", "no", "so", "if", "than", "too", "very", "just", "about",
    "this", "that", "these", "those", "it", "its", "we", "our", "you",
    "your", "they", "their", "how", "what", "which", "who", "when",
    "where", "why", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "only", "also", "new", "one",
])


def extract_keywords(text: str, top_n: int = 12) -> set:
    """Extract top N meaningful keywords from text."""
    words = re.findall(r'[a-z]{3,}', text.lower())
    filtered = [w for w in words if w not in STOP_WORDS]
    counts = Counter(filtered)
    return set(word for word, _ in counts.most_common(top_n))


def keyword_overlap_score(proposed_keywords: set, existing_keywords: set) -> float:
    """Calculate Jaccard similarity between two keyword sets."""
    if not proposed_keywords or not existing_keywords:
        return 0.0
    intersection = proposed_keywords & existing_keywords
    union = proposed_keywords | existing_keywords
    return len(intersection) / len(union) if union else 0.0


def deterministic_check(proposed_angle: str, proposed_headline: str, posted_log: list) -> dict:
    """
    Fast deterministic check using keyword fingerprinting.
    Returns is_duplicate=True if any recent post has >40% keyword overlap.
    """
    proposed_text = f"{proposed_angle} {proposed_headline}"
    proposed_kw = extract_keywords(proposed_text, top_n=12)
    
    # Check last 15 posts (broader window)
    recent_posts = posted_log[-15:] if len(posted_log) > 15 else posted_log
    
    max_overlap = 0.0
    most_similar = ""
    
    for entry in recent_posts:
        existing_text = f"{entry.get('headline', '')} {entry.get('angle', '')} {entry.get('topic', '')}"
        existing_kw = extract_keywords(existing_text, top_n=12)
        overlap = keyword_overlap_score(proposed_kw, existing_kw)
        
        if overlap > max_overlap:
            max_overlap = overlap
            most_similar = entry.get('headline', '')
    
    is_dup = max_overlap > 0.40  # 40% keyword overlap = duplicate
    
    log.info(f"Repetition deterministic check: overlap={max_overlap:.2f}, is_dup={is_dup}")
    if is_dup:
        log.warning(f"Most similar to: '{most_similar}' (overlap: {max_overlap:.2f})")
    
    return {
        "is_duplicate": is_dup,
        "overlap_score": max_overlap,
        "most_similar_headline": most_similar,
    }


SYSTEM_PROMPT = """
You are the Repetition Agent for EcoPulse.
Compare the proposed angle against ALL entries in the posted_log.
Check for thematic overlap — not just exact strings. Look for:
1. Same technology or engineering concept (e.g., "constructed wetlands" appearing in both)
2. Same narrative framing (e.g., both posts questioning the same trade-off)
3. Same industry/regulation angle (e.g., both about BRSR compliance)
4. Same geographic focus (e.g., both about Paravanar basin)

Be strict: even moderate thematic similarity means duplicate.
If it is a duplicate, suggest a COMPLETELY different angle — different technology, different geography, different narrative frame.

Return JSON:
{ "agent": "repetition", "output": { "is_duplicate": bool, "reason": "str", "suggestion": "str" } }
"""


def run(proposed_angle: str, proposed_headline: str, posted_log: list) -> dict:
    """
    Two-pass duplicate detection:
    1. Fast deterministic keyword check
    2. LLM semantic check (only if deterministic check passes)
    """
    # Pass 1: Deterministic keyword fingerprint
    det_result = deterministic_check(proposed_angle, proposed_headline, posted_log)
    
    if det_result["is_duplicate"]:
        return {
            "agent": "repetition",
            "output": {
                "is_duplicate": True,
                "reason": f"Keyword overlap {det_result['overlap_score']:.0%} with '{det_result['most_similar_headline']}'",
                "suggestion": "Choose a completely different technology, geography, and narrative frame.",
            }
        }
    
    # Pass 2: LLM semantic check (only recent 10 posts to save tokens)
    recent_log = posted_log[-10:] if len(posted_log) > 10 else posted_log
    user_content = json.dumps({
        "proposed_angle": proposed_angle,
        "proposed_headline": proposed_headline,
        "posted_log": recent_log
    })
    return call_agent(SYSTEM_PROMPT, user_content)
