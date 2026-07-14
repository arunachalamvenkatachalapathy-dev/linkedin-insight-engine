from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

from .config import Settings, settings
from .logger import log_event
from .models import Draft


class LinkedInEngine:
    """Handles publishing posts (with optional images) to LinkedIn."""

    def __init__(self, config: Settings = settings) -> None:
        self.config = config

    def publish(self, draft: Draft) -> int:
        """Publish a post to LinkedIn. Returns the HTTP status code."""
        token = self.config.linkedin_access_token or os.getenv("LINKEDIN_ACCESS_TOKEN", "")
        person_urn = self.config.linkedin_person_urn

        if not token or not person_urn:
            log_event("linkedin", "publish-simulated", reason="missing credentials")
            return 202

        # Upload image if available
        image_urn = ""
        if draft.image_path and Path(draft.image_path).exists():
            image_urn = self._upload_image(token, person_urn, draft.image_path)

        # Build the post payload
        payload = self._build_payload(draft.text, person_urn, image_urn)

        request = Request(
            "https://api.linkedin.com/v2/ugcPosts",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=30) as response:
                log_event("linkedin", "publish-success", http_status=response.status)
                return response.status
        except Exception as exc:
            log_event("linkedin", "publish-error", error=type(exc).__name__, detail=str(exc)[:200])
            return 500

    def _upload_image(self, token: str, person_urn: str, image_path: str) -> str:
        """Upload an image to LinkedIn and return the media URN."""
        try:
            # Step 1: Register the upload
            register_payload = {
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": person_urn,
                    "serviceRelationships": [
                        {
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent",
                        }
                    ],
                }
            }

            register_request = Request(
                "https://api.linkedin.com/v2/assets?action=registerUpload",
                data=json.dumps(register_payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )

            with urlopen(register_request, timeout=15) as response:
                register_data = json.loads(response.read())

            upload_url = register_data["value"]["uploadMechanism"][
                "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
            ]["uploadUrl"]
            media_urn = register_data["value"]["asset"]

            # Step 2: Upload the image binary
            with open(image_path, "rb") as f:
                image_data = f.read()

            upload_request = Request(
                upload_url,
                data=image_data,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/octet-stream",
                },
                method="PUT",
            )

            with urlopen(upload_request, timeout=30) as response:
                pass  # 201 Created expected

            import time
            time.sleep(3) # Give LinkedIn a few seconds to process the asset

            log_event("linkedin", "image-uploaded", media_urn=media_urn)
            return media_urn

        except Exception as exc:
            log_event("linkedin", "image-upload-error", error=type(exc).__name__, detail=str(exc)[:200])
            return ""

    def _build_payload(self, text: str, person_urn: str, image_urn: str = "") -> dict:
        """Build the LinkedIn UGC post payload."""
        if image_urn:
            return {
                "author": person_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": text},
                        "shareMediaCategory": "IMAGE",
                        "media": [
                            {
                                "status": "READY",
                                "description": {"text": "Environment & Nature"},
                                "media": image_urn,
                                "title": {"text": "Insightful Image"}
                            }
                        ],
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            }
        else:
            return {
                "author": person_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": text},
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            }
