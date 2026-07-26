"""
Publisher agent — posts the final text + image to LinkedIn using the LinkedIn
Posts API (versioned REST API, the current recommended approach as of 2026).

Required environment variables (set as GitHub Actions secrets):
  LINKEDIN_ACCESS_TOKEN  - OAuth2 token with the w_member_social scope
  LINKEDIN_PERSON_URN    - e.g. "urn:li:person:XXXXXXXX" (your member URN)
"""
import os
import logging
import requests

log = logging.getLogger("ecopulse")

API_BASE = "https://api.linkedin.com"
LI_VERSION = "202606"  # Confirmed working version for this account


def _headers(extra: dict = None) -> dict:
    h = {
        "Authorization": f"Bearer {os.environ['LINKEDIN_ACCESS_TOKEN']}",
        "LinkedIn-Version": LI_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }
    if extra:
        h.update(extra)
    return h


def _upload_image(image_path: str, author_urn: str) -> str:
    log.info(f"Uploading image: {image_path} (size: {os.path.getsize(image_path)} bytes)")
    init_resp = requests.post(
        f"{API_BASE}/rest/images?action=initializeUpload",
        headers=_headers({"Content-Type": "application/json"}),
        json={"initializeUploadRequest": {"owner": author_urn}},
        timeout=60,
    )
    log.info(f"Image init response: {init_resp.status_code}")
    init_resp.raise_for_status()
    data = init_resp.json()["value"]
    upload_url = data["uploadUrl"]
    image_urn = data["image"]
    log.info(f"Image URN: {image_urn}")

    with open(image_path, "rb") as f:
        img_bytes = f.read()
    upload_resp = requests.put(
        upload_url,
        headers={"Authorization": f"Bearer {os.environ['LINKEDIN_ACCESS_TOKEN']}"},
        data=img_bytes,
        timeout=120,
    )
    log.info(f"Image upload response: {upload_resp.status_code}")
    upload_resp.raise_for_status()
    return image_urn


def _create_post(text: str, image_urn: str, author_urn: str) -> dict:
    # Log the exact text being sent for debugging
    log.info(f"Publishing post with {len(text)} chars, {len(text.split())} words")
    log.info(f"Post text first 200 chars: {text[:200]}...")

    body = {
        "author": author_urn,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    # Only add image content if we have a valid image URN
    if image_urn:
        body["content"] = {
            "media": {"id": image_urn}
        }

    log.info(f"POST body keys: {list(body.keys())}")
    log.info(f"Commentary length in body: {len(body['commentary'])} chars")

    resp = requests.post(
        f"{API_BASE}/rest/posts",
        headers=_headers({"Content-Type": "application/json"}),
        json=body,
        timeout=60,
    )
    log.info(f"Create post response: {resp.status_code}")
    log.info(f"Create post response headers: {dict(resp.headers)}")
    if resp.text:
        log.info(f"Create post response body: {resp.text[:500]}")

    resp.raise_for_status()
    post_id = resp.headers.get("x-restli-id") or resp.headers.get("x-linkedin-id")
    log.info(f"Post ID from response: {post_id}")
    return {"post_id": post_id, "status_code": resp.status_code}


def run(post_text: str, image_path: str, hashtags: list) -> dict:
    author_urn = os.environ["LINKEDIN_PERSON_URN"]
    full_text = post_text.strip()

    # Append hashtags
    if hashtags:
        hashtag_line = " ".join(f"#{h.lstrip('#')}" for h in hashtags)
        full_text += "\n\n" + hashtag_line

    # CRITICAL SAFETY CHECK: Ensure we're not publishing a truncated post
    word_count = len(full_text.split())
    if word_count < 30:
        log.error(f"SAFETY BLOCK: Refusing to publish truncated post ({word_count} words). Full text: '{full_text}'")
        return {
            "agent": "publisher",
            "output": {
                "status": "failed",
                "error": f"Post too short ({word_count} words) — likely truncated. Aborting publish.",
            },
        }

    log.info(f"Full text to publish: {word_count} words, {len(full_text)} chars")

    try:
        image_urn = None
        if image_path and os.path.exists(image_path):
            image_urn = _upload_image(image_path, author_urn)
        else:
            log.warning(f"Image path missing or not found: {image_path}. Publishing text-only.")

        result = _create_post(full_text, image_urn, author_urn)
        return {
            "agent": "publisher",
            "output": {
                "status": "published",
                "post_id": result["post_id"],
                "word_count": word_count,
                "char_count": len(full_text),
            },
        }
    except requests.HTTPError as e:
        log.error(f"LinkedIn API error: {e}")
        log.error(f"Response body: {getattr(e.response, 'text', '')}")
        return {
            "agent": "publisher",
            "output": {
                "status": "failed",
                "error": str(e),
                "response_body": getattr(e.response, "text", ""),
            },
        }
