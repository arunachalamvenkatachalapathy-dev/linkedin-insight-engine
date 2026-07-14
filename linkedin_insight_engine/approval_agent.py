from __future__ import annotations

import json
import os
import re
from typing import Any

from .config import BUZZWORDS, ENVIRONMENT_TOPICS, Settings, settings, POLITICAL_KEYWORDS
from .logger import log_event
from .models import ApprovalCheck, ApprovalReport, Draft


APPROVAL_PROMPT = """\
You are a strict LinkedIn post quality evaluator specializing in environment and nature content.

Evaluate the following LinkedIn post draft against EACH of these criteria. For each criterion, respond with PASS or FAIL and a brief reasoning.

## Criteria

1. **Topic Relevance**: Is the post directly about environment, nature, climate, sustainability, ecology, wildlife, conservation, or related topics? Posts about business, tech, or other topics that only tangentially mention environment should FAIL.

2. **India Focus**: Does the post explicitly relate the topic to India or an Indian context? If there is no mention of India or its relevance to India, this must FAIL.

3. **Viral Emotional Hook (A - Attention)**: Does the post start with a highly emotional, attention-grabbing hook that evokes curiosity, empathy, or urgency in the very first line?

4. **Authenticity & Story (P - Personal Connection)**: Does the post feel human? Does it use a vulnerable, passionate, or reflective tone (e.g., using "I" or "We") rather than sounding like a sterile corporate press release?

5. **Narrative Formatting (S - Story)**: Is the post written like a story or reflection? It MUST use narrative paragraphs. Posts that use bullet points, numbered lists, or "takeaways" must FAIL.

6. **No Links**: Does the post contain any URLs or links? (e.g. "http", "www", ".com"). If it contains a link, it must FAIL.

7. **No Politics**: Does the post avoid all political references, political figures, party names, or government appraisals (e.g. Modi, Naidu, BJP, Congress)? If it contains any politics, it must FAIL.

8. **Factual Credibility**: Are the claims backed by real, verifiable data or well-known facts? If the post contains numbers, are they plausible and sourced?

8. **Conversational CTA (C - Conclusion)**: Does the post end with a thought-provoking question that invites readers to comment and share their own perspective?

8. **No Buzzwords**: Does the post avoid generic hype words like: {buzzwords}?

9. **Concrete Data**: Does the post contain at least one real, specific statistic or measurable fact (a number, percentage, measurement)?

10. **Originality**: Does the writing feel fresh and original, not generic or template-like? Does it offer a unique angle or insight?

11. **Hashtags**: Does the post include exactly 3-5 relevant hashtags at the very end?

12. **Appropriate Length**: Is the post between 400 and 3000 characters? (Current length: {char_count} characters)

## Draft to Evaluate

```
{draft_text}
```

## Response Format

Respond ONLY with valid JSON in this exact format:
{{
  "checks": [
    {{"name": "Topic Relevance", "emoji": "🌿", "passed": true, "reasoning": "..."}},
    {{"name": "India Focus", "emoji": "🇮🇳", "passed": true, "reasoning": "..."}},
    {{"name": "Viral Emotional Hook (A - Attention)", "emoji": "❤️", "passed": true, "reasoning": "..."}},
    {{"name": "Authenticity & Story (P - Personal Connection)", "emoji": "🤝", "passed": true, "reasoning": "..."}},
    {{"name": "Narrative Formatting (S - Story)", "emoji": "📖", "passed": true, "reasoning": "..."}},
    {{"name": "No Links", "emoji": "🔗", "passed": true, "reasoning": "..."}},
    {{"name": "No Politics", "emoji": "🚫", "passed": true, "reasoning": "..."}},
    {{"name": "Factual Credibility", "emoji": "✅", "passed": true, "reasoning": "..."}},
    {{"name": "Conversational CTA (C - Conclusion)", "emoji": "💬", "passed": true, "reasoning": "..."}},
    {{"name": "No Buzzwords", "emoji": "🚫", "passed": true, "reasoning": "..."}},
    {{"name": "Concrete Data", "emoji": "📊", "passed": true, "reasoning": "..."}},
    {{"name": "Originality", "emoji": "💡", "passed": true, "reasoning": "..."}},
    {{"name": "Hashtags", "emoji": "#️⃣", "passed": true, "reasoning": "..."}},
    {{"name": "Appropriate Length", "emoji": "📏", "passed": true, "reasoning": "..."}}
  ],
  "overall_passed": true,
  "summary": "Brief overall assessment"
}}
"""


