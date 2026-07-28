"""
Standalone RSS-to-LinkedIn Generator script.
Act as a Senior Environmental Engineer and Corporate ESG & Sustainability Specialist.
Scouts trending RSS sustainability news, checks against state/posted_log.json to prevent duplicates,
generates a high-value technical LinkedIn post using Google Gemini AI, and outputs formatted JSON.
"""

import os
import json
import re
import sys
import logging

# Ensure scripts directory is on PATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))

try:
    import rss_scout
except ImportError:
    rss_scout = None

log = logging.getLogger("ecopulse")

POSTED_LOG_FILE = os.path.join("state", "posted_log.json")


def load_posted_log() -> list:
    if os.path.exists(POSTED_LOG_FILE):
        with open(POSTED_LOG_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def generate_post_from_rss() -> dict:
    posted_log = load_posted_log()

    # 1. Fetch fresh unused RSS article
    fresh_articles = []
    if rss_scout:
        fresh_articles = rss_scout.fetch_fresh_rss_articles(posted_log, max_articles=5)

    if not fresh_articles:
        # Fallback RSS feeds directly if rss_scout returned empty
        import feedparser
        FEEDS = [
            "https://www.esgtoday.com/feed/",
            "https://www.greenbiz.com/rss.xml",
            "https://sustainability.economictimes.indiatimes.com/rss/esg",
            "https://climate.nasa.gov/news/rss",
            "https://www.downtoearth.org.in/rss/environment"
        ]
        posted_urls = {entry.get("source_url", "").strip().lower() for entry in posted_log if "source_url" in entry}

        for feed_url in FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    link = getattr(entry, "link", "").strip()
                    title = getattr(entry, "title", "").strip()
                    summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                    clean_summary = re.sub(r"<[^>]+>", "", summary).strip()[:400]

                    if link and link.lower() not in posted_urls:
                        fresh_articles.append({
                            "title": title,
                            "summary": clean_summary,
                            "link": link,
                            "source_url": link
                        })
                        break
            except Exception as e:
                log.warning(f"Error parsing {feed_url}: {e}")
            if fresh_articles:
                break

    if not fresh_articles:
        raise Exception("No new RSS items found today that haven't been posted before.")

    selected_article = fresh_articles[0]

    # 2. Construct Senior Environmental Engineer Prompt
    prompt = f"""You are acting as a Senior Environmental Engineer and Corporate ESG & Sustainability Specialist.

### CONTEXT & INPUT DATA
- ARTICLE HEADLINE: {selected_article['title']}
- ARTICLE SUMMARY: {selected_article['summary']}
- ARTICLE SOURCE URL: {selected_article['link']}

### GOAL
Transform this raw news item into an insightful, highly engaging, and technical LinkedIn post that demonstrates deep domain expertise in corporate sustainability, environmental compliance, and green technology.

---

### CONTENT & STRUCTURAL REQUIREMENTS

1. HOOK (Line 1):
   - Lead with a powerful, attention-grabbing statement or data point highlighting the core strategic/regulatory shift mentioned in the news item.
   - Avoid generic openers like "In today's world..." or "Exciting news!"

2. TECHNICAL & REGULATORY BREAKDOWN (Paragraphs 2 & 3):
   - Translate the high-level news into concrete implications for technical teams and ESG managers.
   - Ground the commentary in established environmental engineering and ESG frameworks where applicable (e.g., BRSR Core, GRI 12/GRI Standards, GHG Protocol Scope 1/2/3, TCFD/ISSB, Circular Economy metrics, or Wastewater/Remediation principles).
   - Explain *why* this matters from a risk management, operational, or compliance perspective.

3. PRACTICAL ESG TAKEAWAYS (Bullet Points):
   - Provide 2–3 practical, actionable takeaways or operational steps for corporate sustainability officers, engineers, or analysts.

4. CALL TO ACTION / DISCUSSION PROMPT (Final Line):
   - End with a thought-provoking, open-ended question designed to drive high-value comments and technical discussions from peers in the sustainability space.

---

### TONAL & FORMATTING RULES
- Tone: Analytical, authoritative, professional, yet accessible. Speak as a practicing engineering peer, not a generic marketer.
- Formatting: Use short paragraphs (1-3 sentences each) and clean bullet points for scannability on mobile screens.
- Emojis: Use sparingly (maximum 2–3 relevant emojis total) to maintain a professional tone.

---

### OUTPUT FORMAT CONSTRAINT
Return ONLY a valid raw JSON object matching this structure exactly:
{{
  "source_url": "{selected_article['link']}",
  "topic_summary": "{selected_article['title']}",
  "post_content": "The complete formatted string of your LinkedIn post..."
}}
"""

    # 3. Call LLM (via scripts/llm.py)
    from llm import call_agent
    result = call_agent(
        system_prompt="You are a Senior Environmental Engineer and Corporate ESG & Sustainability Specialist. Return ONLY valid JSON.",
        user_content=prompt,
        max_tokens=4000
    )

    source_url = result.get("source_url") or selected_article["link"]
    topic_summary = result.get("topic_summary") or selected_article["title"]
    post_content = result.get("post_content") or result.get("final_post_text", "")

    if not post_content and isinstance(result, dict):
        # Extract post_content from alternate keys if needed
        post_content = str(result)

    new_post_data = {
        "source_url": source_url,
        "topic_summary": topic_summary,
        "headline": topic_summary,
        "topic": "corporate ESG & sustainability",
        "post_content": post_content,
        "date": json.loads(json.dumps(os.environ.get("GITHUB_RUN_ID", "local")))
    }

    print("Successfully generated post from RSS article:")
    print(f"Title: {topic_summary}")
    print(f"Source URL: {source_url}")

    return new_post_data


if __name__ == "__main__":
    post_data = generate_post_from_rss()
    print(json.dumps(post_data, indent=2))
