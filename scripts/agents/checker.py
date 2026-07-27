"""
Checker Agent for EcoPulse LinkedIn automation pipeline.
Combined fact-check and quality gate.
"""

import json
from llm import call_agent

from agents.instructor import QUALITY_CREDIBILITY_DIRECTIVE

SYSTEM_PROMPT = f"""
You are the Checker Agent for EcoPulse.

INSTRUCTOR MASTER DIRECTIVE:
{QUALITY_CREDIBILITY_DIRECTIVE}

Your job is to check factual grounding and basic post quality:
1. Factual Grounding: Core facts, metrics, and org names MUST come directly from source_facts or lateral_insight (or be framed as qualitative commentary/possibilities).
2. Sourcing Rule: Flag any unverified precise-sounding numbers not present in source_facts.
3. Concrete Anchor: Ensure there is at least ONE named real-world company, regulation, plant type, technology, or framework.
4. Rhythm: Flag if stock transition phrases like "This creates a paradox" or "The hidden paradox" appear.
5. Banned Phrases: Flag if it uses generic buzzwords ("in today's world", "game changer", "unlock the power", "as we navigate", "it is important to note", "revolutionize", "disrupt", "innovative solution", "cutting-edge", "dangerous architectural dependency", "the industry is rushing to").
6. Set passed=true if the post is factually grounded, contains a concrete anchor, has no unverified statistics, is free of banned phrases, and has a grounding_score >= 70.

Return JSON in the format:
{{ "agent": "checker", "output": {{ "passed": bool, "issues": [], "grounding_score": int }} }}
"""

def sounds_generic(post_text: str) -> bool:
    banned_phrases = [
        "in today's world", "game changer", "unlock the power", "as we navigate",
        "it is important to note", "revolutionize", "disrupt", "innovative solution", "cutting-edge"
    ]
    post_lower = post_text.lower()
    return any(phrase in post_lower for phrase in banned_phrases)

def within_length_band(post_text: str, length_band: dict) -> bool:
    min_words = length_band.get("min_words", 0)
    max_words = length_band.get("max_words", 10000)
    word_count = len(post_text.split())
    # Allow 20% tolerance below min and above max for Strategist agent post formatting
    tolerance_min = int(min_words * 0.8)
    tolerance_max = int(max_words * 1.25)
    return tolerance_min <= word_count <= tolerance_max

def run(post_text: str, source_facts: dict, lateral_insight: dict, format_spec: dict, tone: str, length_band: dict) -> dict:
    user_content = json.dumps({
        "post_text": post_text,
        "source_facts": source_facts,
        "lateral_insight": lateral_insight,
        "format_spec": format_spec,
        "tone": tone,
        "length_band": length_band
    })
    return call_agent(SYSTEM_PROMPT, user_content)
