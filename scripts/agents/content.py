"""
Content agent module for EcoPulse.
Handles scouting, curating, and lateral thinking phases.
Sources content from RSS feeds (ESG Today, GreenBiz, Economic Times ESG, Down To Earth),
environmental journals, and Reddit.
"""

import json
import logging
from llm import call_agent

from agents.instructor import QUALITY_CREDIBILITY_DIRECTIVE
import rss_scout

log = logging.getLogger("ecopulse")

SYSTEM_PROMPT = f"""You are the Content agent for EcoPulse.

INSTRUCTOR MASTER DIRECTIVE:
{QUALITY_CREDIBILITY_DIRECTIVE}

PHASE 1 (SCOUT): Search for FRESH content (last 7 days, prioritize last 48h) across these sources:
- ESG Today (esgtoday.com) — corporate ESG disclosures, sustainable finance, climate tech
- GreenBiz (greenbiz.com) — circular economy, corporate decarbonization, clean energy
- Economic Times Sustainability (sustainability.economictimes.indiatimes.com) — BRSR Core, Scope 1-3, Asian & global ESG regulatory updates
- Down To Earth Magazine (downtoearth.org.in) — environmental engineering field reports, water, waste, climate policy
- Environmental Research Letters, ACS ES&T, Water Research, Nature Climate Change — peer-reviewed findings

For each finding: capture source name, url, date, paraphrased summary, engineering relevance.
Prioritize: NEW regulations, novel technologies, empirical field data, infrastructure project milestones, surprising research findings.

PHASE 2 (CURATE): 
- Filter hard for freshness and specificity.
- SOURCING RULE: Ensure every statistic or metric comes from a REAL named source or framework. If a number cannot be verified with a named source, frame it qualitatively.
- CONCRETE ANCHORS: Capture specific named companies, regulations, plant types, or standards (e.g. GRI, CSRD, BRSR Core).
- Compare against posted_log and REJECT any idea that overlaps thematically with a previous post.
- Select ONE idea that is genuinely current, specific, and factually grounded.
- If nothing fresh enough, set selected_idea to null.

PHASE 3 (LATERAL THINKING): 
- Ask one sharp, non-obvious engineering question about the selected idea (lifecycle costs, second-order impacts, trade-offs vs incumbents, implementation barriers).
- Answer it with a technically grounded insight.

DOMAINS:
ESG Analyst & Sustainability Analyst background: BRSR Core/GRI/CSRD reporting, Scope 1-3 GHG accounting, Constructed Wetlands, watershed risk assessments.

Return ONLY valid JSON with the following schema:
{{
  "agent": "content",
  "topic": "<topic>",
  "output": {{
    "selected_idea": {{
      "headline": "...",
      "supporting_facts": ["fact1", "fact2", "fact3"],
      "recency": "Published YYYY-MM-DD or This week",
      "sources_used": ["Source Name (url)"],
      "why_this_angle": "..."
    }},
    "insight": {{
      "lateral_question": "...",
      "insight_text": "...",
      "hook_potential": "..."
    }}
  }}
}}
"""

def run(topic: str, posted_log: list) -> dict:
    """
    Run the content agent to generate a fresh, non-obvious idea and insight.
    """
    # 1. Scout fresh RSS articles
    rss_articles = rss_scout.fetch_fresh_rss_articles(posted_log, max_articles=4)
    rss_context_lines = []
    if rss_articles:
        for art in rss_articles:
            rss_context_lines.append(
                f"- HEADLINE: {art['title']}\n  SUMMARY: {art['summary']}\n  URL: {art['link']}\n"
            )
    rss_text = "\n".join(rss_context_lines) if rss_context_lines else "None retrieved from feed."

    # 2. Build explicit exclusion list from posted_log
    exclusions = []
    for entry in posted_log[-15:]:
        exclusions.append(f"- {entry.get('headline', '')} (topic: {entry.get('topic', '')})")
    
    exclusion_text = "\n".join(exclusions) if exclusions else "None yet."
    
    prompt = (
        f"Topic: {topic}\n\n"
        f"FRESH RSS NEWS ITEMS DISCOVERED TODAY:\n{rss_text}\n\n"
        f"ALREADY PUBLISHED (DO NOT repeat these angles or similar themes):\n{exclusion_text}\n\n"
        f"Analyze one of the fresh news items above or find something COMPLETELY DIFFERENT from the already published list."
    )
    
    max_retries_for_dup = 2
    for attempt in range(max_retries_for_dup + 1):
        result = call_agent(
            system_prompt=SYSTEM_PROMPT,
            user_content=prompt,
            use_web_search=True,
            max_tokens=6000
        )
        
        from agents import repetition
        
        selected_idea = result.get('output', {}).get('selected_idea')
        if not selected_idea:
            return result
            
        headline = selected_idea.get('headline', '')
        angle = selected_idea.get('why_this_angle', headline)
        
        # Use repetition agent (deterministic + LLM) to check for duplicates
        rep_result = repetition.run(angle, headline, posted_log)
        is_duplicate = rep_result.get('output', {}).get('is_duplicate', False)
        
        if is_duplicate:
            reason = rep_result.get('output', {}).get('reason', 'thematic overlap')
            suggestion = rep_result.get('output', {}).get('suggestion', '')
            log.warning(f"Repetition detected (attempt {attempt+1}): {reason}")
            if attempt < max_retries_for_dup:
                prompt += (
                    f"\n\nREJECTED: '{headline}' was flagged as duplicate ({reason}). "
                    f"Suggestion: {suggestion}. "
                    f"You MUST choose a completely different technology, geography, and narrative frame."
                )
                continue
            else:
                result['error'] = "Max retries reached trying to avoid duplicates."
                return result
        else:
            log.info(f"Content passed repetition check: '{headline}'")
            return result
            
    return result
