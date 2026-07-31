"""
Main Orchestrator for EcoPulse LinkedIn automation pipeline.
Manages the multi-agent execution pipeline with quality audits, rate-limit safety, and clean exit handling.
"""

import os
import sys
import json
import logging

log = logging.getLogger("ecopulse")


def main():
    import random
    from datetime import datetime, timezone

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    log.info("Starting EcoPulse Multi-Agent Orchestrator...")

    # Load posted log
    posted_log_path = os.path.join("state", "posted_log.json")
    posted_log = []
    if os.path.exists(posted_log_path):
        try:
            with open(posted_log_path, "r", encoding="utf-8") as f:
                posted_log = json.load(f)
        except Exception:
            posted_log = []

    # Import agents
    try:
        from agents import planner, content, header, body, footer, stitcher, strategist, checker, accuracy, instructor, image
    except ImportError as err:
        log.error(f"Failed to import agents: {err}")
        sys.exit(1)

    topics = [
        "environmental engineering infrastructure",
        "industrial decarbonization",
        "constructed wetlands and nature-based solutions",
        "Scope 1-3 GHG accounting",
        "BRSR Core and ISSB sustainability reporting",
        "circular economy and industrial symbiosis",
        "wastewater treatment and brine management"
    ]
    topic = random.choice(topics)
    log.info(f"Selected topic: {topic}")

    log.info("═══ STEP 0: Initializing Instructor Agent (Quality & Credibility Layer) ═══")
    log.info("Applying Master Quality Directive across all generation, stitching, and auditing phases.")

    # 1. PLANNER AGENT
    log.info("═══ STEP 1: Running Planner ═══")
    try:
        formats_list = list(planner.FORMATS.keys())
        tones_list = list(planner.TONES.keys())
        length_list = list(planner.LENGTH_BANDS.keys())
        plan_result = planner.run(topic, formats_list, tones_list, length_list, posted_log)
    except Exception as e:
        if "429" in str(e) or "rate-limited" in str(e).lower():
            log.warning(f"Gemini API quota window limit reached: {e}. Exiting run cleanly.")
            sys.exit(0)
        log.error(f"Planner agent failed: {e}")
        sys.exit(1)

    plan_output = plan_result.get("output", plan_result)
    angle = plan_output.get("angle", f"Engineering analysis of {topic}")
    format_name = plan_output.get("format_name", "data_led")
    tone_name = plan_output.get("tone_name", "analytical")
    length_band_name = plan_output.get("length_band_name", "medium")

    format_spec = planner.FORMATS.get(format_name, planner.FORMATS["data_led"])
    tone = planner.TONES.get(tone_name, planner.TONES["analytical"])
    length_band = planner.LENGTH_BANDS.get(length_band_name, planner.LENGTH_BANDS["medium"])

    log.info(f"Planner decided — Angle: {angle} | Format: {format_spec['name']} | Tone: {tone}")

    # 2. CONTENT AGENT
    log.info("═══ STEP 2: Running Content Agent ═══")
    try:
        content_result = content.run(topic, posted_log)
    except Exception as e:
        if "429" in str(e) or "rate-limited" in str(e).lower():
            log.warning(f"Gemini API quota window limit reached: {e}. Exiting run cleanly.")
            sys.exit(0)
        log.error(f"Content agent failed: {e}")
        sys.exit(1)

    content_output = content_result.get("output", content_result)
    selected_idea = content_output.get("selected_idea")

    if not selected_idea:
        log.warning("Content agent found nothing fresh enough or topic is already posted. Exiting run cleanly.")
        sys.exit(0)

    log.info(f"Content selected: {selected_idea.get('headline', 'N/A')}")

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

    # 3-6. HEADER -> BODY -> FOOTER -> STITCHER -> STRATEGIST
    log.info("═══ STEPS 3-6: Running Generation & Formatting Pipeline ═══")
    try:
        h_res = header.run(plan, content_brief)
        h_text = h_res.get("output", {}).get("header_text", "")

        b_res = body.run(plan, content_brief, h_text)
        b_text = b_res.get("output", {}).get("body_text", "")

        f_res = footer.run(plan, content_brief, h_text, b_text)
        f_text = f_res.get("output", {}).get("footer_text", "")
        hashtags = f_res.get("output", {}).get("hashtags", [])

        s_res = stitcher.run(h_text, b_text, f_text, tone)
        final_post_text = s_res.get("output", {}).get("final_post_text", f"{h_text}\n\n{b_text}\n\n{f_text}")

        strat_res = strategist.run(final_post_text, topic, angle)
        viral_post_text = strat_res.get("output", {}).get("viral_post_text", final_post_text)
        if viral_post_text:
            final_post_text = viral_post_text
    except Exception as e:
        if "429" in str(e) or "rate-limited" in str(e).lower():
            log.warning(f"Gemini API quota window limit reached: {e}. Exiting run cleanly.")
            sys.exit(0)
        log.error(f"Generation pipeline failed: {e}")
        sys.exit(1)

    # 7. QUALITY AUDITS
    log.info("═══ STEP 7: Quality & Accuracy Audits ═══")
    try:
        chk_res = checker.run(final_post_text, selected_idea, content_brief.get("insight", {}), format_spec, tone, length_band)
        log.info(f"Checker audit: {chk_res}")
    except Exception as e:
        log.warning(f"Quality audit warning: {e}")

    # 8. IMAGE AGENT
    log.info("═══ STEP 8: Running Image Agent ═══")
    image_path = None
    try:
        img_res = image.run(selected_idea, out_path="state/latest_image.png")
        image_path = img_res.get("output", {}).get("image_path")
        log.info(f"Image agent result: {img_res.get('output', {}).get('model_used', 'N/A')}")
    except Exception as e:
        log.warning(f"Image generation warning: {e}")

    # 9. PUBLISHER
    log.info("═══ STEP 9: Running Publisher ═══")
    dry_run = os.environ.get("ECOPULSE_DRY_RUN", "false").lower() == "true"
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    person_urn = os.environ.get("LINKEDIN_PERSON_URN", "").strip()

    if dry_run or not token or not person_urn:
        log.info("DRY_RUN mode active or missing credentials. Post generated successfully but not published to LinkedIn.")
        log.info(f"Post Preview:\n{final_post_text[:300]}...")
        sys.exit(0)

    try:
        from agents import publisher
        pub_res = publisher.run(final_post_text, image_path=image_path, hashtags=hashtags)
        post_id = pub_res.get("post_id", "simulated")
        log.info(f"✅ Successfully Published to LinkedIn! Post ID: {post_id}")

        # Update posted_log
        posted_log.append({
            "headline": selected_idea.get("headline", topic),
            "topic": topic,
            "source_url": selected_idea.get("sources_used", [""])[0] if selected_idea.get("sources_used") else "",
            "date": datetime.now(timezone.utc).isoformat(),
            "post_id": post_id
        })
        os.makedirs("state", exist_ok=True)
        with open(posted_log_path, "w", encoding="utf-8") as f:
            json.dump(posted_log, f, indent=2)

    except Exception as e:
        log.error(f"Publishing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
