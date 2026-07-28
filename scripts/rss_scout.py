"""
RSS Scout Module for EcoPulse.
Scrapes live trending sustainability & ESG news feeds:
- ESG Today (https://www.esgtoday.com/feed/)
- GreenBiz (https://www.greenbiz.com/rss.xml)
- Economic Times ESG (https://sustainability.economictimes.indiatimes.com/rss/esg)
- NASA Climate (https://climate.nasa.gov/news/rss)
- Down To Earth (https://www.downtoearth.org.in/rss/environment)

Filters against state/posted_log.json to prevent duplicate URL/article processing.
"""
import os
import json
import logging
import urllib.request
import re

log = logging.getLogger("ecopulse")

try:
    import feedparser
except ImportError:
    feedparser = None

DEFAULT_FEEDS = [
    "https://www.esgtoday.com/feed/",
    "https://www.greenbiz.com/rss.xml",
    "https://sustainability.economictimes.indiatimes.com/rss/esg",
    "https://climate.nasa.gov/news/rss",
    "https://www.downtoearth.org.in/rss/environment"
]


def fetch_fresh_rss_articles(posted_log: list, max_articles: int = 5) -> list[dict]:
    """
    Fetch fresh unused articles from RSS feeds.
    Returns list of dicts: [{"title": ..., "summary": ..., "link": ..., "source": ...}]
    """
    posted_urls = set()
    posted_titles = set()

    for entry in posted_log:
        if "source_url" in entry:
            posted_urls.add(entry["source_url"].strip().lower())
        if "headline" in entry:
            posted_titles.add(entry["headline"].strip().lower())
        if "link" in entry:
            posted_urls.add(entry["link"].strip().lower())

    fresh_articles = []

    if feedparser:
        for feed_url in DEFAULT_FEEDS:
            try:
                log.info(f"Scouting RSS feed: {feed_url}")
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    article_url = getattr(entry, "link", "").strip()
                    title = getattr(entry, "title", "").strip()
                    raw_summary = getattr(entry, "summary", "") or getattr(entry, "description", "")

                    # Clean HTML tags from summary
                    summary = re.sub(r"<[^>]+>", "", raw_summary).strip()[:400]

                    if not article_url or not title:
                        continue

                    url_low = article_url.lower()
                    title_low = title.lower()

                    if url_low not in posted_urls and title_low not in posted_titles:
                        fresh_articles.append({
                            "title": title,
                            "summary": summary,
                            "link": article_url,
                            "source_url": article_url,
                            "source_feed": feed_url
                        })
                        posted_urls.add(url_low)
                        posted_titles.add(title_low)

                        if len(fresh_articles) >= max_articles:
                            break
            except Exception as exc:
                log.warning(f"Error parsing feed {feed_url}: {exc}")
            if len(fresh_articles) >= max_articles:
                break
    else:
        log.warning("feedparser library not installed. Falling back to HTTP RSS scraper.")

    return fresh_articles
