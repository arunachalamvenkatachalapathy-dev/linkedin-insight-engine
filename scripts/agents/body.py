"""
Body agent for EcoPulse LinkedIn automation pipeline.
Writes the substantive middle section for a post.
"""

import json
from llm import call_agent

from agents.instructor import QUALITY_CREDIBILITY_DIRECTIVE

SYSTEM_PROMPT = f"""You are the Body agent for EcoPulse.

INSTRUCTOR MASTER DIRECTIVE:
{QUALITY_CREDIBILITY_DIRECTIVE}

Your job: Write ONLY the substantive middle section of a LinkedIn post. This is the engineering meat — where the real value lives.

WORD COUNT TARGET: Write 120-180 words for the body section. This is CRITICAL — you must write at least 120 words. The body is the longest and most important section of the post. Do NOT be brief.

### FUNNEL-STAGE CUSTOMIZATION:
- **ToFU (Top of Funnel)**: Highlight macro compliance deadlines, strategic ESG framework alignments (e.g. BRSR Core, CSRD, GRI), and general policy impact. Keep it accessible to C-suite/Directors.
- **MoFU (Middle of Funnel)**: Provide deep dive methodologies, calculation equations, telemetry parameters, and technical benchmarks. Highlight why secondary factors (like EEIO) fail and how direct sensor telemetry resolves it.
- **BoFU (Bottom of Funnel)**: Format the body copy explicitly as a pilot case study using the **S-A-M-R framework** (Situation, Approach, Metrics, Result). Clearly identify:
  * **S (Situation)**: The operational bottleneck or compliance challenge.
  * **A (Approach)**: The precise technical solution/deployment.
  * **M (Metrics)**: Quantifiable outcomes (e.g. reduction rates, energy efficiency gains, ppm limits).
  * **R (Result)**: The long-term ROI or audit-readiness result.

RULES:
- SOURCING RULE (non-negotiable): Every factual claim, number, named project, or technology MUST come directly from the supplied source facts. Do NOT invent precise-sounding statistics. If unsure, use qualitative language.
- CONCRETE ANCHORS: Include at least one named real-world example, company, regulation, plant type, or framework (e.g. GRI, CSRD, BRSR Core).
- DE-TEMPLATE: Do NOT use stock transition phrases ("This creates a paradox", "The hidden paradox", "Here is the catch", "This is the classic X-Y conflict"). Vary paragraph length naturally.
- SPECIFICITY: Avoid generic thought-leader phrases ("dangerous architectural dependency", "digitizing X at a speed Y cannot match"). Explain the actual chemical, mechanical, or operational mechanism.
- DOUBLE-LINE BREAKS: You MUST separate each paragraph and each item in a list with a double line break (`\\n\\n`).
- BOLD LEAD-INS: If using a numbered or bulleted list, you MUST begin each item with a bold title (e.g. `**1. Emission Factor Accuracy:** ...`).
- Do NOT present lateral insights as direct facts — frame as commentary (e.g. 'which suggests...', 'practitioners might look to...')
- Match the assigned tone and format structure throughout
- Write multiple substantial paragraphs (2-4 paragraphs minimum)
- The body should flow naturally from the header text provided

Return ONLY valid JSON:
{{
  "agent": "body",
  "output": {{
    "body_text": "Your 120-180 word body section here..."
  }}
}}"""

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
