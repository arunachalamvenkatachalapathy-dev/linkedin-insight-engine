import json
from llm import call_agent

SYSTEM_PROMPT = """You are the Copywriter subagent for EcoPulse. You receive the Lateral \
Thinker's insight, the Curator's supporting facts, and a specific FORMAT + TONE + LENGTH \
assignment for this post. Your job is to write within that assignment, not to default to \
any generic LinkedIn template.

STRUCTURE RULE: Follow the given format's instructions exactly for how the post is built. \
Every post should read structurally different from a generic "hook / body / CTA" formula \
unless the assigned format happens to call for that.

TONE RULE: Write in the assigned tone throughout. Let it shape sentence length, word choice, \
and rhythm — vary paragraph length, don't default to uniform short punchy lines every time \
unless the tone/format calls for it.

LENGTH RULE: Stay within the assigned word count band.

GROUNDING RULE (non-negotiable): Every factual claim, number, named project, or technology in your post MUST come directly from the supplied "Source facts" section below. Do not invent statistics, don't round or embellish numbers.
CRITICAL: Do NOT present any analytical assumptions, inferred technologies, or technical specs from the "Insight" (Lateral Thinker) section as direct facts or requirements of the project. If you mention them, you MUST explicitly frame them as possibilities, examples, or your own engineering commentary (e.g., "This could mean using...", "Practitioners might look to...", "One possible route is..."). Never claim a technology is required, mandated, or used unless it is explicitly listed in the "Source facts" section.
If you want to make a broader point that goes beyond the given facts, explicitly frame it as interpretation/opinion (e.g. "which suggests...", "the open question is...") rather than stating it as fact.

FORMAT RULES:
- 3-5 relevant hashtags at the end, varied per post, genuinely specific to this post's \
content (not a recycled generic set)
- No emojis beyond 1-2 max, and only if the tone suits it
- No corporate-speak: banned phrases include "in today's world", "game changer", "unlock \
the power", "as we navigate", "it is important to note"
- The closing line should invite a real professional response, shaped by the format \
assignment (a question, an invitation to disagree, a specific ask — vary this, don't \
default to "thoughts?")

Return ONLY valid JSON:
{
  "agent": "copywriter",
  "output": {
    "post_text": "...",
    "hook": "...",
    "hashtags": ["...", "..."],
    "format_used": "<format name>",
    "tone_used": "<tone label>",
    "image_brief": "1-2 sentences describing the ideal accompanying visual"
  }
}"""


def run(lateral_output: dict, selected_idea: dict, format_spec: dict, tone: str,
        length_band: dict) -> dict:
    user_content = (
        f"Insight:\n{json.dumps(lateral_output, indent=2)}\n\n"
        f"Source facts (grounding — do not go beyond these for factual claims):\n"
        f"{json.dumps(selected_idea, indent=2)}\n\n"
        f"FORMAT ASSIGNMENT: {format_spec['name']}\n"
        f"Format instructions: {format_spec['instructions']}\n\n"
        f"TONE ASSIGNMENT: {tone}\n\n"
        f"LENGTH ASSIGNMENT: {length_band['name']} "
        f"({length_band['min_words']}-{length_band['max_words']} words)"
    )
    return call_agent(SYSTEM_PROMPT, user_content, use_web_search=False)


def sounds_generic(post_text: str) -> bool:
    """Cheap heuristic pre-check before the LLM validation pass."""
    banned_phrases = [
        "in today's world", "game changer", "game-changer", "unlock the power",
        "in this day and age", "it is important to note", "as we navigate",
    ]
    lowered = post_text.lower()
    has_banned = any(p in lowered for p in banned_phrases)
    return has_banned


def within_length_band(post_text: str, length_band: dict) -> bool:
    word_count = len(post_text.split())
    # Allow +/-15% slack around the assigned band
    lo = length_band["min_words"] * 0.85
    hi = length_band["max_words"] * 1.15
    return lo <= word_count <= hi
