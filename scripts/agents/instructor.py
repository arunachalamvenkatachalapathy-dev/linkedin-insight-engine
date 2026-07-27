"""
Instructor Agent for EcoPulse LinkedIn automation pipeline.
Acts as the Master Quality & Credibility Directive Layer that executes at the beginning 
and governs every single agent (Planner, Content, Header, Body, Footer, Stitcher, Strategist, Checker, Accuracy).
"""

import json
import re
import logging
from llm import call_agent

log = logging.getLogger("ecopulse")

QUALITY_CREDIBILITY_DIRECTIVE = """
===============================================================================
MASTER INSTRUCTOR DIRECTIVE: QUALITY & CREDIBILITY LAYER
(Must be strictly respected during generation, stitching, formatting, and auditing)
===============================================================================

1. SOURCING RULE (No Fabricated Statistics):
   - Before including ANY statistic, percentage, or data claim (e.g. "40% higher risk"):
     * It MUST come directly from a real, named source (report, study, org) that can be cited.
     * OR it MUST be rewritten as a qualitative claim without a fabricated number (e.g., "significantly higher risk" instead of "40% higher risk").
   - NEVER invent precise-sounding statistics to make a claim feel authoritative. If unsure whether a stat is real, default to qualitative language.

2. CONCRETE ANCHOR REQUIREMENT:
   - Every post MUST include at least ONE of the following before publishing:
     * A named real-world example (a specific company, plant type, regulation, or technology by name).
     * A first-person observation or experience framed as such.
     * A specific citation or reference to a real report/framework (e.g., GRI 303, CSRD ESRS E1/E4, BRSR Core clause).
   - Abstract arguments with zero concrete anchors are NOT acceptable output.

3. DE-TEMPLATE THE RHYTHM:
   - Avoid rigid AI-pattern structure:
     * Do NOT use uniform one-sentence paragraphs throughout the entire post.
     * Do NOT use a rigid "setup -> paradox -> technical point -> moral urgency -> rhetorical question" arc.
   - Vary paragraph length naturally (mix 1-line punches with 2-3 sentence paragraphs).
   - AVOID stock transition phrases such as: "This creates a paradox", "The hidden paradox", "Here is the catch", "This is the classic X-Y conflict in action", "In today's world", "As we navigate".

4. CLOSING QUESTION CHECK:
   - The closing question MUST add a NEW angle, not restate the thesis already stated twice in the body.
   - Pose a genuinely open, debatable question that climate tech, energy, and ESG professionals haven't already been told the answer to.

5. SPECIFICITY OVER GENERIC PHRASING:
   - Flag and rewrite generic thought-leader phrases such as:
     * "dangerous architectural dependency"
     * "digitizing X at a speed Y cannot match"
     * "the industry is rushing to..."
     * "game changer", "unlock the power", "as we navigate", "revolutionize", "cutting-edge"
   - Replace with specific, falsifiable language tied to the actual mechanism being discussed.

6. SELF-CHECK BEFORE OUTPUT:
   - Is every number in this post real or clearly softened to avoid fabrication?
   - Is there at least one concrete, named anchor?
   - Would a domain expert reading this be able to point to a specific claim and ask "source?" — if yes, fix that claim first.
===============================================================================
"""


def get_system_instructions() -> str:
    """Returns the master quality directive to be included in downstream agents."""
    return QUALITY_CREDIBILITY_DIRECTIVE


def clean_stock_transitions(post_text: str) -> str:
    """
    Strips out banned stock transition phrases and generic thought-leader clichés.
    """
    banned_transitions = [
        r"(?i)\bthis creates a paradox:?\b",
        r"(?i)\bthe hidden paradox:?\b",
        r"(?i)\bhere is the catch:?\b",
        r"(?i)\bthis is the classic [^.\n]+ conflict in action:?\b",
        r"(?i)\bdangerous architectural dependency\b",
        r"(?i)\bthe industry is rushing to\b",
        r"(?i)\bdigitizing [^.\n]+ at a speed [^.\n]+ cannot match\b",
        r"(?i)\bin today's world\b",
        r"(?i)\bas we navigate\b",
        r"(?i)\bgame changer\b",
        r"(?i)\bunlock the power\b",
    ]
    
    cleaned = post_text
    for pattern in banned_transitions:
        cleaned = re.sub(pattern, "", cleaned)
        
    # Clean up double blank lines caused by removals
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
    return cleaned


AUDITOR_SYSTEM_PROMPT = f"""You are the Instructor Audit Agent for EcoPulse.

YOUR JOB: Audit the final post draft against the Master Quality & Credibility Directive.

{QUALITY_CREDIBILITY_DIRECTIVE}

Return ONLY valid JSON:
{{
  "agent": "instructor",
  "output": {{
    "passed": bool,
    "issues": ["list of explicit violations of the 6 rules, if any"],
    "sourcing_check_passed": bool,
    "concrete_anchor_found": "Name of concrete anchor found (company, regulation, tech, or report) OR 'NONE'",
    "rhythm_check_passed": bool,
    "closing_question_valid": bool,
    "suggested_rewrites": "Actionable feedback if passed=false"
  }}
}}
"""


def audit(post_text: str, source_facts: dict, topic: str) -> dict:
    """
    Run the Instructor Agent to audit the post against all 6 Quality & Credibility rules.
    """
    user_content = json.dumps({
        "post_text": post_text,
        "source_facts": source_facts,
        "topic": topic
    })
    return call_agent(AUDITOR_SYSTEM_PROMPT, user_content)
