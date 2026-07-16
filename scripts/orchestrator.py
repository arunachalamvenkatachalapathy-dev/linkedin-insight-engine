"""
EcoPulse root orchestrator.
Run via: python orchestrator.py
Reads config/niche_topics.json, config/post_formats.json, config/tones.json, and
state/posted_log.json, runs the 7-agent pipeline, and (if everything validates)
publishes to LinkedIn.
"""
import os
import sys
import json
import random
import logging
from datetime import datetime, timezone

# Load env variables from local .env
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k.strip()] = v.strip()

sys.path.insert(0, os.path.dirname(__file__))

from agents import scout, curator, lateral_thinker, copywriter, fact_checker, visualizer, publisher, prompt_engineer  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ecopulse")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOPICS_PATH = os.path.join(ROOT, "config", "niche_topics.json")
FORMATS_PATH = os.path.join(ROOT, "config", "post_formats.json")
TONES_PATH = os.path.join(ROOT, "config", "tones.json")
LOG_PATH = os.path.join(ROOT, "state", "posted_log.json")
IMAGE_PATH = os.path.join(ROOT, "state", "latest_image.png")

DRY_RUN = os.environ.get("ECOPULSE_DRY_RUN", "false").lower() == "true"
NO_REPEAT_WINDOW = 3  # don't reuse a format/tone used in the last N posts


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def pick_topic(topics: list, posted_log: list) -> str:
    recent_topics = [e.get("topic", "").lower() for e in posted_log[-8:]]
    candidates = [t for t in topics if t.lower() not in recent_topics] or topics
    return random.choice(candidates)


def pick_non_repeating(pool: list, recent_used: list, key=lambda x: x):
    """Pick a random item from pool, avoiding anything in recent_used if possible."""
    candidates = [item for item in pool if key(item) not in recent_used] or pool
    return random.choice(candidates)


