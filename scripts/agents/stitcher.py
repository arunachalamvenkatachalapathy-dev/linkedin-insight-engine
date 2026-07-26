"""
Stitcher agent for EcoPulse LinkedIn automation pipeline.
Assembles the header, body, and footer into one cohesive post.
"""

import json
from llm import call_agent

SYSTEM_PROMPT = """You are the Stitcher agent for EcoPulse.

Your ONLY job: Assemble three separately written sections (header, body, footer) into one cohesive LinkedIn post.

CRITICAL RULES:
1. PRESERVE ALL CONTENT — Do NOT trim, summarize, condense, or remove any sentences from header, body, or footer. Every sentence from all three sections MUST appear in the final output.
2. Smooth transitions between sections (fix abrupt jumps with a connecting word or phrase if needed).
3. Ensure consistent tone throughout.
4. Fix minor redundancy ONLY if the exact same sentence appears twice — do NOT remove similar-but-different sentences.
5. Do NOT add new facts, claims, or content.
6. Do NOT significantly alter meaning or wording.
7. The output should read as one natural flowing post — no section headers, no labels.
8. Count the final word count accurately.

IMPORTANT: The final word count should be very close to the combined word count of header + body + footer. If your output is significantly shorter, you are trimming too aggressively. STOP and include everything.

Return ONLY valid JSON:
{
  "agent": "stitcher",
  "output": {
    "final_post_text": "The complete assembled post text...",
    "word_count": 0
  }
}"""

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
