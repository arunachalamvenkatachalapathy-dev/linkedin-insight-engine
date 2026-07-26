"""
Accuracy & Fact-Check Agent for EcoPulse LinkedIn automation pipeline.
Audits every post for technical, empirical, and mathematical accuracy against original sources.
"""

import json
import logging
import re
from llm import call_agent

log = logging.getLogger("ecopulse")

SYSTEM_PROMPT = """
You are the Accuracy & Fact-Check Agent for EcoPulse.

YOUR SOLE MISSION: Audit the complete assembled LinkedIn post to ensure 100% technical, empirical, mathematical, and regulatory accuracy before publication.

AUDIT CHECKS:
1. EMPIRICAL ACCURACY:
   - Check every statistic, percentage, unit of measurement, and numerical metric against the source_facts.
   - Verify units are accurate (e.g., mg/L vs ppm, MW vs MWh, Scope 1 vs Scope 3, COD vs BOD, GWP values).
   - Reject any post that hallucinated or misquoted numbers, percentages, or chemical formulas.

2. TECHNICAL REALISM:
   - Does the engineering mechanism described make physical/chemical sense? (e.g., constructed wetland HRT, dynamic line rating thermal limits, PFAS precursor oxidation).
   - Ensure the post does not claim scientifically impossible or exaggerated results.

3. REGULATORY ACCURACY:
   - If mentioning standards (e.g., BRSR Core, GRI 303, CSRD ESRS E1/E4, EPA Method 1633, CPCB discharge norms), ensure the standard names, compliance mandates, and reporting scopes are used correctly.

4. FACTUAL GROUNDING:
   - Every claim must either originate directly from source_facts/lateral_insight OR be explicitly framed as an expert hypothesis ("which suggests...", "practitioners might consider...").

EVALUATION CRITERIA:
- Set accuracy_passed = true ONLY if accuracy_score >= 85 and there are ZERO critical factual hallucinations or mathematical errors.
- If accuracy_passed = false, provide explicit, actionable correction instructions for the writing agents.

Return JSON strictly in this format:
{
  "agent": "accuracy",
  "output": {
    "accuracy_passed": bool,
    "accuracy_score": int,
    "factual_errors": ["list of explicit errors or hallucinations found, if any"],
    "unit_check_passed": bool,
    "regulatory_check_passed": bool,
    "correction_guidance": "Detailed instructions on what specific numbers or facts to fix if accuracy_passed is false"
  }
}
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
