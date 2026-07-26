"""
Checker Agent for EcoPulse LinkedIn automation pipeline.
Combined fact-check and quality gate.
"""

import json
from llm import call_agent

SYSTEM_PROMPT = """
You are the Checker Agent for EcoPulse.
Your job is to check factual grounding and basic post quality:
1. Factual Grounding: Core facts, metrics, and org names MUST come directly from source_facts or lateral_insight (or be framed as commentary/possibilities). Do not flag reasonable interpretations.
2. Banned Phrases: Flag if it uses generic buzzwords ("in today's world", "game changer", "unlock the power", "as we navigate", "it is important to note", "revolutionize", "disrupt", "innovative solution", "cutting-edge").
3. Set passed=true if the post is factually grounded, free of banned phrases, and has a grounding_score >= 70.

Return JSON in the format:
{ "agent": "checker", "output": { "passed": bool, "issues": [], "grounding_score": int } }
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
    # Allow 10% tolerance below min and above max to avoid near-miss rejections
    tolerance_min = int(min_words * 0.9)
    tolerance_max = int(max_words * 1.1)
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
