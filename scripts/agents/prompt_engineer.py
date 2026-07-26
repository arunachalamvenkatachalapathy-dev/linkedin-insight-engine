"""
Prompt Engineer Agent for EcoPulse LinkedIn automation pipeline.
Dynamically generates optimized prompts for downstream agents.
"""

import json
from llm import call_agent

SCHEMAS = {
    'planner': { 'agent': 'planner', 'output': { 'angle': '...', 'format_name': '...', 'tone_name': '...', 'length_band_name': '...', 'rationale': '...' } },
    'content': { 'agent': 'content', 'topic': '<topic>', 'output': { 'selected_idea': { 'headline': '...', 'supporting_facts': ['...'], 'recency': '...', 'sources_used': ['...'], 'why_this_angle': '...' }, 'insight': { 'lateral_question': '...', 'insight_text': '...', 'hook_potential': '...' } } },
    'header': { 'agent': 'header', 'output': { 'header_text': '...' } },
    'body': { 'agent': 'body', 'output': { 'body_text': '...' } },
    'footer': { 'agent': 'footer', 'output': { 'footer_text': '...', 'hashtags': ['...'] } },
    'stitcher': { 'agent': 'stitcher', 'output': { 'final_post_text': '...', 'word_count': 0 } },
    'checker': { 'agent': 'checker', 'output': { 'passed': True, 'issues': [], 'grounding_score': 0 } },
    'image': { 'agent': 'image', 'output': { 'image_prompt': '...', 'aspect_ratio': '1:1', 'style_notes': '...' } }
}

SYSTEM_PROMPT = """
You are the Prompt Engineer for EcoPulse.
Your task is to generate highly optimized system and user prompts for each downstream agent.
For the 'content' agent: include Reddit search strategies (e.g., site:reddit.com/r/sustainability, etc.).
For the 'image' agent: include DSLR photography style requirements.
Domain anchoring: Constructed Wetlands ACW, BRSR Core/GHG, Paravanar basin.
Always enforce the target agent's JSON return schema.

Return a JSON object containing 'generated_system_prompt' and 'generated_user_prompt'.
"""

def generate_prompt_for_agent(agent_name: str, topic: str, extra_context: dict = None) -> dict:
    schema = SCHEMAS.get(agent_name, {})
    user_content = json.dumps({
        "agent_name": agent_name,
        "topic": topic,
        "extra_context": extra_context or {},
        "target_schema": schema
    })
    return call_agent(SYSTEM_PROMPT, user_content)

def run(*args, **kwargs):
    # Fallback to match module requirements
    return generate_prompt_for_agent(*args, **kwargs)
