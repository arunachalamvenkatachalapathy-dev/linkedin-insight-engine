"""
Body agent for EcoPulse LinkedIn automation pipeline.
Writes the substantive middle section for a post with structured markdown section headers and emoji bullet points.
"""

import json
from llm import call_agent

from agents.instructor import QUALITY_CREDIBILITY_DIRECTIVE

SYSTEM_PROMPT = f"""You are the Body agent for EcoPulse.

INSTRUCTOR MASTER DIRECTIVE:
{QUALITY_CREDIBILITY_DIRECTIVE}

Your job: Write ONLY the substantive middle section of a LinkedIn post with deep technical depth, structured headers, and clean bullet points.

WORD COUNT TARGET: Write 130-190 words for the body section.

### REQUIRED STRUCTURAL ELEMENTS:
1. SECTION HEADER: Start with a clear markdown subheader with an emoji, e.g.:
   `### 🛠️ The Engineering Pivot: [Core Technology / Mechanism]` or `### 🔬 Technical & Regulatory Breakdown`
2. EXPLANATORY PROSE: Explain the exact physical, chemical, or operational mechanism in 2 short, punchy paragraphs.
3. NUMBERED EMOJI BULLETS: Include 2-3 structured takeaways using numbered emojis, formatted as:
   1️⃣ **[Bold Lead-In Title]:** [Detailed explanation with data/telemetry].
   2️⃣ **[Bold Lead-In Title]:** [Detailed explanation with data/telemetry].
   3️⃣ **[Bold Lead-In Title]:** [Detailed explanation with data/telemetry].
4. KEY TAKEAWAY HEADER: Include a takeaway callout header, e.g.:
   `### 💡 Key Takeaway for Infrastructure & ESG Leaders`
   followed by 1-2 punchy summary sentences.

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
