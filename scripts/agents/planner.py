"""
Planner Agent for EcoPulse LinkedIn automation pipeline.
Decides angle, format, and tone for the post.
"""

import json
from llm import call_agent
from agents.instructor import QUALITY_CREDIBILITY_DIRECTIVE

FORMATS = {
    "cost_tradeoff": {"name": "Cost vs Compliance Trade-Off", "desc": "Examines financial vs regulatory tension"},
    "data_led": {"name": "Data-Led Analysis", "desc": "Leads with specific metrics"},
    "myth_vs_reality": {"name": "Myth vs Reality", "desc": "Contrasts industry misconceptions with field data"},
    "mini_case_study": {"name": "Mini Case Study", "desc": "Focuses on a specific project/plant"},
    "question_led": {"name": "Question-Led Discussion", "desc": "Starts with a sharp technical question"}
}

TONES = {
    "analytical": "analytical and precise — like an engineer briefing peers",
    "blunt": "blunt and direct — short sentences, no hedging",
    "optimistic": "cautiously optimistic — acknowledges real progress without hype",
    "skeptical": "skeptical — questioning whether the obvious narrative holds up",
    "curious": "curious and exploratory — thinking out loud on the page"
}

LENGTH_BANDS = {
    "short": {"name": "short (100-155 words)", "min_words": 100, "max_words": 155},
    "medium": {"name": "medium (155-210 words)", "min_words": 155, "max_words": 210},
    "long": {"name": "long (210-280 words)", "min_words": 210, "max_words": 280}
}

SYSTEM_PROMPT = f"""
You are the Planner Agent for EcoPulse.
Analyze the topic and available formats/tones.

INSTRUCTOR MASTER DIRECTIVE:
{QUALITY_CREDIBILITY_DIRECTIVE}

YOUR JOB:
1. Choose a format and tone that maximizes LinkedIn engagement for environmental engineering professionals.
2. Articulate a SPECIFIC angle — not just the topic name. The angle must be a concrete engineering question, trade-off, or recent development.
3. The angle MUST be different from all angles in the posted_log. If a similar angle was already used, pick a fundamentally different perspective.

Return JSON in the format:
{{ "agent": "planner", "output": {{ "angle": "...", "format_name": "...", "tone_name": "...", "length_band_name": "...", "rationale": "..." }} }}
"""

def run(topic: str, formats: list = None, tones: list = None, length_bands: list = None, posted_log: list = None) -> dict:
    if formats is None:
        formats = list(FORMATS.keys())
    if tones is None:
        tones = list(TONES.keys())
    if length_bands is None:
        length_bands = list(LENGTH_BANDS.keys())
    if posted_log is None:
        posted_log = []

    recent_log = posted_log[-10:] if len(posted_log) > 10 else posted_log
    user_content = json.dumps({
        "topic": topic,
        "formats": formats,
        "tones": tones,
        "length_bands": length_bands,
        "posted_log_recent": recent_log,
        "total_posts_published": len(posted_log),
        "instruction": "Pick an angle that is COMPLETELY DIFFERENT from everything in posted_log_recent."
    })
    return call_agent(SYSTEM_PROMPT, user_content)
