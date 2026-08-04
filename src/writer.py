"""
Step 2: Copywriter & 5-Part AI Prompt Engineer Agent
Generates clean LinkedIn commentary using Gemini API (or structured fallbacks) without AI buzzwords,
renders Unicode Bold headers, and constructs the 5-Part Prompt Blueprint for 3D AI Infographic slides.
"""

import os
import json
import logging
import requests

log = logging.getLogger("ecopulse")

FORBIDDEN_AI_PHRASES = [
    "in today's world",
    "in today's fast-paced world",
    "recent developments",
    "this highlights",
    "this underscores",
    "as industries evolve",
    "it is important to note",
    "with increasing awareness",
    "delve",
    "testament",
    "game-changer",
    "paradigm shift",
    "synergy",
    "beacon",
    "tapestry"
]


def to_unicode_bold(text: str) -> str:
    """
    Converts plain text to Unicode Sans-Serif Bold characters.
    LinkedIn does NOT render Markdown **bold**, but natively renders Unicode Bold.
    """
    res = []
    for char in text:
        if 'A' <= char <= 'Z':
            res.append(chr(0x1D5D4 + ord(char) - ord('A')))
        elif 'a' <= char <= 'z':
            res.append(chr(0x1D5EE + ord(char) - ord('a')))
        elif '0' <= char <= '9':
            res.append(chr(0x1D7EC + ord(char) - ord('0')))
        else:
            res.append(char)
    return "".join(res)


def generate_post_text_with_gemini(scout_data: dict, api_key: str) -> str:
    """
    Generates precision, evidence-backed post text using Gemini API with strict AI review rules.
    """
    headline = scout_data.get("headline", "")
    metric_left = scout_data.get("metric_left", "")
    metric_right = scout_data.get("metric_right", "")
    summary = scout_data.get("summary", "")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    prompt = (
        f"You are a Senior Environmental Engineering & ESG Analyst writing for Financial Times and Reuters.\n"
        f"Topic: {headline}\n"
        f"Baseline Metric: {metric_left}\n"
        f"Solution Metric: {metric_right}\n"
        f"Context: {summary}\n\n"
        f"WRITE A LINKEDIN POST FOLLOWING THESE STRICT RULES:\n"
        f"1. Hook: Start directly with a surprising numerical metric or friction point. NEVER use generic openings like 'In today's world' or 'Everyone is talking about'.\n"
        f"2. Paragraphs: Keep every paragraph strictly 1 to 2 short sentences long with clear line breaks.\n"
        f"3. Forbidden Words: NEVER use 'highlights', 'underscores', 'delve', 'testament', 'fast-paced world', 'paradigm shift'.\n"
        f"4. Structure:\n"
        f"   - Opening hook (1-2 sentences)\n"
        f"   - Core operational reality (1-2 sentences)\n"
        f"   - 🛠️ Benchmark comparison (Baseline vs Solution vs Audit Assurance)\n"
        f"   - 💡 Executive takeaway for sustainability and engineering leaders\n"
        f"   - 🤔 One precise technical question for discussion\n"
        f"5. Output plain text without markdown **bold** (Unicode bold formatting will be applied)."
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.6, "maxOutputTokens": 1000}
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts:
                    text = parts[0].get("text", "").strip()
                    # Sanitize forbidden phrases
                    lower_text = text.lower()
                    if not any(bad in lower_text for bad in FORBIDDEN_AI_PHRASES):
                        log.info("✅ Successfully generated post text via Gemini API")
                        return text
    except Exception as e:
        log.warning(f"Gemini post text generation error: {e}")

    return ""


def generate_post_text(scout_data: dict) -> str:
    """
    Generates structured, clean LinkedIn post text without generic AI filler.
    """
    gemini_key = (
        os.environ.get("GEMINI_API_KEY", "").strip() or
        os.environ.get("GOOGLE_API_KEY", "").strip()
    )

    if gemini_key:
        ai_post = generate_post_text_with_gemini(scout_data, gemini_key)
        if ai_post:
            return ai_post

    # Precision fallback template (Strictly avoiding forbidden AI buzzwords)
    headline = scout_data["headline"]
    metric_left = scout_data["metric_left"]
    metric_right = scout_data["metric_right"]
    summary = scout_data["summary"]

    header_bold = to_unicode_bold("THE ENGINEERING PIVOT: OPERATIONAL BREAKDOWN")
    takeaway_bold = to_unicode_bold("KEY TAKEAWAY FOR INFRASTRUCTURE & ESG LEADERS")
    question_bold = to_unicode_bold("Question for the network:")

    post = (
        f"If your industrial facility relies on legacy spend-based factor estimates, your carbon accounting balance sheet carries up to 38% unverified variance.\n\n"
        f"Here is the engineering reality behind {headline.split(':')[0]}: {summary}\n\n"
        f"🛠️ {header_bold}\n\n"
        f"1️⃣ Baseline Benchmark: {metric_left}.\n\n"
        f"2️⃣ Advanced Solution: {metric_right}.\n\n"
        f"3️⃣ Compliance & Audit Assurance: Direct telemetry alignment under BRSR Core 9 attributes and CSRD ESRS E1 standards replaces unverified spend multipliers.\n\n"
        f"💡 {takeaway_bold}\n\n"
        f"As operational density increases, legacy methods hit physical limits. Sustainability leadership belongs to closed-loop, audit-verified engineering.\n\n"
        f"🤔 {question_bold}\n"
        f"How is your engineering team evaluating direct operational telemetry versus spend-based factor estimates this quarter?\n\n"
        f"Let's discuss below. 👇\n\n"
        f"#Sustainability #CleanTech #ESG #EnvironmentalEngineering #EcoPulse"
    )
    return post


def construct_5part_ai_prompt(scout_data: dict) -> str:
    """
    Constructs the exact 5-Part AI Prompt Blueprint for 3D Isometric Infographic Slides.
    """
    headline = scout_data.get("headline", "")
    metric_left = scout_data.get("metric_left", "")
    metric_right = scout_data.get("metric_right", "")

    part1_title = f"A modern high-tech digital infographic presentation slide for LinkedIn titled '{headline}'."
    part2_color = "Dark theme aesthetic with deep indigo blue background (#0B132B) and glowing cyan and emerald glassmorphic cards."
    part3_diagram = "Includes a sleek 3D isometric rendering of an industrial server rack, solar tandem cell stack, or water treatment equipment with glowing coolant pipes, neon flow rays, and digital telemetry screens."
    part4_cards = f"Displays two side-by-side frosted glass comparison metric cards: Left Card: '{metric_left}'. Right Card: '{metric_right}'."
    part5_typography = "Sharp modern sans-serif typography, clean visual hierarchy, hyper-detailed executive presentation slide style, crisp resolution, 16:9 ratio."

    prompt_blueprint = f"{part1_title} {part2_color} {part3_diagram} {part4_cards} {part5_typography}"
    log.info(f"Generated 5-Part AI Prompt Blueprint: {prompt_blueprint[:120]}...")
    return prompt_blueprint
