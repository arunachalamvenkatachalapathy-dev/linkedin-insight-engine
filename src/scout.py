"""
Step 1: News Scout & Data Distiller Agent
Scouts technical environmental engineering news & topics, and distills them into a headline and 2 contrasting numerical metrics.
"""

import random
import logging
import xml.etree.ElementTree as ET
import requests

log = logging.getLogger("ecopulse")

RSS_FEEDS = [
    "https://www.esgtoday.com/feed/",
    "https://www.downtoearth.org.in/rss/environment"
]

TECHNICAL_TOPICS = [
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


def scout_topic(posted_log: list) -> dict:
    """
    Selects a fresh, non-repetitive topic distilled into a headline, summary, and 2 contrasting metrics.
    """
    posted_headlines = {entry.get("headline", "").lower() for entry in posted_log}
    
    # Filter out already posted topics
    available_topics = [t for t in TECHNICAL_TOPICS if t["headline"].lower() not in posted_headlines]
    
    if not available_topics:
        available_topics = TECHNICAL_TOPICS

    selected = random.choice(available_topics)
    log.info(f"Scout selected topic: '{selected['headline']}'")
    return selected
