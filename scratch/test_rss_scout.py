import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))

from rss_scout import fetch_fresh_rss_articles

articles = fetch_fresh_rss_articles([])
print(f"Fetched {len(articles)} fresh RSS items:")
for i, a in enumerate(articles, 1):
    print(f"{i}. [{a['source_feed']}] {a['title']}")
    print(f"   URL: {a['link']}")
    print(f"   Summary: {a['summary'][:150]}...\n")
