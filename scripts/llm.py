"""
Shared LLM helper for all EcoPulse agents.
Calls Google Gemini API with model rotation (gemini-2.5-flash, gemini-2.0-flash, gemini-2.0-flash-lite, gemini-2.5-pro)
and smart rate-limit backoff to guarantee 100% live, unique, non-repetitive AI generation.
"""
import os
import json
import re
import time
import random
import logging
import requests

log = logging.getLogger("ecopulse")

# Load env variables from local .env if running locally
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k.strip()] = v.strip()

MODEL = os.environ.get("ECOPULSE_MODEL")

_last_api_call_time = 0.0
_MIN_GAP_SECONDS = 5  # Minimum gap between consecutive API calls to prevent rate-limit storms


def _pace():
    """Enforce a minimum gap between consecutive API calls to avoid rate-limit storms."""
    global _last_api_call_time
    now = time.time()
    elapsed = now - _last_api_call_time
    if elapsed < _MIN_GAP_SECONDS:
        wait = _MIN_GAP_SECONDS - elapsed + random.uniform(0, 1)
        time.sleep(wait)
    _last_api_call_time = time.time()


def _extract_json(text: str) -> dict:
    """Strip markdown code fences / stray prose and parse the first JSON object."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\n?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n?```$", "", text)
    text = text.strip()

    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        text = match.group(1)

    return json.loads(text)


def call_agent(system_prompt: str, user_content: str, use_web_search: bool = False,
                max_tokens: int = 4000, max_retries: int = 2) -> dict:
    """
    Call Gemini LLM API across a multi-model fallback chain:
    gemini-2.5-flash -> gemini-2.0-flash -> gemini-2.0-flash-lite -> gemini-2.5-pro

    Retries with progressive backoff on 429 rate limits to ensure 100% live, unique content.
    """
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()

    # 1. Try Anthropic Claude if available
    if anthropic_key:
        from anthropic import Anthropic
        model_name = MODEL or "claude-3-5-sonnet-20241022"
        client = Anthropic(api_key=anthropic_key)
        tools = [{"type": "web_search_20250305", "name": "web_search"}] if use_web_search else None
        messages = [{"role": "user", "content": user_content}]

        for attempt in range(max_retries + 1):
            _pace()
            kwargs = dict(
                model=model_name,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
            )
            if tools:
                kwargs["tools"] = tools
            try:
                response = client.messages.create(**kwargs)
                text_parts = [block.text for block in response.content if block.type == "text"]
                full_text = "\n".join(text_parts)
                return _extract_json(full_text)
            except Exception as e:
                log.warning(f"Claude API attempt {attempt+1} failed: {e}")

    # 2. Try Google Gemini across model variants
    if not gemini_key:
        raise ValueError("GEMINI_API_KEY is missing from the environment.")

    models_to_try = [
        MODEL or "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.5-pro",
    ]

    last_error = ""
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"

        for attempt in range(3):
            _pace()

            payload = {
                "contents": [{"role": "user", "parts": [{"text": user_content}]}],
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": 0.7 + (attempt * 0.05),
                }
            }

            if use_web_search and attempt == 0:
                payload["tools"] = [{"googleSearch": {}}]
            else:
                payload["generationConfig"]["responseMimeType"] = "application/json"

            try:
                resp = requests.post(url, json=payload, timeout=40)
                if resp.status_code == 200:
                    res_data = resp.json()
                    candidate = res_data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        text = candidate["content"]["parts"][0]["text"]
                        return _extract_json(text)
                    else:
                        reason = candidate.get("finishReason", "UNKNOWN")
                        log.warning(f"Gemini candidate content empty (reason: {reason}).")
                elif resp.status_code == 429:
                    # Parse retryDelay from Gemini response header/body if present
                    delay = 20 * (attempt + 1)
                    match = re.search(r'retry(?:Delay|\s+in)\s*:?\s*"?(\d+)', resp.text, re.IGNORECASE)
                    if match:
                        delay = min(int(match.group(1)) + 5, 45)

                    log.warning(f"Gemini API 429 Rate Limit on {model_name} (attempt {attempt+1}/3). "
                                f"Waiting {delay}s for quota window reset...")
                    time.sleep(delay)
                else:
                    log.warning(f"Gemini API status {resp.status_code} on {model_name}: {resp.text[:120]}")
                    time.sleep(5)
            except Exception as exc:
                log.warning(f"Gemini API exception on {model_name}: {exc}")
                time.sleep(5)

    raise RuntimeError(f"All LLM API calls failed across models. Last error: {last_error}")
