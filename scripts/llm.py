"""
Shared LLM helper for all EcoPulse agents.
Supports both Anthropic Claude (via SDK) and Google Gemini (via REST API).
Requires ANTHROPIC_API_KEY or GEMINI_API_KEY in the environment.
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

# ── Global pacing: track the last API call time to enforce minimum gap ──
_last_api_call_time = 0.0
_MIN_GAP_SECONDS = 10  # Minimum gap between consecutive API calls


def _pace():
    """Enforce a minimum gap between consecutive API calls to avoid rate-limit storms."""
    global _last_api_call_time
    now = time.time()
    elapsed = now - _last_api_call_time
    if elapsed < _MIN_GAP_SECONDS:
        wait = _MIN_GAP_SECONDS - elapsed + random.uniform(0, 2)
        log.info(f"Pacing: waiting {wait:.1f}s before next API call...")
        time.sleep(wait)
    _last_api_call_time = time.time()


def _extract_json(text: str) -> dict:
    """Strip markdown code fences / stray prose and parse the first JSON object."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\n?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n?```$", "", text)
    text = text.strip()

    # Extract only the balanced/outermost JSON block to ignore stray prose
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        text = match.group(1)

    return json.loads(text)


def call_agent(system_prompt: str, user_content: str, use_web_search: bool = False,
                max_tokens: int = 4000, max_retries: int = 2) -> dict:
    """
    Call Claude (via SDK) or Gemini (via REST) depending on available API keys.
    Returns parsed JSON dict.
    """
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")

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
                frequency_penalty=0.75,
                presence_penalty=0.4,
            )
            if tools:
                kwargs["tools"] = tools
            try:
                response = client.messages.create(**kwargs)
                text_parts = [block.text for block in response.content if block.type == "text"]
                full_text = "\n".join(text_parts)
                return _extract_json(full_text)
            except Exception as e:
                if "frequency_penalty" in kwargs:
                    del kwargs["frequency_penalty"]
                    del kwargs["presence_penalty"]
                    try:
                        response = client.messages.create(**kwargs)
                        text_parts = [block.text for block in response.content if block.type == "text"]
                        full_text = "\n".join(text_parts)
                        return _extract_json(full_text)
                    except Exception as retry_err:
                        e = retry_err
                if attempt < max_retries:
                    messages.append({"role": "assistant", "content": full_text if 'full_text' in locals() else str(e)})
                    messages.append({
                        "role": "user",
                        "content": f"That was not valid JSON ({e}). Return ONLY the corrected "
                                    f"JSON object, nothing else — no prose, no code fences."
                    })
                    continue
                raise RuntimeError(f"Claude API failed after retries: {e}")

    elif gemini_key:
        # Use a single model — gemini-2.0-flash and 2.5-flash share the same
        # rate-limit quota, so model fallback doesn't help with 429s.
        # Instead, retry aggressively with exponential backoff.
        model_name = MODEL or "gemini-2.0-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
        max_attempts = 5

        last_error = None
        for attempt in range(max_attempts):
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
                resp = requests.post(url, json=payload, timeout=90)

                if resp.status_code == 429:
                    # Linear backoff: 30s, 60s, 90s, 120s, 150s — enough to
                    # clear the per-minute rate window on each retry.
                    wait_time = 30 * (attempt + 1) + random.uniform(5, 15)
                    log.warning(f"429 rate limit on {model_name} (attempt {attempt+1}/{max_attempts}). "
                                f"Waiting {wait_time:.0f}s...")
                    time.sleep(wait_time)
                    last_error = RuntimeError(f"429 rate limit on {model_name}")
                    continue  # Try the next attempt

                resp.raise_for_status()
                res_data = resp.json()

                candidate = res_data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    text = candidate["content"]["parts"][0]["text"]
                    return _extract_json(text)
                else:
                    reason = candidate.get("finishReason", "UNKNOWN")
                    raise KeyError(f"No content found (Finish Reason: {reason})")

            except requests.exceptions.HTTPError as e:
                last_error = e
                log.warning(f"Gemini API attempt {attempt+1}/{max_attempts} on {model_name} failed: {e}")
                time.sleep(10 + random.uniform(0, 5))
            except json.JSONDecodeError as e:
                last_error = e
                log.warning(f"JSON parse error on {model_name} (attempt {attempt+1}/{max_attempts}): {e}")
                time.sleep(5)
            except Exception as e:
                last_error = e
                log.warning(f"Gemini API attempt {attempt+1}/{max_attempts} on {model_name} failed: {e}")
                time.sleep(10 + random.uniform(0, 5))

        raise RuntimeError(f"Gemini API failed after {max_attempts} attempts: {last_error}")

    else:
        raise ValueError("Neither ANTHROPIC_API_KEY nor GEMINI_API_KEY found in the environment.")
