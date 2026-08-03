"""
Body agent for EcoPulse LinkedIn automation pipeline.
Writes the substantive middle section for a post formatted with clean section headers and emoji bullet points.
"""

import json
from llm import call_agent

from agents.instructor import QUALITY_CREDIBILITY_DIRECTIVE

SYSTEM_PROMPT = f"""You are the Body agent for EcoPulse.

INSTRUCTOR MASTER DIRECTIVE:
{QUALITY_CREDIBILITY_DIRECTIVE}

Your job: Write ONLY the substantive middle section of a LinkedIn post with deep technical depth, structured section headers, and clean bullet points.

WORD COUNT TARGET: Write 130-190 words for the body section.

CRITICAL LINKEDIN FORMATTING RULE:
- Do NOT use raw markdown hashes (like `###`). LinkedIn does NOT parse `###` and displays `###` as raw text to readers.
- Use bold text for section headers, e.g.:
  `🛠️ **THE ENGINEERING PIVOT: [SECTION TITLE]**`
- Use numbered emojis for bullet points:
  1️⃣ **[Lead-In Title]:** [Detailed explanation with data/telemetry].
  2️⃣ **[Lead-In Title]:** [Detailed explanation with data/telemetry].
  3️⃣ **[Lead-In Title]:** [Detailed explanation with data/telemetry].
- Use bold text for key takeaway callouts:
  `💡 **KEY TAKEAWAY FOR SUSTAINABILITY LEADERS**`

### FUNNEL-STAGE CUSTOMIZATION:
- **ToFU (Top of Funnel)**: Focus on macro compliance deadlines, ESG frameworks (BRSR Core, CSRD ESRS, GRI), and strategic risks.
- **MoFU (Middle of Funnel)**: Focus on calculation methodologies, telemetry parameters, and technical benchmarks.
- **BoFU (Bottom of Funnel)**: Format using the **S-A-M-R framework** (Situation, Approach, Metrics, Result) with clear headings.

RULES:
- Separate every section and bullet point with double line breaks (`\\n\\n`).
- All numbers, named projects, and technologies MUST come directly from source facts.

Return ONLY valid JSON:
{{
  "agent": "body",
  "output": {{
    "body_text": "Your structured body section here..."
  }}
}}"""

def run(plan: dict, content_brief: dict, header_text: str) -> dict:
    """Run the Body agent."""
    length_band = plan.get("length_band", {})
    min_words = length_band.get("min_words", 155)
    
    target_words = "140-180 words" if min_words >= 220 else "110-140 words"

    user_content = json.dumps({
        "plan": plan,
        "content_brief": content_brief,
        "header_text": header_text,
        "target_word_count_for_body": target_words
    })
    
    custom_system_prompt = SYSTEM_PROMPT.replace("130-190 words", target_words)
    return call_agent(system_prompt=custom_system_prompt, user_content=user_content)
