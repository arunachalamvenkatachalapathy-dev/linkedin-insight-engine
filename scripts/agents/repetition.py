"""
Repetition Agent for EcoPulse LinkedIn automation pipeline.
Acts as an anti-repetition gate.
"""

import json
from llm import call_agent

SYSTEM_PROMPT = """
You are the Repetition Agent for EcoPulse.
Compare the proposed angle against ALL entries in the posted_log.
Check thematic overlap, not just exact strings. Check similar engineering concepts, technologies, narrative approaches.
Be strict: even moderate similarity means it is a duplicate.
Suggest an alternative angle if it is a duplicate.

Return JSON in the format:
{ "agent": "repetition", "output": { "is_duplicate": bool, "reason": "str", "suggestion": "str" } }
"""

def run(proposed_angle: str, proposed_headline: str, posted_log: list) -> dict:
    user_content = json.dumps({
        "proposed_angle": proposed_angle,
        "proposed_headline": proposed_headline,
        "posted_log": posted_log
    })
    return call_agent(SYSTEM_PROMPT, user_content)
