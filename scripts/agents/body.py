"""
Body agent for EcoPulse LinkedIn automation pipeline.
Writes the substantive middle section for a post.
"""

import json
from llm import call_agent

SYSTEM_PROMPT = """You are the Body agent for EcoPulse.

Your job: Write ONLY the substantive middle section of a LinkedIn post. This is the engineering meat — where the real value lives.

WORD COUNT TARGET: Write 120-180 words for the body section. This is CRITICAL — you must write at least 120 words. The body is the longest and most important section of the post. Do NOT be brief.

RULES:
- GROUNDING RULE (non-negotiable): Every factual claim, number, named project, or technology MUST come directly from the supplied source facts. Do not invent statistics or embellish numbers.
- INFORMATIONAL DENSITY: Include at least 2-3 specific, granular metrics, physical measurements, efficiency percentages, or exact numbers from the source facts. Explain the actual chemical, mechanical, or operational engineering mechanism.
- Do NOT present lateral insights as direct facts — frame as commentary (e.g. 'which suggests...', 'practitioners might look to...')
- Match the assigned tone and format structure throughout
- Banned phrases: 'in today's world', 'game changer', 'unlock the power', 'as we navigate', 'it is important to note'
- Vary paragraph length — don't default to uniform short punchy lines
- Write multiple substantial paragraphs (2-4 paragraphs minimum)
- The body should flow naturally from the header text provided

Return ONLY valid JSON:
{
  "agent": "body",
  "output": {
    "body_text": "Your 120-180 word body section here..."
  }
}"""

def run(plan: dict, content_brief: dict, header_text: str) -> dict:
    """Run the Body agent."""
    length_band = plan.get("length_band", {})
    min_words = length_band.get("min_words", 155)
    
    if min_words >= 220:
        target_words = "140-180 words"
    else:
        target_words = "100-130 words"

    user_content = json.dumps({
        "plan": plan,
        "content_brief": content_brief,
        "header_text": header_text,
        "target_word_count_for_body": target_words
    })
    
    custom_system_prompt = SYSTEM_PROMPT.replace("120-180 words", target_words)
    return call_agent(system_prompt=custom_system_prompt, user_content=user_content)
