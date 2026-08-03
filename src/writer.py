"""
Step 2: Copywriter & 5-Part AI Prompt Engineer Agent
Generates high-impact formatted LinkedIn post text and constructs the 5-Part Prompt Blueprint for 3D AI Infographic slides.
"""

import json
import logging
import requests
import os

log = logging.getLogger("ecopulse")


def generate_post_text(scout_data: dict) -> str:
    """
    Generates structured, highly readable LinkedIn post text.
    """
    headline = scout_data["headline"]
    metric_left = scout_data["metric_left"]
    metric_right = scout_data["metric_right"]
    summary = scout_data["summary"]
    source = scout_data["source"]

    post = (
        f"Everyone is talking about energy efficiency in industrial infrastructure.\n\n"
        f"Almost nobody is talking about the core engineering breakthrough in {headline.split(':')[0]}. 💡\n\n"
        f"Here is the operational reality: {summary}\n\n"
        f"🛠️ **THE ENGINEERING PIVOT: OPERATIONAL BREAKDOWN**\n\n"
        f"1️⃣ **Baseline Benchmark:** {metric_left}.\n\n"
        f"2️⃣ **Advanced Technology Solution:** {metric_right}.\n\n"
        f"3️⃣ **Compliance & Audit Assurance:** Direct telemetry alignment under BRSR Core Core 9 attributes and CSRD ESRS E1 standards replaces unverified spend multipliers.\n\n"
        f"💡 **KEY TAKEAWAY FOR INFRASTRUCTURE & ESG LEADERS**\n\n"
        f"As operational density increases, legacy methods hit physical limits. Sustainability leadership belongs to closed-loop, audit-verified engineering.\n\n"
        f"---\n\n"
        f"🤔 **Question for the network:**\n"
        f"How is your engineering team evaluating direct operational telemetry versus spend-based factor estimates this quarter? What is the biggest friction point?\n\n"
        f"Let's discuss below. 👇\n\n"
        f"#Sustainability #CleanTech #ESG #EnvironmentalEngineering #EcoPulse"
    )
    return post


def construct_5part_ai_prompt(scout_data: dict) -> str:
    """
    Constructs the exact 5-Part AI Prompt Blueprint for 3D Isometric Infographic Slides.
    Blueprint: [1. TITLE & THEME] + [2. COLOR & AESTHETIC] + [3. 3D ISOMETRIC DIAGRAM] + [4. SIDE-BY-SIDE DATA CARDS] + [5. TYPOGRAPHY & RATIO]
    """
    headline = scout_data["headline"]
    metric_left = scout_data["metric_left"]
    metric_right = scout_data["metric_right"]

    part1_title = f"A modern high-tech digital infographic presentation slide for LinkedIn titled '{headline}'."
    part2_color = "Dark theme aesthetic with deep indigo blue background (#0B132B) and glowing cyan and emerald glassmorphic cards."
    part3_diagram = "Includes a sleek 3D isometric rendering of an industrial server rack, solar tandem cell stack, or water treatment equipment with glowing coolant pipes, neon flow rays, and digital telemetry screens."
    part4_cards = f"Displays two side-by-side frosted glass comparison metric cards: Left Card: '{metric_left}'. Right Card: '{metric_right}'."
    part5_typography = "Sharp modern sans-serif typography, clean visual hierarchy, hyper-detailed executive presentation slide style, crisp resolution, 16:9 ratio."

    prompt_blueprint = f"{part1_title} {part2_color} {part3_diagram} {part4_cards} {part5_typography}"
    log.info(f"Generated 5-Part AI Prompt Blueprint: {prompt_blueprint[:120]}...")
    return prompt_blueprint
