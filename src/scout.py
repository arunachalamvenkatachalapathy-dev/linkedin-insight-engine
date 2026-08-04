"""
Step 1: News Scout & Data Distiller Agent
Scouts technical environmental engineering news live from real-time RSS feeds (ESG Today, DownToEarth, Google News)
and distills them via Gemini API into a headline, summary, and 2 contrasting numerical metrics.
"""

import os
import json
import random
import logging
import xml.etree.ElementTree as ET
import requests

log = logging.getLogger("ecopulse")

LIVE_RSS_FEEDS = [
    "https://www.esgtoday.com/feed/",
    "https://www.downtoearth.org.in/rss/environment"
]

TECHNICAL_TOPICS_FALLBACK = [
    {
        "headline": "AI Data Centers: The Hidden Water Footprint",
        "topic": "data center liquid cooling",
        "metric_left": "Traditional Evaporative Cooling: 1.8 Liters of fresh water consumed per kWh",
        "metric_right": "Closed-Loop Liquid Cooling: Zero water loss, 40% PUE efficiency reduction",
        "summary": "Evaporative cooling towers in hyper-scale data centers consume massive volumes of potable water. Transitioning to closed-loop direct-to-chip liquid cooling eliminates water evaporation completely while unlocking 100kW+ rack thermal density.",
        "source": "Clean Energy Engineering Review"
    },
    {
        "headline": "Perovskite-Silicon Tandem Solar: Breaking the Efficiency Ceiling",
        "topic": "perovskite tandem solar",
        "metric_left": "Conventional Silicon: 22% Commercial Module Efficiency",
        "metric_right": "Perovskite-Silicon Tandem: 33.9% Efficiency Record",
        "summary": "Commercial single-junction silicon panels are approaching the theoretical Shockley-Queisser ceiling (29.4%). Stacking a top perovskite layer captures high-energy blue photons while the bottom silicon absorbs infrared, breaking efficiency boundaries.",
        "source": "Nature Energy & PV Tech"
    },
    {
        "headline": "PFAS Destruction via Supercritical Water Oxidation (SCWO)",
        "topic": "pfas destruction technology",
        "metric_left": "Legacy Incineration: Hazardous fluorinated byproducts and high Scope 1 emissions",
        "metric_right": "Supercritical Water Oxidation: >99.99% PFAS destruction efficiency with zero toxic off-gas",
        "summary": "Supercritical water oxidation subjects contaminated industrial sludge to 374°C and 221 bar pressure, mineralizing recalcitrant C-F bonds into harmless inorganic fluoride salts without hazardous thermal emissions.",
        "source": "Water Environment Federation"
    },
    {
        "headline": "E-Waste Hydrometallurgical Gold & Copper Recovery",
        "topic": "circular economy and urban mining",
        "metric_left": "Pyrometallurgical Smelting: High energy intensity & toxic heavy metal atmospheric loss",
        "metric_right": "Closed-Loop Hydrometallurgy: 94% Copper & 89% Gold recovery with 40% lower carbon intensity",
        "summary": "Closed-loop hydrometallurgical leaching replaces high-temperature smelting for circuit board recycling, recovering critical metals using mild organic acids at ambient temperature.",
        "source": "ACS Sustainable Chemistry & Engineering"
    },
    {
        "headline": "Scope 3 Inventory: Primary Telemetry vs Spend-Based Proxies",
        "topic": "Scope 1-3 GHG accounting",
        "metric_left": "EEIO Spend-Based Factor Proxies: +/-25% Inventory Uncertainty",
        "metric_right": "Primary Supplier Sensor Telemetry: +/-3.2% Audit-Verified Accuracy",
        "summary": "Replacing spend multipliers with direct IoT sensor telemetry reduces carbon accounting variance, providing third-party reasonable assurance audit trails for BRSR Core and CSRD disclosures.",
        "source": "ESG Regulatory & Compliance Journal"
    }
]


def fetch_live_news_items() -> list:
    """Fetches real-time environmental news items from live RSS feeds."""
    news_items = []
    for feed_url in LIVE_RSS_FEEDS:
        try:
            resp = requests.get(feed_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                for item in root.findall(".//item")[:5]:
                    title = item.findtext("title", "")
                    link = item.findtext("link", "")
                    description = item.findtext("description", "")
                    if title:
                        news_items.append({"title": title, "link": link, "description": description[:300]})
        except Exception as e:
            log.warning(f"Error fetching RSS feed {feed_url}: {e}")
    return news_items


def distill_news_item_with_gemini(news_item: dict, api_key: str) -> dict:
    """Distills a live news item into headline, summary, and 2 numerical metrics via Gemini API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    prompt = (
        f"Distill this environmental news article into a structured technical analysis.\n"
        f"Article Title: {news_item.get('title')}\n"
        f"Description: {news_item.get('description')}\n\n"
        f"Return valid JSON with keys:\n"
        f"- 'headline': Executive title (max 8 words)\n"
        f"- 'topic': Short topic key\n"
        f"- 'metric_left': Baseline metric (e.g. 'Legacy Method: 22% Efficiency')\n"
        f"- 'metric_right': Advanced metric (e.g. 'New Technology: 33.9% Efficiency')\n"
        f"- 'summary': 2-sentence technical summary\n"
        f"- 'source': 'ESG Today & Industry Reports'"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.5, "responseMimeType": "application/json"}
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts:
                    return json.loads(parts[0].get("text", ""))
    except Exception as e:
        log.warning(f"Gemini news distillation error: {e}")

    return None


def scout_topic(posted_log: list) -> dict:
    """
    Selects a fresh, non-repetitive topic distilled from live RSS feeds or fallback curated data.
    """
    posted_headlines = {entry.get("headline", "").lower() for entry in posted_log if entry.get("headline")}
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("GOOGLE_API_KEY", "").strip()

    # Try Live RSS News Scouting first
    if gemini_key:
        live_news = fetch_live_news_items()
        for item in live_news:
            if item.get("title", "").lower() not in posted_headlines:
                distilled = distill_news_item_with_gemini(item, gemini_key)
                if distilled and "headline" in distilled:
                    log.info(f"✅ Scouted live RSS news: '{distilled['headline']}'")
                    return distilled

    # Fallback to curated non-repetitive list
    available_topics = [t for t in TECHNICAL_TOPICS_FALLBACK if t["headline"].lower() not in posted_headlines]
    if not available_topics:
        available_topics = TECHNICAL_TOPICS_FALLBACK

    selected = random.choice(available_topics)
    log.info(f"Scout selected topic: '{selected['headline']}'")
    return selected
