"""
Content agent module for EcoPulse.
Handles scouting, curating, and lateral thinking phases.
"""

import json
import logging
from llm import call_agent

SYSTEM_PROMPT = """You are the Content agent for EcoPulse.

PHASE 1 (SCOUT): Search Google News (last 7 days, prioritize last 48h), Reddit (r/environmental_science, r/sustainability, r/civilengineering, r/renewableenergy, r/ClimateTech), and industry sources (ASCE, WEF, EPA, IEA)
For each finding: capture source, url, date, paraphrased summary, engineering relevance.
Flag NEW regulations, technologies, data/studies, infrastructure projects.

PHASE 2 (CURATE): Filter hard for freshness. Cross-check facts. Discard thematic overlap with posted_log. Select ONE idea that is genuinely current, specific enough for numeric claims, relevant to LinkedIn professionals.
If nothing fresh enough, set selected_idea to null.

PHASE 3 (LATERAL THINKING): Ask one sharp non-obvious engineering question about the selected idea (lifecycle costs, second-order impacts, trade-offs vs incumbents). Answer it with 200-350 word technically grounded insight.
Domain: Constructed Wetlands ACW, BRSR Core/GHG, Paravanar basin.

Return ONLY valid JSON with the following schema:
{
  "agent": "content",
  "topic": "<topic>",
  "output": {
    "selected_idea": {
      "headline": "...",
      "supporting_facts": ["..."],
      "recency": "...",
      "sources_used": ["..."],
      "why_this_angle": "..."
    },
    "insight": {
      "lateral_question": "...",
      "insight_text": "...",
      "hook_potential": "..."
    }
  }
}
"""

def run(topic: str, posted_log: list) -> dict:
    """
    Run the content agent to generate a fresh, non-obvious idea and insight.
    """
    prompt = f"Topic: {topic}\nPosted log (avoid overlap): {json.dumps(posted_log)}"
    
    max_retries_for_dup = 2
    for attempt in range(max_retries_for_dup + 1):
        result = call_agent(
            system_prompt=SYSTEM_PROMPT,
            user_content=prompt,
            use_web_search=True,
            max_tokens=6000
        )
        
        # Ensure it returned dict and not str, though call_agent returns dict
        from agents import repetition
        
        selected_idea = result.get('output', {}).get('selected_idea')
        if not selected_idea:
            # If no idea found, return result directly
            return result
            
        headline = selected_idea.get('headline', '')
        angle = selected_idea.get('why_this_angle', headline)
        
        # Use repetition.run to check for duplicates
        rep_result = repetition.run(angle, headline, posted_log)
        is_duplicate = rep_result.get('output', {}).get('is_duplicate', False)
        
        if is_duplicate:
            if attempt < max_retries_for_dup:
                prompt += f"\n\nThe previous headline '{headline}' was deemed a duplicate by the repetition agent. You must choose a completely different angle."
                continue
            else:
                # Max retries reached
                result['error'] = "Max retries reached trying to avoid duplicates."
                return result
        else:
            return result
            
    return result
