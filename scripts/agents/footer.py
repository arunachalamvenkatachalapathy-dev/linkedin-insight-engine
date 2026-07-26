"""
Footer agent for EcoPulse LinkedIn automation pipeline.
Writes the closing CTA and hashtags for a post.
"""

import json
from llm import call_agent

SYSTEM_PROMPT = """You are the Footer agent for EcoPulse.

Your job: Write ONLY the closing section of a LinkedIn post (2-4 sentences) plus hashtags.

WORD COUNT TARGET: Write 30-50 words for the footer text (excluding hashtags). Do not write less than 25 words.

RULES:
- VARY the closing style across posts — use one of: a provocative question, an invitation to disagree, a specific data challenge, a direct ask for professional input, or a forward-looking statement
- Do NOT default to generic closings like 'What are your thoughts?' or 'Thoughts?'
- Include 3-5 relevant, specific hashtags that are genuinely related to this post's content (not a recycled generic set)
- Max 1-2 emojis only if the tone suits it
- The closing should invite a real professional response shaped by the post's format and content

Return ONLY valid JSON:
{
  "agent": "footer",
  "output": {
    "footer_text": "Your 30-50 word closing section here...",
    "hashtags": ["Hashtag1", "Hashtag2", "Hashtag3"]
  }
}"""

def run(plan: dict, content_brief: dict, header_text: str, body_text: str) -> dict:
    """Run the Footer agent."""
    length_band = plan.get("length_band", {})
    min_words = length_band.get("min_words", 155)
    
    if min_words >= 220:
        target_words = "35-50 words"
    else:
        target_words = "25-35 words"

    user_content = json.dumps({
        "plan": plan,
        "content_brief": content_brief,
        "header_text": header_text,
        "body_text": body_text,
        "target_word_count_for_footer": target_words
    })
    
    custom_system_prompt = SYSTEM_PROMPT.replace("30-50 words", target_words)
    return call_agent(system_prompt=custom_system_prompt, user_content=user_content)
