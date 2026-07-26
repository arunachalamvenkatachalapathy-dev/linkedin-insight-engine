"""
EcoPulse root orchestrator — Multi-Agent Architecture v2.
Pipeline: Manager → Planner → Content(+Repetition) → Header/Body/Footer → Stitcher → Checker → Image → Publish

Run via: python orchestrator.py
Reads config/niche_topics.json, config/post_formats.json, config/tones.json, and
state/posted_log.json, runs the 11-agent pipeline, and (if everything validates)
publishes to LinkedIn.
"""
import os
import sys
import json
import random
import logging
import time
from datetime import datetime, timezone

# Load env variables from local .env
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k.strip()] = v.strip()

sys.path.insert(0, os.path.dirname(__file__))

from agents import (  # noqa: E402
    prompt_engineer,
    planner,
    content,
    header,
    body,
    footer,
    stitcher,
    checker,
    image,
    publisher,
)

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
MAX_CHECKER_RETRIES = 2  # max times to re-run writing agents if checker fails


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def pick_topic(topics: list, posted_log: list) -> str:
    """Pick a topic, avoiding any topic used in the last 15 posts."""
    recent_topics = [e.get("topic", "").lower() for e in posted_log[-15:]]
    candidates = [t for t in topics if t.lower() not in recent_topics] or topics
    return random.choice(candidates)


def pick_non_repeating(pool: list, recent_used: list, key=lambda x: x):
    """Pick a random item from pool, avoiding anything in recent_used if possible."""
    candidates = [item for item in pool if key(item) not in recent_used] or pool
    return random.choice(candidates)


