from __future__ import annotations

from hashlib import sha256
import json
import os
import random
import re
import time

from .config import CTA_OPTIONS, ENVIRONMENT_TOPICS, Settings, settings
from .logger import log_event
from .models import Draft, SourceContext


DRAFT_PROMPT = """\
You are a leading Indian environmental thought-leader and sustainability advocate on LinkedIn.
Write a highly authentic, engaging, and viral LinkedIn post based on the following source material, and extract structured entities.

## Source Material
{sources}

## The Narrative Story Framework
To ensure the post feels human, vulnerable, and engaging, you MUST strictly follow this narrative structure:
1. **A - Attention (The Hook)**: Your first 1-2 lines MUST make people stop scrolling. Use a bold claim, a surprising realization, or an emotional observation (max 150 chars). Do NOT start with generic greetings.
2. **S - Story (The Narrative)**: Frame the news as a personal story or a reflection. DO NOT write a lecture or a list of "takeaways". Write it as an unfolding story. "I remember when...", "It struck me today that...", or "We are living through a moment...". 
3. **P - Personal Connection**: Why does this matter deeply to you and to India? Be vulnerable, passionate, and human. Speak from the "I" or "We" perspective.
4. **C - Conclusion (The CTA)**: End with this exact question to drive comments: "{cta}"

## Requirements & Writing Style
You MUST write the post strictly adhering to the following style guide:
{style_profile}

## Additional Rules
- **No Links**: NEVER include URLs or links in the post text.
- **No Bullet Points/Lists**: Write in short, powerful, narrative paragraphs. No "3 things we must learn" or bulleted takeaways.
- **India Focus**: You MUST explicitly weave India's future, economy, or ecosystems into the story.
- **Data**: Include at least one specific statistic or verifiable fact from the source, woven naturally into the story.
- **NO buzzwords**: Never use: game-changing, revolutionary, disruptive, cutting-edge, unlock, seamless, paradigm shift, synergy, leverage, holistic, delve.
- **Length**: Between 900 and 2800 characters (ensuring at least 140 words).
- **NO emojis in body**: Minimal emoji use (max 2, only at start of lines).

## Entity Extraction
Identify the following specific entities from the source material:
- **technology**: The specific real-world named technology or system mentioned (e.g. "dynamic line rating sensor", "solid state sodium battery"). Never use a generic category like "renewable energy" or "batteries".
- **organization**: The specific company, academic lab, or government agency behind the technology or event (e.g. "Department of Energy", "Reliance Industries").
- **mechanism**: The specific operational, physical, chemical, or thermodynamic mechanism described (e.g. "real-time thermal conductor load monitoring").

## Previous Ideas to AVOID (do NOT repeat these themes)
{avoid_ideas}

You MUST return a valid JSON object matching this structure:
{{
  "post_text": "...",
  "keywords": ["kw1", "kw2", "kw3", "kw4", "kw5"],
  "entities": {{
    "technology": "...",
    "organization": "...",
    "mechanism": "..."
  }}
}}
"""


