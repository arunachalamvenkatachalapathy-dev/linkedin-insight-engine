"""
Stitcher agent for EcoPulse LinkedIn automation pipeline.
Assembles the header, body, and footer into one cohesive post.
"""

import json
from llm import call_agent

from agents.instructor import QUALITY_CREDIBILITY_DIRECTIVE, clean_stock_transitions

SYSTEM_PROMPT = f"""You are the Stitcher agent for EcoPulse.

INSTRUCTOR MASTER DIRECTIVE:
{QUALITY_CREDIBILITY_DIRECTIVE}

Your ONLY job: Assemble three separately written sections (header, body, footer) into one cohesive LinkedIn post.

CRITICAL RULES:
1. PRESERVE ALL CONTENT — Do NOT trim, summarize, condense, or remove any sentences from header, body, or footer.
2. SOURCING RULE: Ensure no unverified numbers were invented.
3. CONCRETE ANCHORS: Preserve all named companies, regulations, plant types, and frameworks.
4. DE-TEMPLATE THE RHYTHM: Do NOT introduce stock transition phrases ("This creates a paradox", "The hidden paradox", "Here is the catch", "This is the classic X-Y conflict"). Vary paragraph length naturally.
5. SPECIFICITY: Avoid generic thought-leader clichés.
6. The output should read as one natural flowing post — no section headers, no labels.

Return ONLY valid JSON:
{{
  "agent": "stitcher",
  "output": {{
    "final_post_text": "The complete assembled post text...",
    "word_count": 0
  }}
}}"""

def run(header_text: str, body_text: str, footer_text: str, tone: str) -> dict:
    """Run the Stitcher agent."""
    # Calculate input word count for reference
    input_words = len(header_text.split()) + len(body_text.split()) + len(footer_text.split())
    
    user_content = json.dumps({
        "header_text": header_text,
        "body_text": body_text,
        "footer_text": footer_text,
        "tone": tone,
        "combined_input_word_count": input_words,
        "instruction": f"The combined input is {input_words} words. Your output MUST be at least {int(input_words * 0.9)} words. Do NOT trim."
    })
    return call_agent(system_prompt=SYSTEM_PROMPT, user_content=user_content)