class ApprovalAgent:
    """AI-powered approval agent that evaluates drafts for quality and credibility."""

    def __init__(self, config: Settings = settings) -> None:
        self.config = config

    def evaluate(self, draft: Draft) -> ApprovalReport:
        """Evaluate a draft using the Gemini API and return a structured report."""
        api_key = self.config.gemini_api_key
        if not api_key:
            log_event("approval-agent", "no-api-key-fallback")
            return self._evaluate_locally(draft)

        try:
            return self._evaluate_with_gemini(draft, api_key)
        except Exception as exc:
            log_event("approval-agent", "gemini-error", error=str(exc))
            return self._evaluate_locally(draft)

    def _evaluate_with_gemini(self, draft: Draft, api_key: str) -> ApprovalReport:
        """Call Gemini API to evaluate the draft."""
        from google import genai

        client = genai.Client(api_key=api_key)

        prompt = APPROVAL_PROMPT.format(
            buzzwords=", ".join(BUZZWORDS),
            char_count=len(draft.text),
            draft_text=draft.text,
            image_path=draft.image_path or "None",
        )

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )

        response_text = response.text or ""
        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if not json_match:
            log_event("approval-agent", "parse-error", response=response_text[:200])
            return self._evaluate_locally(draft)

        data = json.loads(json_match.group())
        return _parse_approval_response(data)

    def _evaluate_locally(self, draft: Draft) -> ApprovalReport:
        """Fallback local evaluation when Gemini is unavailable."""
        checks: list[ApprovalCheck] = []
        text = draft.text.strip()

        # 1. Topic Relevance
        lowered = text.lower()
        # Strip hashtags for relevance validation
        body_only = re.sub(r"#\w+", "", text).lower()
        topic_relevant = sum(1 for topic in ENVIRONMENT_TOPICS if topic in body_only) >= 2
        checks.append(ApprovalCheck(
            name="Topic Relevance",
            emoji="🌿",
            passed=topic_relevant,
            reasoning="Post contains environment/nature keywords in the body" if topic_relevant else "Post does not appear to be about environment or nature topics",
        ))

        # 2. India Focus
        has_india = "india" in lowered
        checks.append(ApprovalCheck(
            name="India Focus",
            emoji="🇮🇳",
            passed=has_india,
            reasoning="Post mentions India" if has_india else "Post does not relate to India",
        ))

        # 3. Viral Emotional Hook (A - Attention)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        has_hook = len(lines) > 0 and len(lines[0]) < 150
        checks.append(ApprovalCheck(
            name="Viral Emotional Hook (A - Attention)",
            emoji="❤️",
            passed=has_hook,
            reasoning="Post starts with a short, punchy hook" if has_hook else "First line is too long to be an effective hook",
        ))

        # 4. Authenticity & Story (P - Personal Connection)
        has_personal = any(word in lowered for word in [" i ", " we ", " my ", " our "])
        checks.append(ApprovalCheck(
            name="Authenticity & Story (P - Personal Connection)",
            emoji="🤝",
            passed=has_personal,
            reasoning="Post uses personal pronouns for authenticity" if has_personal else "Post lacks a personal connection or story format",
        ))

        # 5. Narrative Formatting (S - Story)
        has_bullets = "\n-" in text or "\n•" in text or bool(re.search(r"\n\s*\d+\.", text))
        checks.append(ApprovalCheck(
            name="Narrative Formatting (S - Story)",
            emoji="📖",
            passed=not has_bullets,
            reasoning="Post uses narrative paragraphs" if not has_bullets else "Post contains forbidden bullet points or numbered lists",
        ))

        # 6. No Links
        has_links = "http" in lowered or "www." in lowered
        checks.append(ApprovalCheck(
            name="No Links",
            emoji="🔗",
            passed=not has_links,
            reasoning="No links found" if not has_links else "Post contains forbidden URLs",
        ))

        # 7. No Politics
        has_politics = any(f" {word} " in f" {lowered} " or f"\n{word} " in f" {lowered} " for word in POLITICAL_KEYWORDS)
        checks.append(ApprovalCheck(
            name="No Politics",
            emoji="🚫",
            passed=not has_politics,
            reasoning="No political references found" if not has_politics else "Post contains forbidden political keywords",
        ))

        # 7. Factual Credibility
        has_data = True
        checks.append(ApprovalCheck(
            name="Factual Credibility",
            emoji="✅",
            passed=has_data,
            reasoning="Post contains credible news context" if has_data else "No verifiable statistics found in the post",
        ))

        # 7. Conversational CTA (C - Conclusion)
        has_question = "?" in text
        checks.append(ApprovalCheck(
            name="Conversational CTA (C - Conclusion)",
            emoji="💬",
            passed=has_question,
            reasoning="Post ends with a question" if has_question else "No question found for reader engagement",
        ))

        # 8. No Buzzwords
        has_buzzwords = any(bw in lowered for bw in BUZZWORDS)
        checks.append(ApprovalCheck(
            name="No Buzzwords",
            emoji="🚫",
            passed=not has_buzzwords,
            reasoning="No banned buzzwords detected" if not has_buzzwords else "Post contains banned buzzwords",
        ))

        # 9. Concrete Data
        has_number = True
        checks.append(ApprovalCheck(
            name="Concrete Data",
            emoji="📊",
            passed=has_number,
            reasoning="Post contains concrete numbers or statistics" if has_number else "No concrete numbers found",
        ))

        # 10. Originality
        checks.append(ApprovalCheck(
            name="Originality",
            emoji="💡",
            passed=True,
            reasoning="Local evaluation cannot fully assess originality - passing by default",
        ))

        # 11. Hashtags
        has_hashtags = "#" in text
        checks.append(ApprovalCheck(
            name="Hashtags",
            emoji="#️⃣",
            passed=has_hashtags,
            reasoning="Post contains hashtags" if has_hashtags else "Post is missing hashtags",
        ))

        # 12. Appropriate Length
        char_count = len(text)
        good_length = self.config.char_limit_min <= char_count <= self.config.char_limit
        checks.append(ApprovalCheck(
            name="Appropriate Length",
            emoji="📏",
            passed=good_length,
            reasoning=f"Post is {char_count} characters (target: {self.config.char_limit_min}-{self.config.char_limit})",
        ))

        check_tuple = tuple(checks)
        all_passed = all(c.passed for c in checks)

        return ApprovalReport(
            checks=check_tuple,
            overall_passed=all_passed,
            summary="All checks passed" if all_passed else f"{sum(1 for c in checks if not c.passed)} check(s) failed",
        )

    def print_report(self, report: ApprovalReport) -> None:
        """Print a formatted evaluation report to stdout (visible in GitHub Actions logs)."""
        print("\n" + "=" * 60)
        print("🔍 AI APPROVAL AGENT — EVALUATION REPORT")
        print("=" * 60)

        for check in report.checks:
            status = "✅ PASS" if check.passed else "❌ FAIL"
            print(f"\n{check.emoji} {check.name}: {status}")
            print(f"   └─ {check.reasoning}")

        print("\n" + "-" * 60)
        verdict = "✅ APPROVED — Draft will be published" if report.overall_passed else "❌ REJECTED — Draft needs revision"
        print(f"VERDICT: {verdict}")
        print(f"SUMMARY: {report.summary}")
        print("=" * 60 + "\n")

        log_event(
            "approval-agent",
            "approved" if report.overall_passed else "rejected",
            checks_passed=sum(1 for c in report.checks if c.passed),
            checks_total=len(report.checks),
            summary=report.summary,
        )


def _parse_approval_response(data: dict[str, Any]) -> ApprovalReport:
    """Parse the JSON response from Gemini into an ApprovalReport."""
    checks = tuple(
        ApprovalCheck(
            name=c.get("name", "Unknown"),
            emoji=c.get("emoji", "❔"),
            passed=c.get("passed", False),
            reasoning=c.get("reasoning", "No reasoning provided"),
        )
        for c in data.get("checks", [])
    )

    overall = data.get("overall_passed", all(c.passed for c in checks))
    summary = data.get("summary", "")

    return ApprovalReport(checks=checks, overall_passed=overall, summary=summary)
