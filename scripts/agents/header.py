"""
Header agent for EcoPulse LinkedIn automation pipeline.
Writes the opening hook/header for a post.
"""

import json
from llm import call_agent

from agents.instructor import QUALITY_CREDIBILITY_DIRECTIVE

SYSTEM_PROMPT = f"""You are the Header agent for EcoPulse.

INSTRUCTOR MASTER DIRECTIVE:
{QUALITY_CREDIBILITY_DIRECTIVE}

Your job: Write ONLY the opening hook/introduction of a LinkedIn post. This is 2-4 sentences that grab attention and set up the topic.

WORD COUNT TARGET: Write 30-60 words for the header section. This is critical — do not write less than 30 words.

RULES:
- HOOK OPTIMIZATION: Write a punchy, self-contained first sentence of maximum 140 characters, followed immediately by a double line break (`\\n\\n`) to create an intriguing curiosity gap. This creates a preview that drives high clicks on "...see more".
- SOURCING RULE: Do NOT invent precise-sounding statistics. If a stat isn't in source facts, frame it qualitatively.
- CONCRETE ANCHORS: Include named real-world technologies, regulations, or frameworks if present in the brief.
- DE-TEMPLATE: Do NOT use stock transition phrases like "This creates a paradox" or "Here is the catch".
- The opening sentence MUST be substantive and attention-grabbing, at least 15-25 words long
- MUST NOT be a short 2-3 word label or title (no 'Before vs. After:', 'Field Note:', 'Myth vs. Reality:')
- Lead directly into the narrative so the LinkedIn feed preview is highly informative and does not look blank
- Match the assigned tone throughout
- Be specific to the engineering topic — use real project names, technologies, or metrics from the content brief

Return ONLY valid JSON:
{{
  "agent": "header",
  "output": {{
    "header_text": "Your 30-60 word opening hook here..."
  }}
}}"""

def run(plan: dict, content_brief: dict) -> dict:
    """Run the Header agent."""
    length_band = plan.get("length_band", {})
    min_words = length_band.get("min_words", 155)
    
    if min_words >= 220:
        target_words = "40-60 words"
    else:
        target_words = "30-45 words"

    user_content = json.dumps({
        "plan": plan,
        "content_brief": content_brief,
        "target_word_count_for_header": target_words
    })
    
    custom_system_prompt = SYSTEM_PROMPT.replace("30-60 words", target_words)
    return call_agent(system_prompt=custom_system_prompt, user_content=user_content)
