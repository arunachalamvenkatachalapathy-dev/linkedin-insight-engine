"""
EcoPulse LinkedIn Engine — Main Orchestrator
Executes the clean 4-Step Pipeline:
Step 1: News Scout & Data Distiller (scout.py)
Step 2: Copywriter & 5-Part AI Prompt Engineer (writer.py)
Step 3: 3D AI Infographic Slide Generator (visualizer.py)
Step 4: LinkedIn Publisher (publisher.py)
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load local .env variables automatically if present
load_dotenv()

from src import scout, writer, visualizer, publisher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("ecopulse")


def main():
    log.info("═══ Starting EcoPulse Clean 4-Step LinkedIn Engine ═══")

    # Load posted history for deduplication
    posted_log_path = os.path.join("state", "posted_log.json")
    posted_log = []
    if os.path.exists(posted_log_path):
        try:
            with open(posted_log_path, "r", encoding="utf-8") as f:
                posted_log = json.load(f)
        except Exception:
            posted_log = []

    # Step 1: Scout & Distill Data
    log.info("═══ Step 1: Scouting & Distilling Data Metrics ═══")
    scout_data = scout.scout_topic(posted_log)

    # Step 2: Write Post Copy & Construct 5-Part AI Prompt Blueprint
    log.info("═══ Step 2: Writing Post Copy & 5-Part AI Prompt Blueprint ═══")
    post_text = writer.generate_post_text(scout_data)
    prompt_blueprint = writer.construct_5part_ai_prompt(scout_data)

    # Step 3: Render 3D AI Infographic Slide Image
    log.info("═══ Step 3: Rendering 3D AI Infographic Slide ═══")
    slide_path = visualizer.render_3d_slide(prompt_blueprint, scout_data, out_path="state/latest_slide.png")

    # Step 4: Publish to LinkedIn
    log.info("═══ Step 4: Publishing to LinkedIn ═══")
    pub_res = publisher.publish_to_linkedin(post_text, slide_path)

    # Save posted log memory
    if pub_res.get("status") in ["published", "dry_run"]:
        posted_log.append({
            "headline": scout_data.get("headline"),
            "topic": scout_data.get("topic"),
            "date": datetime.now(timezone.utc).isoformat(),
            "post_id": pub_res.get("post_id"),
            "post_url": pub_res.get("post_url")
        })
        os.makedirs("state", exist_ok=True)
        with open(posted_log_path, "w", encoding="utf-8") as f:
            json.dump(posted_log, f, indent=2)

    log.info("═══ Engine Run Completed Successfully ═══")


if __name__ == "__main__":
    main()
