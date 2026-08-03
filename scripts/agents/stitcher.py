"""
Stitcher agent for EcoPulse LinkedIn automation pipeline.
Assembles the header, body, and footer into a beautifully formatted, highly engaging LinkedIn post.
"""

import json
from llm import call_agent

from agents.instructor import QUALITY_CREDIBILITY_DIRECTIVE

SYSTEM_PROMPT = f"""You are the Stitcher agent for EcoPulse.

INSTRUCTOR MASTER DIRECTIVE:
{QUALITY_CREDIBILITY_DIRECTIVE}

Your job: Assemble three separately written sections (header, body, footer) into a beautifully formatted, highly engaging LinkedIn post.

CRITICAL FORMATTING & STRUCTURAL REQUIREMENTS:
1. PRESERVE ALL CONTENT & STRUCTURE — Do NOT trim, summarize, or flatten the post into plain continuous prose.
2. SECTION HEADERS & EMOJI BULLETS: Retain and enhance all markdown section headers (e.g., `### 🛠️ ...`, `### 📊 ...`, `### 💡 Key Takeaways`), numbered emoji bullets (`1️⃣`, `2️⃣`, `3️⃣`), and bold lead-ins.
3. DOUBLE LINE BREAKS: You MUST use double line breaks (`\\n\\n`) between every paragraph, bullet point, and section header to guarantee optimal scannability on mobile screens.
4. SOURCING RULE: Ensure no unverified numbers were invented.
5. CONCRETE ANCHORS: Preserve all named companies, regulations, plant types, and frameworks.
6. CTA & HASHTAGS: Ensure the final output ends with a clean discussion prompt (`🤔 Question for the network:...`) and relevant industry hashtags.

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
        "instruction": f"Assemble header, body, and footer into a beautifully formatted LinkedIn post with markdown headers, double line breaks, and emoji bullet points."
    })
    return call_agent(system_prompt=SYSTEM_PROMPT, user_content=user_content)
