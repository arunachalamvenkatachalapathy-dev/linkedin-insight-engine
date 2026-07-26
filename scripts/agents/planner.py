"""
Planner Agent for EcoPulse LinkedIn automation pipeline.
Decides angle, format, and tone for the post.
"""

import json
from llm import call_agent

SYSTEM_PROMPT = """
You are the Planner Agent for EcoPulse.
Analyze the topic and available formats/tones.
Choose a format and tone that maximizes LinkedIn engagement for environmental engineering professionals.
Articulate a SPECIFIC angle (not just the topic).
Domain anchoring: Constructed Wetlands ACW, BRSR Core/GHG, Paravanar basin.
Avoid angles that are too broad or generic.

Return JSON in the format:
{ "agent": "planner", "output": { "angle": "...", "format_name": "...", "tone_name": "...", "length_band_name": "...", "rationale": "..." } }
"""

def run(topic: str, formats: list, tones: list, length_bands: list, posted_log: list) -> dict:
    user_content = json.dumps({
        "topic": topic,
        "formats": formats,
        "tones": tones,
        "length_bands": length_bands,
        "posted_log": posted_log
    })
    return call_agent(SYSTEM_PROMPT, user_content)