def main():
    # ──────────────────────────────────────────────
    # LOAD CONFIGURATION
    # ──────────────────────────────────────────────
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

    # ──────────────────────────────────────────────
    # STEP 1: PLANNER — decide angle, format, tone
    # ──────────────────────────────────────────────
    log.info("═══ STEP 1: Running Planner ═══")
    try:
        pe_planner = prompt_engineer.generate_prompt_for_agent("planner", topic, {
            "formats": [f["name"] for f in formats],
            "tones": tones,
            "length_bands": [lb["name"] for lb in length_bands],
            "recent_posts": posted_log[-NO_REPEAT_WINDOW:]
        })
        from llm import call_agent as llm_call
        planner_result = llm_call(
            pe_planner.get("generated_system_prompt", planner.SYSTEM_PROMPT),
            pe_planner.get("generated_user_prompt", f"Topic: {topic}")
        )
    except Exception as e:
        log.warning(f"Prompt-engineered planner failed ({e}), using fallback...")
        planner_result = planner.run(topic, formats, tones, length_bands, posted_log)

    planner_output = planner_result.get("output", planner_result)
    angle = planner_output.get("angle", topic)
    format_name = planner_output.get("format_name", "")
    tone_name = planner_output.get("tone_name", "")
    length_band_name = planner_output.get("length_band_name", "")

    # Resolve names to full specs from config
    format_spec = next((f for f in formats if f["name"] == format_name), random.choice(formats))
    tone = tone_name if tone_name in tones else random.choice(tones)
    length_band = next((lb for lb in length_bands if lb["name"] == length_band_name), random.choice(length_bands))

    log.info(f"Planner decided — Angle: {angle} | Format: {format_spec['name']} | Tone: {tone} | Length: {length_band['name']}")

    # ──────────────────────────────────────────────
    # STEP 2: CONTENT — source facts + lateral insight + repetition check
    # ──────────────────────────────────────────────
    time.sleep(5)
    log.info("═══ STEP 2: Running Content Agent ═══")
    try:
        pe_content = prompt_engineer.generate_prompt_for_agent("content", topic, {
            "angle": angle,
            "posted_log_headlines": [e.get("headline", "") for e in posted_log]
        })
        from llm import call_agent as llm_call
        content_result = llm_call(
            pe_content.get("generated_system_prompt", content.SYSTEM_PROMPT),
            pe_content.get("generated_user_prompt", f"Topic: {topic}"),
            use_web_search=True,
            max_tokens=6000
        )
    except Exception as e:
        log.warning(f"Prompt-engineered content failed ({e}), using fallback...")
        content_result = content.run(topic, posted_log)

    content_output = content_result.get("output", content_result)
    selected_idea = content_output.get("selected_idea")

    # If prompt-engineered content found nothing, try direct fallback
    if not selected_idea:
        log.warning("Prompt-engineered content found nothing. Trying direct content agent fallback...")
        content_result = content.run(topic, posted_log)
        content_output = content_result.get("output", content_result)
        selected_idea = content_output.get("selected_idea")

    if not selected_idea:
        log.warning("Content agent found nothing fresh enough. Skipping this run.")
        sys.exit(0)

    log.info(f"Content selected: {selected_idea.get('headline', 'N/A')}")

    # Build the shared brief that Header/Body/Footer all read from
    plan = {
        "angle": angle,
        "format_name": format_spec["name"],
        "format_spec": format_spec,
        "tone_name": tone,
        "length_band": length_band,
    }
    content_brief = {
        "selected_idea": selected_idea,
        "insight": content_output.get("insight", {}),
    }

    # ──────────────────────────────────────────────
    # STEPS 3-6: HEADER → BODY → FOOTER → STITCHER (with Checker retry loop)
    # ──────────────────────────────────────────────
    final_post_text = None
    hashtags = []

    for checker_attempt in range(MAX_CHECKER_RETRIES + 1):
        # STEP 3: HEADER
        time.sleep(5)
        log.info(f"═══ STEP 3: Running Header Agent (attempt {checker_attempt + 1}) ═══")
        header_result = header.run(plan, content_brief)
        header_text = header_result.get("output", header_result).get("header_text", "")
        log.info(f"Header: {header_text[:80]}...")

        # STEP 4: BODY
        time.sleep(5)
        log.info(f"═══ STEP 4: Running Body Agent (attempt {checker_attempt + 1}) ═══")
        body_result = body.run(plan, content_brief, header_text)
        body_text = body_result.get("output", body_result).get("body_text", "")
        log.info(f"Body: {body_text[:80]}...")

        # STEP 5: FOOTER
        time.sleep(5)
        log.info(f"═══ STEP 5: Running Footer Agent (attempt {checker_attempt + 1}) ═══")
        footer_result = footer.run(plan, content_brief, header_text, body_text)
        footer_output = footer_result.get("output", footer_result)
        footer_text = footer_output.get("footer_text", "")
        hashtags = footer_output.get("hashtags", [])
        log.info(f"Footer: {footer_text[:80]}...")

        # STEP 6: STITCHER
        time.sleep(5)
        log.info(f"═══ STEP 6: Running Stitcher Agent (attempt {checker_attempt + 1}) ═══")
        stitcher_result = stitcher.run(header_text, body_text, footer_text, tone)
        stitcher_output = stitcher_result.get("output", stitcher_result) if isinstance(stitcher_result, dict) else {}
        final_post_text = stitcher_output.get("final_post_text") if isinstance(stitcher_output, dict) else None

        # Fail-safe assembly if stitcher returned empty or truncated title-only text
        if not final_post_text or len(final_post_text.split()) < 30:
            log.warning("Stitcher text missing or truncated. Performing fail-safe concatenation of header + body + footer...")
            final_post_text = f"{header_text}\n\n{body_text}\n\n{footer_text}"

        word_count = len(final_post_text.split())
        log.info(f"Stitcher assembled post: {word_count} words")

        # ──────────────────────────────────────────────
        # STEP 7: CHECKER — fact-check + quality gate
        # ──────────────────────────────────────────────
        time.sleep(5)
        log.info(f"═══ STEP 7: Running Checker Agent (attempt {checker_attempt + 1}) ═══")

        # Local heuristic checks first
        if checker.sounds_generic(final_post_text):
            log.warning("Post failed local generic-content heuristic check.")
            if checker_attempt < MAX_CHECKER_RETRIES:
                log.info("Retrying writing agents...")
                continue
            else:
                log.error("Post still generic after max retries. Aborting.")
                sys.exit(1)

        if not checker.within_length_band(final_post_text, length_band):
            log.warning(f"Post failed length check (got {len(final_post_text.split())} words, "
                        f"band: {length_band['min_words']}-{length_band['max_words']}).")
            if checker_attempt < MAX_CHECKER_RETRIES:
                log.info("Retrying writing agents...")
                continue
            else:
                log.error("Post still wrong length after max retries. Aborting.")
                sys.exit(1)

        # LLM-based deep check
        checker_result = checker.run(
            post_text=final_post_text,
            source_facts=selected_idea,
            lateral_insight=content_output.get("insight", {}),
            format_spec=format_spec,
            tone=tone,
            length_band=length_band
        )
        checker_output = checker_result.get("output", checker_result)
        passed = checker_output.get("passed", False)
        issues = checker_output.get("issues", [])
        grounding_score = checker_output.get("grounding_score", 0)

        log.info(f"Checker verdict: passed={passed}, score={grounding_score}, issues={issues}")

        if passed:
            log.info("✅ Post passed all quality checks!")
            break
        else:
            if checker_attempt < MAX_CHECKER_RETRIES:
                log.warning(f"Checker failed (issues: {issues}). Retrying writing agents...")
                continue
            else:
                log.error(f"Post failed checker after {MAX_CHECKER_RETRIES + 1} attempts. Aborting.")
                sys.exit(1)

    # ──────────────────────────────────────────────
    # STEP 8: IMAGE — generate + render via Stable Diffusion
    # ──────────────────────────────────────────────
    time.sleep(5)
    log.info("═══ STEP 8: Running Image Agent ═══")
    image_brief = {
        "post_text": final_post_text,
        "image_brief": f"Professional DSLR photograph related to: {angle}",
        "topic": topic,
    }
    image_result = image.run(copywriter_output=image_brief, out_path=IMAGE_PATH)
    image_output = image_result.get("output", image_result)
    image_path = image_output.get("image_path")
    model_used = image_output.get("model_used", "unknown")
    log.info(f"Image generated via {model_used}: {image_path}")

    # ──────────────────────────────────────────────
    # STEP 9: PUBLISH (or dry-run)
    # ──────────────────────────────────────────────
    if DRY_RUN:
        log.info("═══ DRY RUN — not publishing ═══")
        print("\n" + "=" * 60)
        print("FINAL POST PREVIEW:")
        print("=" * 60)
        print(final_post_text)
        print(f"\nHashtags: {hashtags}")
        print(f"Format: {format_spec['name']} | Tone: {tone} | Angle: {angle}")
        print(f"Image: {image_path} (model: {model_used})")
        print(f"Word count: {word_count}")
        print("=" * 60)
        return

    log.info("═══ STEP 9: Running Publisher ═══")

    # Pre-publish safety validation
    assert final_post_text and len(final_post_text.split()) >= 30, \
        f"ABORT: final_post_text is too short ({len(final_post_text.split()) if final_post_text else 0} words)"
    log.info(f"Pre-publish validation: {len(final_post_text.split())} words, {len(final_post_text)} chars")
    log.info(f"First 300 chars of post: {final_post_text[:300]}")

    publish_result = publisher.run(
        post_text=final_post_text,
        image_path=image_path,
        hashtags=hashtags,
    )

    if publish_result["output"]["status"] == "published":
        post_id = publish_result["output"]["post_id"]
        log.info(f"✅ Published! post_id={post_id}")

        # Save post text for verification
        with open(os.path.join(ROOT, "state", "latest_published_post.txt"), "w", encoding="utf-8") as f:
            f.write(f"POST TEXT:\n{final_post_text}\n\nHASHTAGS:\n{', '.join(hashtags)}\n"
                    f"\nFORMAT: {format_spec['name']}\nTONE: {tone}\nANGLE: {angle}\n"
                    f"\nIMAGE MODEL: {model_used}\n")

        posted_log.append({
            "headline": selected_idea.get("headline", angle),
            "topic": topic,
            "format_used": format_spec["name"],
            "tone_used": tone,
            "angle": angle,
            "date": datetime.now(timezone.utc).isoformat(),
            "post_id": post_id,
        })
        save_json(LOG_PATH, posted_log)
    else:
        log.error(f"Publish failed: {publish_result['output'].get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