class CreatorAgent:
    def __init__(self, config: Settings = settings) -> None:
        self.config = config

    def create(
        self,
        contexts: tuple[SourceContext, ...],
        notes: tuple[str, ...] = (),
        avoid_ideas: list[set[str]] | None = None,
    ) -> Draft:
        api_key = self.config.gemini_api_key
        if api_key:
            return self._create_with_gemini(contexts, notes, avoid_ideas or [], api_key)
        return self._create_locally(contexts, notes)

    def _create_with_gemini(
        self,
        contexts: tuple[SourceContext, ...],
        notes: tuple[str, ...],
        avoid_ideas: list[set[str]],
        api_key: str,
    ) -> Draft:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        sources_text = "\n".join(
            f"- Title: {ctx.title}\n  Summary: {ctx.summary}\n  URL: {ctx.url}"
            for ctx in contexts[:5]
        )

        avoid_text = "None yet — this is a fresh start."
        if avoid_ideas:
            avoid_lines = [f"- {', '.join(sorted(kws))}" for kws in avoid_ideas[-10:]]
            avoid_text = "\n".join(avoid_lines)

        if notes:
            sources_text += "\n\n## Revision Notes (fix these issues):\n"
            sources_text += "\n".join(f"- {note}" for note in notes)

        cta = random.choice(CTA_OPTIONS)
        prompt = DRAFT_PROMPT.format(
            sources=sources_text,
            cta=cta,
            avoid_ideas=avoid_text,
            style_profile=self.config.style_profile,
        )

        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                response_text = (response.text or "").strip()
                if not response_text:
                    raise ValueError("Empty response from Gemini")

                res_json = json.loads(response_text)
                draft_text = res_json.get("post_text", "").strip()
                keywords = tuple(str(k).lower().strip() for k in res_json.get("keywords", [])[:5])
                entities = res_json.get("entities", {})
                
                # Fill missing entities with defaults if model failed to extract them
                if "technology" not in entities:
                    entities["technology"] = "sustainability"
                if "organization" not in entities:
                    entities["organization"] = "Environmental Community"
                if "mechanism" not in entities:
                    entities["mechanism"] = "green transitions"

                idea_summary = " ".join(sorted(keywords)[:3]) if keywords else ""
                fingerprint = sha256(draft_text[:200].lower().encode("utf-8")).hexdigest()[:16]

                log_event("creator", "gemini-draft-created", chars=len(draft_text), keywords=list(keywords))

                return Draft(
                    text=draft_text,
                    topic_fingerprint=fingerprint,
                    sources=contexts,
                    image_path="", # delegated to prompt engineer + image agent
                    keywords=keywords,
                    idea_summary=idea_summary,
                    entities=entities,
                )
            except Exception as exc:
                log_event("creator", "gemini-retry", attempt=attempt + 1, error=str(exc)[:200])
                time.sleep(2 ** attempt)

        log_event("creator", "gemini-failed-fallback-local")
        return self._create_locally(contexts, notes)

    def _create_locally(self, contexts: tuple[SourceContext, ...], notes: tuple[str, ...]) -> Draft:
        """Fallback local draft creation when Gemini is unavailable."""
        lead = contexts[0]
        title = _clean_text(lead.title) if lead.title else "Ecology & Sustainability update"
        
        # Compile unique facts from top sources
        facts = []
        for ctx in contexts[:3]:
            fact_sum = _clean_summary(ctx.summary)
            if fact_sum and len(fact_sum) > 40:
                facts.append(fact_sum)
                
        facts_text = " ".join(facts)
        if len(facts_text.split()) < 80:
            facts_text += (
                " Environmental metrics indicate that localized community restoration, "
                "decarbonization initiatives, and resource-recovery loops have a compounding "
                "positive impact on regional ecosystems over time."
            )
            
        text = (
            f"Insight: The recent development around '{title}' marks a significant milestone in Indian ecological planning.\n\n"
            f"Fact-base: {facts_text}\n\n"
            f"From an operational standpoint, implementing sustainable infrastructure and de-risking conservation projects "
            f"requires deep coordination across stakeholders, local communities, and regulatory bodies. The long-term recovery "
            f"of our regional ecosystems is directly tied to how proactively we deploy these technological and community models.\n\n"
            f"Which aspect of this ecological solution do you think is the most challenging to scale? Share your perspective in the comments below.\n\n"
            f"#India #Sustainability #Environment #Nature"
        )

        keywords = _extract_keywords_locally(text)
        fingerprint = sha256(title.lower().encode("utf-8")).hexdigest()[:16]
        
        entities = {
            "technology": keywords[0] if len(keywords) > 0 else "conservation",
            "organization": "Local Community",
            "mechanism": "community action"
        }

        return Draft(
            text=text,
            topic_fingerprint=fingerprint,
            sources=contexts,
            image_path="", # delegated to prompt engineer + image agent
            keywords=keywords,
            idea_summary=" ".join(sorted(keywords)[:3]),
            entities=entities,
        )


def _clean_text(text: str) -> str:
    import html
    import unicodedata
    # Unescape HTML entities
    text = html.unescape(text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Normalize unicode (fixes non-breaking spaces, weird quotes)
    text = unicodedata.normalize('NFKC', text)
    text = text.replace('\xa0', ' ').replace('\u2019', "'").replace('\u2018', "'").replace('\u201c', '"').replace('\u201d', '"').replace('\u2014', '-').replace('\u2013', '-')
    # Replace multiple spaces/newlines with a single space
    return " ".join(text.replace("\n", " ").split())


def _clean_summary(summary: str) -> str:
    return _clean_text(summary)[:600]


def _has_number(text: str) -> bool:
    return bool(re.search(r"\d", text))


def _extract_keywords_locally(text: str) -> tuple[str, ...]:
    """Simple keyword extraction based on environment topic matching."""
    lowered = text.lower()
    matched = [topic for topic in ENVIRONMENT_TOPICS if topic in lowered]
    if len(matched) >= 3:
        return tuple(matched[:5])
    # Fallback: extract significant words
    words = re.findall(r"\b[a-z]{4,}\b", lowered)
    stop_words = {"that", "this", "with", "from", "have", "been", "their", "would", "could", "should",
                  "about", "which", "when", "what", "where", "than", "then", "into", "just", "also",
                  "more", "most", "some", "each", "every", "will", "your", "they", "them", "these"}
    meaningful = [w for w in words if w not in stop_words]
    # Get unique words by frequency
    freq: dict[str, int] = {}
    for w in meaningful:
        freq[w] = freq.get(w, 0) + 1
    top = sorted(freq, key=lambda x: freq[x], reverse=True)[:5]
    return tuple(top)
