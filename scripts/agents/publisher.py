"""
Publisher agent — posts the final text + image to LinkedIn using the LinkedIn
Posts API (versioned REST API, the current recommended approach as of 2026).

NOTE: LinkedIn's API surface changes over time. Before relying on this in
production, cross-check the endpoints/headers below against LinkedIn's
current docs at https://learn.microsoft.com/en-us/linkedin/ — specifically
the "Posts API" and "Images API" sections. This implementation follows the
documented flow as of writing:
  1. Initialize an image upload -> get an uploadUrl + image URN
  2. PUT the raw image bytes to that uploadUrl
  3. Create the post referencing the image URN

Required environment variables (set as GitHub Actions secrets):
  LINKEDIN_ACCESS_TOKEN  - OAuth2 token with the w_member_social scope
  LINKEDIN_PERSON_URN    - e.g. "urn:li:person:XXXXXXXX" (your member URN)
"""
import os
import requests

API_BASE = "https://api.linkedin.com"
LI_VERSION = "202606"  # bump as needed to a current LinkedIn API version


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
        upload_resp = requests.put(
            upload_url,
            headers={"Authorization": f"Bearer {os.environ['LINKEDIN_ACCESS_TOKEN']}"},
            data=f.read(),
            timeout=120,
        )
    upload_resp.raise_for_status()
    return image_urn


def _create_post(text: str, image_urn: str, author_urn: str) -> dict:
    body = {
        "author": author_urn,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "content": {
            "media": {"id": image_urn}
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    resp = requests.post(
        f"{API_BASE}/rest/posts",
        headers=_headers({"Content-Type": "application/json"}),
        json=body,
        timeout=60,
    )
    resp.raise_for_status()
    post_id = resp.headers.get("x-restli-id") or resp.headers.get("x-linkedin-id")
    return {"post_id": post_id, "status_code": resp.status_code}


def run(post_text: str, image_path: str, hashtags: list) -> dict:
    author_urn = os.environ["LINKEDIN_PERSON_URN"]
    full_text = post_text.strip()
    if hashtags:
        full_text += "\n\n" + " ".join(f"#{h.lstrip('#')}" for h in hashtags)

    try:
        image_urn = _upload_image(image_path, author_urn)
        result = _create_post(full_text, image_urn, author_urn)
        return {
            "agent": "publisher",
            "output": {
                "status": "published",
                "post_id": result["post_id"],
            },
        }
    except requests.HTTPError as e:
        return {
            "agent": "publisher",
            "output": {
                "status": "failed",
                "error": str(e),
                "response_body": getattr(e.response, "text", ""),
            },
        }
