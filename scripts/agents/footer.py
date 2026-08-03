"""
Footer agent for EcoPulse LinkedIn automation pipeline.
Writes the concluding call-to-action prompt and relevant hashtags.
"""

import json
from llm import call_agent

from agents.instructor import QUALITY_CREDIBILITY_DIRECTIVE

SYSTEM_PROMPT = f"""You are the Footer agent for EcoPulse.

INSTRUCTOR MASTER DIRECTIVE:
{QUALITY_CREDIBILITY_DIRECTIVE}

Your job: Write ONLY the closing discussion prompt and hashtags for a LinkedIn post.

FORMAT REQUIREMENT:
---
🤔 **Question for the network:**
[Your thought-provoking open-ended question for engineers, sustainability officers, or investors]

Let's discuss below. 👇

#Hashtag1 #Hashtag2 #Hashtag3 #Hashtag4 #EcoPulse

RULES:
- Ask a high-value technical/strategic question that sparks meaningful peer discussion.
- Provide 4-6 targeted, relevant hashtags.
- Separate sections with clean double line breaks (`\\n\\n`).

Return ONLY valid JSON:
{{
  "agent": "footer",
  "output": {{
    "footer_text": "Your formatted footer text here...",
    "hashtags": ["Hashtag1", "Hashtag2", "Hashtag3", "Hashtag4", "EcoPulse"]
  }}
}}"""

def run(plan: dict, content_brief: dict, header_text: str, body_text: str) -> dict:
    """Run the Footer agent."""
    user_content = json.dumps({
        "plan": plan,
        "content_brief": content_brief,
        "header_text": header_text,
        "body_text": body_text
    })
    return call_agent(system_prompt=SYSTEM_PROMPT, user_content=user_content)
