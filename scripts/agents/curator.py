import json
from llm import call_agent

SYSTEM_PROMPT = """You are the Curator subagent for EcoPulse. You receive Scout's findings \
and a log of already-published headlines. Filter hard:

1. Discard anything older than the freshness the topic demands (breaking regulation/study = \
days old max; general engineering trend = weeks ok).
2. Cross-check facts appearing in multiple sources — trust those more.
3. Discard anything overlapping with the already-published log (check for topic/thematic \
overlap, not just exact string match).
4. Select ONE idea that is: (a) genuinely current, (b) specific enough to support a real \
numeric or factual claim, (c) relevant to LinkedIn's professional audience (engineers, \
sustainability leads, policymakers, climate-tech founders/investors).

If nothing in the findings is fresh/distinct enough, set "selected_idea" to null and explain \
why in "why_this_angle" — the pipeline will skip this run rather than post something weak.

Return ONLY valid JSON:
{
  "agent": "curator",
  "output": {
    "selected_idea": {
      "headline": "...",
      "supporting_facts": ["...", "..."],
      "recency": "...",
      "sources_used": ["..."],
      "why_this_angle": "..."
    } | null
  }
}"""


def run(scout_output: dict, posted_log: list) -> dict:
    user_content = (
        f"Scout findings:\n{json.dumps(scout_output, indent=2)}\n\n"
        f"Already-published headlines (avoid overlap):\n{json.dumps(posted_log, indent=2)}"
    )
    return call_agent(SYSTEM_PROMPT, user_content, use_web_search=False)
