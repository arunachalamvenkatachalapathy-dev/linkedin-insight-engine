"""
Shared LLM helper for all EcoPulse agents.
Supports Anthropic Claude, Google Gemini, and OpenAI GPT as engines.
Falls back through providers automatically on rate limits or failures.
Requires at least one of: ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY.
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
_MIN_GAP_SECONDS = 8  # Minimum gap between consecutive API calls


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


# ──────────────────────────────────────────────────
# Provider: OpenAI GPT (via REST API)
# ──────────────────────────────────────────────────
def _call_openai(system_prompt: str, user_content: str, max_tokens: int = 4000) -> dict:
    """Call OpenAI GPT-4o-mini via REST API. Returns parsed JSON dict."""
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not openai_key:
        raise ValueError("OPENAI_API_KEY not available")

    model_name = "gpt-4o-mini"
    url = "https://api.openai.com/v1/chat/completions"

    for attempt in range(3):
        _pace()
        try:
            resp = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                    "response_format": {"type": "json_object"}
                },
                timeout=90
            )

            if resp.status_code == 429:
                wait = 30 * (attempt + 1) + random.uniform(5, 10)
                log.warning(f"OpenAI 429 rate limit (attempt {attempt+1}/3). Waiting {wait:.0f}s...")
                time.sleep(wait)
                continue

            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return _extract_json(text)

        except Exception as e:
            log.warning(f"OpenAI attempt {attempt+1}/3 failed: {e}")
            if attempt < 2:
                time.sleep(5 + random.uniform(0, 5))
            else:
                raise RuntimeError(f"OpenAI API failed after 3 attempts: {e}")

    raise RuntimeError("OpenAI API failed after all attempts")


# ──────────────────────────────────────────────────
# Provider: Google Gemini (via REST API)
# ──────────────────────────────────────────────────
def _call_gemini(system_prompt: str, user_content: str, max_tokens: int = 4000,
                 use_web_search: bool = False) -> dict:
    """Call Gemini via REST API. Returns parsed JSON dict. Raises on persistent 429."""
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not gemini_key:
        raise ValueError("GEMINI_API_KEY not available")

    model_name = MODEL or "gemini-2.0-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
    # Only retry twice on 429 — then bail to fallback provider
    max_attempts = 3

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
                wait_time = 30 * (attempt + 1) + random.uniform(5, 15)
                log.warning(f"Gemini 429 rate limit (attempt {attempt+1}/{max_attempts}). "
                            f"Waiting {wait_time:.0f}s...")
                time.sleep(wait_time)
                continue  # Try again

            resp.raise_for_status()
            res_data = resp.json()

            candidate = res_data["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                text = candidate["content"]["parts"][0]["text"]
                return _extract_json(text)
            else:
                reason = candidate.get("finishReason", "UNKNOWN")
                raise KeyError(f"No content found (Finish Reason: {reason})")

        except Exception as e:
            if "429" in str(e) or resp.status_code == 429 if 'resp' in dir() else False:
                log.warning(f"Gemini 429 on attempt {attempt+1}/{max_attempts}")
            else:
                log.warning(f"Gemini attempt {attempt+1}/{max_attempts} failed: {e}")
            if attempt < max_attempts - 1:
                time.sleep(5 + random.uniform(0, 5))
            else:
                raise RuntimeError(f"Gemini API failed after {max_attempts} attempts: {e}")

    raise RuntimeError(f"Gemini API exhausted all {max_attempts} attempts (persistent 429)")


# ──────────────────────────────────────────────────
# Provider: Anthropic Claude (via SDK)
# ──────────────────────────────────────────────────
def _call_anthropic(system_prompt: str, user_content: str, max_tokens: int = 4000,
                    use_web_search: bool = False, max_retries: int = 2) -> dict:
    """Call Claude via Anthropic SDK. Returns parsed JSON dict."""
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not anthropic_key:
        raise ValueError("ANTHROPIC_API_KEY not available")

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
            if attempt < max_retries:
                messages.append({"role": "assistant", "content": full_text if 'full_text' in locals() else str(e)})
                messages.append({
                    "role": "user",
                    "content": f"That was not valid JSON ({e}). Return ONLY the corrected "
                                f"JSON object, nothing else — no prose, no code fences."
                })
                continue
            raise RuntimeError(f"Claude API failed after retries: {e}")

    raise RuntimeError("Claude API failed after all retries")


# ──────────────────────────────────────────────────
# Main entry point: cascading provider fallback
# ──────────────────────────────────────────────────
def call_agent(system_prompt: str, user_content: str, use_web_search: bool = False,
                max_tokens: int = 4000, max_retries: int = 2) -> dict:
    """
    Call the best available LLM provider, falling back through:
    Anthropic Claude → Google Gemini → OpenAI GPT-4o-mini

    Returns parsed JSON dict.
    """
    errors = []

    # 1. Try Anthropic Claude first (if key is set)
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if anthropic_key:
        try:
            log.info("Using Anthropic Claude...")
            return _call_anthropic(system_prompt, user_content, max_tokens, use_web_search, max_retries)
        except Exception as e:
            log.warning(f"Anthropic Claude failed: {e}")
            errors.append(f"Claude: {e}")

    # 2. Try Google Gemini (if key is set)
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if gemini_key:
        try:
            log.info("Using Google Gemini...")
            return _call_gemini(system_prompt, user_content, max_tokens, use_web_search)
        except Exception as e:
            log.warning(f"Google Gemini failed: {e}. Falling back to OpenAI...")
            errors.append(f"Gemini: {e}")

    # 3. Fallback to OpenAI GPT-4o-mini (if key is set)
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if openai_key:
        try:
            log.info("Using OpenAI GPT-4o-mini fallback...")
            return _call_openai(system_prompt, user_content, max_tokens)
        except Exception as e:
            log.warning(f"OpenAI GPT-4o-mini failed: {e}")
            errors.append(f"OpenAI: {e}")

    # All providers failed
    raise RuntimeError(f"All LLM providers failed: {'; '.join(errors) or 'No API keys found'}")
