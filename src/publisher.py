"""
Step 4: LinkedIn Publisher Agent
Posts final text and 3D visual slide image to LinkedIn using LinkedIn REST Posts & Images API.
"""

import os
import logging
import requests

log = logging.getLogger("ecopulse")

API_BASE = "https://api.linkedin.com"
LI_VERSION = "202606"


def _headers(extra: dict = None) -> dict:
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    h = {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": LI_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }
    if extra:
        h.update(extra)
    return h


def upload_image(image_path: str, author_urn: str) -> str:
    """Upload image to LinkedIn Images API."""
    log.info(f"Uploading visual slide to LinkedIn: {image_path} ({os.path.getsize(image_path)} bytes)")
    init_resp = requests.post(
        f"{API_BASE}/rest/images?action=initializeUpload",
        headers=_headers({"Content-Type": "application/json"}),
        json={"initializeUploadRequest": {"owner": author_urn}},
        timeout=60,
    )
    init_resp.raise_for_status()
    data = init_resp.json()["value"]
    upload_url = data["uploadUrl"]
    image_urn = data["image"]

    with open(image_path, "rb") as f:
        img_bytes = f.read()

    upload_resp = requests.put(
        upload_url,
        headers={"Authorization": f"Bearer {os.environ.get('LINKEDIN_ACCESS_TOKEN', '').strip()}"},
        data=img_bytes,
        timeout=120,
    )
    upload_resp.raise_for_status()
    log.info(f"Image upload successful. LinkedIn Image URN: {image_urn}")
    return image_urn


def create_post(post_text: str, image_urn: str, author_urn: str) -> dict:
    """Create LinkedIn Post with commentary and attached image URN."""
    body = {
        "author": author_urn,
        "commentary": post_text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    if image_urn:
        body["content"] = {
            "media": {"id": image_urn}
        }

    resp = requests.post(
        f"{API_BASE}/rest/posts",
        headers=_headers({"Content-Type": "application/json"}),
        json=body,
        timeout=60,
    )
    resp.raise_for_status()
    post_id = resp.headers.get("x-restli-id") or resp.headers.get("x-linkedin-id") or "published"
    return {"post_id": post_id, "status_code": resp.status_code}


def publish_to_linkedin(post_text: str, image_path: str) -> dict:
    """
    Publishes the post text and visual slide to LinkedIn.
    """
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    author_urn = os.environ.get("LINKEDIN_PERSON_URN", "").strip()
    dry_run = os.environ.get("ECOPULSE_DRY_RUN", "false").lower() == "true"

    if dry_run or not token or not author_urn:
        log.info("DRY_RUN mode active or missing credentials. Post generated successfully (Dry Run).")
        log.info(f"Post Preview:\n{post_text[:250]}...")
        return {"status": "dry_run", "post_id": "simulated", "post_url": "N/A"}

    image_urn = None
    if image_path and os.path.exists(image_path):
        image_urn = upload_image(image_path, author_urn)

    result = create_post(post_text, image_urn, author_urn)
    post_id = result["post_id"]
    post_url = f"https://www.linkedin.com/feed/update/{post_id}/" if post_id != "simulated" else "N/A"

    log.info(f"✅ Successfully Published to LinkedIn! Post ID: {post_id}")
    log.info(f"🔗 Direct LinkedIn URL: {post_url}")
    return {"status": "published", "post_id": post_id, "post_url": post_url}
