"""
Stitcher agent for EcoPulse LinkedIn automation pipeline.
Assembles the header, body, and footer into one cohesive post.
"""

import json
from llm import call_agent

SYSTEM_PROMPT = """You are the Stitcher agent for EcoPulse
- Receive three separately written sections: header, body, footer
- ONLY job: assemble into one cohesive post
- Smooth transitions (fix abrupt jumps)
- Ensure consistent tone
- Fix redundancy (if body repeats header content, trim)
- Do NOT add new facts, claims, or content
- Do NOT significantly alter meaning
- Count final word count
- Output should read as one natural flowing post
- Return ONLY valid JSON: { "agent": "stitcher", "output": { "final_post_text": "...", "word_count": 0 } }"""

def run(header_text: str, body_text: str, footer_text: str, tone: str) -> dict:
    """Run the Stitcher agent."""
    user_content = json.dumps({
        "header_text": header_text,
        "body_text": body_text,
        "footer_text": footer_text,
        "tone": tone
    })
    return call_agent(system_prompt=SYSTEM_PROMPT, user_content=user_content)
