"""
Stitcher agent for EcoPulse LinkedIn automation pipeline.
Assembles header, body, and footer into a cohesive, beautifully formatted LinkedIn post.
"""

import json
from llm import call_agent

from agents.instructor import QUALITY_CREDIBILITY_DIRECTIVE

SYSTEM_PROMPT = f"""You are the Stitcher agent for EcoPulse.

INSTRUCTOR MASTER DIRECTIVE:
{QUALITY_CREDIBILITY_DIRECTIVE}

Your job: Assemble three separately written sections (header, body, footer) into a cohesive LinkedIn post.

CRITICAL LINKEDIN FORMATTING RULES:
1. NO RAW `###` HASHES — Remove any raw `###` markdown hashes if present. Replace with clean bold headers (e.g. `🛠️ **THE ENGINEERING PIVOT: ...**`).
2. EMOJI NUMBERED BULLETS: Preserve all emoji numbered bullets (`1️⃣`, `2️⃣`, `3️⃣`) and bold lead-ins.
3. DOUBLE LINE BREAKS: You MUST preserve double line breaks (`\\n\\n`) between every paragraph, bullet point, and section header to guarantee optimal scannability on mobile screens.
4. PRESERVE ALL CONTENT: Do NOT trim, summarize, or remove any content sentences.
5. SOURCING & CONCRETE ANCHORS: Preserve all facts, figures, named companies, regulations, and frameworks.

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
    input_words = len(header_text.split()) + len(body_text.split()) + len(footer_text.split())
    
    user_content = json.dumps({
        "header_text": header_text,
        "body_text": body_text,
        "footer_text": footer_text,
        "tone": tone,
        "combined_input_word_count": input_words,
        "instruction": f"Assemble header, body, and footer into a beautifully formatted LinkedIn post with bold headers (no raw ### hashes), double line breaks, and emoji bullet points."
    })
    return call_agent(system_prompt=SYSTEM_PROMPT, user_content=user_content)
