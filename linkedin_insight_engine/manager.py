from __future__ import annotations

import random
import urllib.parse
from urllib.request import urlopen
from xml.etree import ElementTree

from .config import DEFAULT_NICHE_TOPICS, Settings, settings
from .logger import log_event
from .models import SourceContext
from .state_store import StateStore


BRAINSTORM_PROMPT = """\
Brainstorm exactly one specific, trending, niche topic (2-4 words) relating to environment, nature, sustainability, or green tech in India.
It MUST be highly specific (e.g. "Miyawaki urban forestry", "solar powered irrigation", "seaweed biofuel", not just "sustainability").
It MUST NOT repeat or overlap with any of these recently used keywords:
{avoid_keywords}

Return ONLY the topic as a clean string. Do not include quotes, markdown, or any explanation.
"""


def fetch_context(
    store: StateStore | None = None,
    config: Settings = settings,
    timeout_seconds: int = 8,
) -> tuple[SourceContext, ...]:
    # 1. Determine the niche topic
    avoid_words = []
    if store:
        recent_kws = store.get_recent_keywords(config.duplicate_window_days)
        avoid_words = [kw for kws in recent_kws for kw in kws]
    
    niche_topic = None
    api_key = config.gemini_api_key
    if api_key:
        try:
            # We use gemini-2.5-flash as default, or fallback
            from google import genai
            client = genai.Client(api_key=api_key)
            avoid_text = ", ".join(set(avoid_words)) if avoid_words else "None"
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=BRAINSTORM_PROMPT.format(avoid_keywords=avoid_text),
            )
            niche_topic = (response.text or "").strip().strip('"').strip("'").strip("`")
            log_event("manager", "brainstorm-topic-success", topic=niche_topic)
        except Exception as exc:
            log_event("manager", "brainstorm-topic-failed", error=str(exc))
            
    if not niche_topic:
        # Fallback locally
        choices = list(DEFAULT_NICHE_TOPICS)
        random.shuffle(choices)
        for choice in choices:
            choice_words = set(choice.lower().split())
            if not (choice_words & set(avoid_words)):
                niche_topic = choice
                break
        if not niche_topic:
            niche_topic = random.choice(DEFAULT_NICHE_TOPICS)
        log_event("manager", "fallback-local-topic", topic=niche_topic)

    # 2. Build RSS query URL for this dynamic topic
    query = f"{niche_topic} india"
    encoded_query = urllib.parse.quote(query)
    source_url = f"https://news.google.com/rss/search?q={encoded_query}+when:7d&hl=en-IN&gl=IN&ceid=IN:en"
    
    contexts: list[SourceContext] = []
    try:
        contexts.extend(_read_rss(source_url, timeout_seconds))
        log_event("manager", "source-read", source=source_url, topic=niche_topic)
    except Exception as exc:
        log_event("manager", "source-failed", source=source_url, error=type(exc).__name__)

    # Fallback to general environment news if the niche query returned nothing
    if not contexts:
        log_event("manager", "niche-returned-no-results-falling-back")
        for source_url in config.rss_sources:
            try:
                contexts.extend(_read_rss(source_url, timeout_seconds))
            except Exception:
                pass

    if contexts:
        return tuple(contexts[:8])

    return (
        SourceContext(
            title=f"The Rise of {niche_topic}",
            summary=f"Developing sustainable solutions in {niche_topic} is becoming critical for India. Focus on practical impacts, green policies, and local action.",
        ),
    )


def _read_rss(source_url: str, timeout_seconds: int) -> list[SourceContext]:
    with urlopen(source_url, timeout=timeout_seconds) as response:
        body = response.read()

    root = ElementTree.fromstring(body)
    items = root.findall(".//item")[:5]
    contexts: list[SourceContext] = []
    for item in items:
        title = item.findtext("title", default="").strip()
        summary = item.findtext("description", default="").strip()
        link = item.findtext("link", default="").strip()
        if title or summary:
            contexts.append(SourceContext(title=title, summary=summary, url=link))
    return contexts
