"""
Accuracy & Fact-Check Agent for EcoPulse LinkedIn automation pipeline.
Audits every post for technical, empirical, and mathematical accuracy against original sources.
"""

import json
import logging
import re
from llm import call_agent

log = logging.getLogger("ecopulse")

from agents.instructor import QUALITY_CREDIBILITY_DIRECTIVE

SYSTEM_PROMPT = f"""
You are the Accuracy & Fact-Check Agent for EcoPulse.

INSTRUCTOR MASTER DIRECTIVE:
{QUALITY_CREDIBILITY_DIRECTIVE}

YOUR SOLE MISSION: Audit the complete assembled LinkedIn post to ensure 100% technical, empirical, mathematical, and regulatory accuracy before publication.

AUDIT CHECKS:
1. SOURCING RULE & EMPIRICAL ACCURACY:
   - Check every statistic, percentage, unit of measurement, and numerical metric against the source_facts.
   - REJECT any precise statistic or percentage (e.g. "40% higher risk") that does NOT come from a real named source. Such stats MUST be rewritten qualitatively (e.g. "significantly higher risk").
   - Verify units are accurate (e.g., mg/L vs ppm, MW vs MWh, Scope 1 vs Scope 3, COD vs BOD).

2. CONCRETE ANCHOR REQUIREMENT:
   - Verify the post includes at least ONE named real-world example (company, plant type, regulation, framework like BRSR/GRI/CSRD, or technology).

3. TECHNICAL REALISM:
   - Does the engineering mechanism described make physical/chemical sense?

4. REGULATORY ACCURACY:
   - Verify standard names, compliance mandates, and reporting scopes are cited correctly.

EVALUATION CRITERIA:
- Set accuracy_passed = true ONLY if accuracy_score >= 85 and there are ZERO ungrounded/invented statistics or factual errors.
- If accuracy_passed = false, provide explicit, actionable correction instructions for the writing agents.

Return JSON strictly in this format:
{{
  "agent": "accuracy",
  "output": {{
    "accuracy_passed": bool,
    "accuracy_score": int,
    "factual_errors": ["list of explicit errors, unverified statistics, or hallucinations found, if any"],
    "unit_check_passed": bool,
    "regulatory_check_passed": bool,
    "correction_guidance": "Detailed instructions on what specific numbers or facts to fix if accuracy_passed is false"
  }}
}}
"""


def verify_numeric_hallucinations(post_text: str, source_facts: dict) -> list:
    """
    Local heuristic check: extract numbers from post_text and check if they exist 
    in source_facts or are plausible derivations.
    """
    facts_str = json.dumps(source_facts).lower()
    # Find numbers (percentages, decimals, large numbers)
    numbers_in_post = re.findall(r'\b\d+(?:\.\d+)?%?\b', post_text)
    
    unverified = []
    for num in numbers_in_post:
        # Ignore common harmless numbers (like 1-3, 2026, 2-4)
        if num in ["1", "2", "3", "4", "5", "2024", "2025", "2026"]:
            continue
        if num.lower() not in facts_str:
            unverified.append(num)
            
    return unverified


def run(post_text: str, source_facts: dict, lateral_insight: dict) -> dict:
    """
    Run the Accuracy Agent to audit post correctness.
    """
    user_content = json.dumps({
        "post_text": post_text,
        "source_facts": source_facts,
        "lateral_insight": lateral_insight
    })
    
    # LLM deep accuracy audit
    result = call_agent(SYSTEM_PROMPT, user_content)
    
    # Add local numeric cross-check feedback
    unverified_nums = verify_numeric_hallucinations(post_text, source_facts)
    if unverified_nums:
        log.info(f"Accuracy agent local audit flagged unverified metrics: {unverified_nums}")
        
    return result
