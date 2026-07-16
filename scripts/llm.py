"""
Shared LLM helper for all EcoPulse agents.
Supports both Anthropic Claude (via SDK) and Google Gemini (via REST API).
Requires ANTHROPIC_API_KEY or GEMINI_API_KEY in the environment.
"""
import os
import json
import re
import requests

# Load env variables from local .env if running locally
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k.strip()] = v.strip()

MODEL = os.environ.get("ECOPULSE_MODEL")


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
        model_name = MODEL or "gemini-3.1-flash-lite"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
        
        contents = [
            {
                "role": "user",
                "parts": [{"text": user_content}]
            }
        ]
        
        for attempt in range(max_retries + 1):
            payload = {
                "contents": contents,
                "systemInstruction": {
                    "parts": [{"text": system_prompt}]
                },
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": 0.7 + (attempt * 0.1),
                    "frequencyPenalty": 0.75,
                    "presencePenalty": 0.4,
                    "thinkingConfig": {
                        "thinkingBudget": 0
                    }
                }
            }
            
            if use_web_search and attempt == 0:
                payload["tools"] = [{"googleSearch": {}}]
            else:
                payload["generationConfig"]["responseMimeType"] = "application/json"

            try:
                resp = requests.post(url, json=payload, timeout=60)
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
                if "frequencyPenalty" in payload.get("generationConfig", {}):
                    del payload["generationConfig"]["frequencyPenalty"]
                    del payload["generationConfig"]["presencePenalty"]
                    try:
                        resp = requests.post(url, json=payload, timeout=60)
                        resp.raise_for_status()
                        res_data = resp.json()
                        candidate = res_data["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            text = candidate["content"]["parts"][0]["text"]
                            return _extract_json(text)
                    except Exception as retry_err:
                        e = retry_err
                # Catch rate limits (429) and temporary server overloads (502, 503, 504) and sleep before retrying
                is_retryable = False
                if isinstance(e, requests.exceptions.HTTPError):
                    if e.response.status_code in (429, 502, 503, 504):
                        is_retryable = True
                elif any(err in str(e) for err in ("429", "502", "503", "504")):
                    is_retryable = True

                if is_retryable and attempt < max_retries:
                    import time
                    time.sleep(15 * (attempt + 1))
                    continue

                if attempt < max_retries:
                    # Append model's response and retry instructions
                    model_text = ""
                    try:
                        model_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                    except Exception:
                        model_text = "Empty or failed response"
                    
                    contents.append({
                        "role": "model",
                        "parts": [{"text": model_text}]
                    })
                    contents.append({
                        "role": "user",
                        "parts": [{
                            "text": f"That was not valid JSON ({e}). Output ONLY the corrected, clean JSON object. "
                                    "Ensure all double quotes inside string values are properly escaped (e.g. \\\"quote\\\")."
                        }]
                    })
                    continue
                raise RuntimeError(f"Gemini API failed: {e}")
    else:
        raise ValueError("Neither ANTHROPIC_API_KEY nor GEMINI_API_KEY found in the environment.")