def main():
    topics = load_json(TOPICS_PATH, {}).get("topics", [])
    formats = load_json(FORMATS_PATH, {}).get("formats", [])
    tones = load_json(TONES_PATH, {}).get("tones", [])
    length_bands = load_json(TONES_PATH, {}).get("length_bands", [])
    posted_log = load_json(LOG_PATH, [])

    if not topics or not formats or not tones or not length_bands:
        log.error("Missing config (topics/formats/tones/length_bands) — aborting.")
        sys.exit(1)

    topic = pick_topic(topics, posted_log)
    log.info(f"Selected topic: {topic}")

    recent_formats = [e.get("format_used") for e in posted_log[-NO_REPEAT_WINDOW:]]
    recent_tones = [e.get("tone_used") for e in posted_log[-NO_REPEAT_WINDOW:]]
    format_spec = pick_non_repeating(formats, recent_formats, key=lambda f: f["name"])
    tone = pick_non_repeating(tones, recent_tones)
    length_band = random.choice(length_bands)
    log.info(f"Format: {format_spec['name']} | Tone: {tone} | Length: {length_band['name']}")

    import time

    log.info("Running Scout...")
    scout_prompts = prompt_engineer.generate_prompt_for_agent("scout", topic)
    scout_result = scout.call_agent(scout_prompts["generated_system_prompt"], scout_prompts["generated_user_prompt"], use_web_search=True)
    log.info(f"Scout found {len(scout_result['output']['findings'])} items.")

    time.sleep(8)
    log.info("Running Curator...")
    curator_result = curator.run(scout_result, posted_log)
    selected = curator_result["output"]["selected_idea"]
    if not selected:
        log.warning(f"Curator found nothing fresh enough. Reason: "
                     f"{curator_result['output'].get('why_this_angle')}. Skipping this run.")
        sys.exit(0)
    log.info(f"Curator selected: {selected['headline']}")

    time.sleep(8)
    log.info("Running Lateral Thinker...")
    lat_prompts = prompt_engineer.generate_prompt_for_agent("lateral_thinker", topic, {"selected_idea": selected})
    lateral_result = lateral_thinker.call_agent(lat_prompts["generated_system_prompt"], lat_prompts["generated_user_prompt"], use_web_search=False)

    def write_post():
        time.sleep(8)
        copy_prompts = prompt_engineer.generate_prompt_for_agent(
            "copywriter",
            topic,
            {
                "lateral_output": lateral_result,
                "source_facts": selected,
                "format": format_spec,
                "tone": tone,
                "length": length_band
            }
        )
        result = copywriter.call_agent(copy_prompts["generated_system_prompt"], copy_prompts["generated_user_prompt"], use_web_search=False)
        return result["output"]["post_text"], result

    log.info("Running Copywriter...")
    post_text, copy_result = write_post()

    # Validation gate 1: generic-content heuristic
    if copywriter.sounds_generic(post_text) or not copywriter.within_length_band(post_text, length_band):
        log.warning("Post failed quality/length check. Re-running Copywriter once...")
        post_text, copy_result = write_post()
        if copywriter.sounds_generic(post_text) or not copywriter.within_length_band(post_text, length_band):
            log.error("Post still fails quality check after retry. Aborting without publishing.")
            sys.exit(1)

    # Validation gate 2: factual grounding
    time.sleep(8)
    log.info("Running Fact Checker...")
    fc_result = fact_checker.run(post_text, selected, lateral_result)
    if not fc_result["output"]["grounded"]:
        log.warning(f"Post failed grounding check: {fc_result['output']['issues']}. "
                     f"Re-running Copywriter once...")
        post_text, copy_result = write_post()
        time.sleep(8)
        fc_result = fact_checker.run(post_text, selected, lateral_result)
        if not fc_result["output"]["grounded"]:
            log.error(f"Post still ungrounded after retry: {fc_result['output']['issues']}. "
                       f"Aborting without publishing.")
            sys.exit(1)

    time.sleep(8)
    log.info("Running Visualizer...")
    vis_prompts = prompt_engineer.generate_prompt_for_agent("visualizer", topic, {"copywriter_output": copy_result["output"]})
    visual_result = visualizer.call_agent(vis_prompts["generated_system_prompt"], vis_prompts["generated_user_prompt"], use_web_search=False)
    prompt = visual_result["output"]["image_prompt"]
    
    style_suffix = (
        ", crisp DSLR architectural photography, corporate editorial style, "
        "natural sunlight, sharp focus on physical engineering media, "
        "real-world environmental aesthetic, no 3D renders, no cartoons, no text"
    )
    prompt = f"{prompt.rstrip('.')}{style_suffix}"
    image_path = visualizer._render_image_pollinations(prompt, IMAGE_PATH)

    if DRY_RUN:
        log.info("DRY RUN — not publishing. Final post preview:\n")
        print(post_text)
        print(f"\nHashtags: {copy_result['output']['hashtags']}")
        print(f"Format: {format_spec['name']} | Tone: {tone}")
        print(f"Image saved to: {image_path}")
        return

    log.info("Running Publisher...")
    publish_result = publisher.run(
        post_text=post_text,
        image_path=image_path,
        hashtags=copy_result["output"]["hashtags"],
    )

    if publish_result["output"]["status"] == "published":
        log.info(f"Published! post_id={publish_result['output']['post_id']}")
        
        # Save post text to a local file for easy verification/debugging
        with open(os.path.join(ROOT, "state", "latest_published_post.txt"), "w", encoding="utf-8") as f:
            f.write(f"POST TEXT:\n{post_text}\n\nHASHTAGS:\n{', '.join(copy_result['output']['hashtags'])}\n")

        posted_log.append({
            "headline": selected["headline"],
            "topic": topic,
            "format_used": format_spec["name"],
            "tone_used": tone,
            "date": datetime.now(timezone.utc).isoformat(),
            "post_id": publish_result["output"]["post_id"],
        })
        save_json(LOG_PATH, posted_log)
    else:
        log.error(f"Publish failed: {publish_result['output'].get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
