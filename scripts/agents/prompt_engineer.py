import json
from llm import call_agent

SYSTEM_PROMPT = """You are the Prompt Engineer subagent for EcoPulse. Your single task is to generate \
highly optimized system and user instruction sets (prompts) for each subagent action in the pipeline, \
rather than using hardcoded prompts.

Based on the current selected topic and desired format/tone, generate the exact prompt for the target agent.

When generating prompts for the "scout" agent:
- You MUST instruct the scout to specifically formulate web search queries targeting relevant Reddit threads to gather trending community angles, using search operators like `site:reddit.com/r/sustainability`, `site:reddit.com/r/civilengineering`, or `site:reddit.com/r/ClimateTech` alongside the selected topic.
- Emphasize that the scout must find recent Reddit discussions (within the past month) and capture post links (`url`) and community discussions (`excerpt`).

You MUST enforce that the generated system prompt instructs the target agent to return ONLY valid JSON matching the exact schema specified below:

Required JSON Return Schemas:
- scout:
{
  "agent": "scout",
  "topic": "<topic>",
  "output": {
    "findings": [
      {"source": "...", "url": "...", "date": "...", "excerpt": "...", "relevance_to_engineers": "..."}
    ]
  }
}

- lateral_thinker:
{
  "agent": "lateral_thinker",
  "output": {
    "lateral_question": "...",
    "insight": "...",
    "hook_potential": "..."
  }
}

- copywriter:
{
  "agent": "copywriter",
  "output": {
    "post_text": "...",
    "hook": "...",
    "hashtags": ["...", "..."],
    "format_used": "...",
    "tone_used": "...",
    "image_brief": "..."
  }
}

- visualizer:
{
  "agent": "visualizer",
  "output": {
    "image_prompt": "...",
    "aspect_ratio": "1:1",
    "style_notes": "...",
    "text_overlay": null
  }
}

Return ONLY valid JSON:
{
  "agent": "prompt_engineer",
  "output": {
    "generated_system_prompt": "...",
    "generated_user_prompt": "..."
  }
}"""

SCHEMAS = {
    "scout": """
Return ONLY valid JSON matching this schema:
{
  "agent": "scout",
  "topic": "<topic>",
  "output": {
    "findings": [
      {"source": "...", "url": "...", "date": "...", "excerpt": "...", "relevance_to_engineers": "..."}
    ]
  }
}
""",
    "lateral_thinker": """
Return ONLY valid JSON matching this schema:
{
  "agent": "lateral_thinker",
  "output": {
    "lateral_question": "...",
    "insight": "...",
    "hook_potential": "..."
  }
}
""",
    "copywriter": """
Return ONLY valid JSON matching this schema:
{
  "agent": "copywriter",
  "output": {
    "post_text": "...",
    "hook": "...",
    "hashtags": ["...", "..."],
    "format_used": "...",
    "tone_used": "...",
    "image_brief": "..."
  }
}
""",
    "visualizer": """
Return ONLY valid JSON matching this schema:
{
  "agent": "visualizer",
  "output": {
    "image_prompt": "...",
    "aspect_ratio": "1:1",
    "style_notes": "...",
    "text_overlay": null
  }
}
"""
}

def generate_prompt_for_agent(agent_name: str, topic: str, extra_context: dict = None) -> dict:
    """Dynamically engineer a prompt for a targeted pipeline action."""
    user_content = (
        f"Generate optimized prompts for agent: {agent_name}\n"
        f"Topic: {topic}\n"
        f"Context details: {json.dumps(extra_context or {})}"
    )
    result = call_agent(SYSTEM_PROMPT, user_content, use_web_search=False)
    prompts = result["output"]
    if agent_name in SCHEMAS:
        prompts["generated_system_prompt"] += "\n\n" + SCHEMAS[agent_name]
    return prompts
