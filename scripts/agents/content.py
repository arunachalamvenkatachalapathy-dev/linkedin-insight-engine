"""
Content agent module for EcoPulse.
Handles scouting, curating, and lateral thinking phases.
"""

import json
import logging
from llm import call_agent

SYSTEM_PROMPT = """You are the Content agent for EcoPulse.

PHASE 1 (SCOUT): Search across premier environmental journalism and research journals:
- Down To Earth Magazine (site:downtoearth.org.in) for grounded, real-world environmental policy, climate data, and field reports.
- Top Environmental Journals: ACS Environmental Science & Technology (ES&T), Water Research, Nature Climate Change, ScienceDirect Environmental Engineering, ASCE Journal of Environmental Engineering.
- Reddit (r/environmental_science, r/sustainability, r/civilengineering, r/renewableenergy, r/ClimateTech).
- Industry/Gov Bodies: ASCE, WEF, EPA press releases, IEA, CPCB / MoEFCC India updates.

For each finding: capture source, url, date, paraphrased summary, engineering relevance.
Flag NEW regulations, technologies, empirical datasets, and industrial infrastructure projects.

PHASE 2 (CURATE): Filter hard for freshness. Cross-check facts across sources. Discard thematic overlap with posted_log. Select ONE idea that is genuinely current, specific enough for numeric claims, and relevant to environmental professionals.
If nothing fresh enough, set selected_idea to null.

PHASE 3 (LATERAL THINKING): Ask one sharp, non-obvious engineering question about the selected idea (lifecycle costs, second-order impacts, trade-offs vs incumbents). Answer it with a 200-350 word technically grounded insight.
Domain Anchors: Advanced Constructed Wetlands (ACW), Indian Corporate BRSR Core & GHG accounting (Scope 1-3), Watershed environmental risk assessments (Paravanar basin, openLCA, QGIS).

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
