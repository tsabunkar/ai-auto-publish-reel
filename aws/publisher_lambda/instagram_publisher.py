from typing import Any

import requests
import tenacity

from aws.shared.exceptions import SocialPublishError


class InstagramPublisher:
    def __init__(self, credentials: dict[str, Any]) -> None:
        self._access_token = credentials["access_token"]
        self._ig_user_id = credentials["ig_user_id"]

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(2),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
        retry=tenacity.retry_if_exception_type(SocialPublishError),
        reraise=True,
    )
    def publish(self, video_url: str, caption: str) -> str:
        create_resp = requests.post(
            f"https://graph.facebook.com/v25.0/{self._ig_user_id}/media",
            params={
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "access_token": self._access_token,
            },
            timeout=30,
        )
        if create_resp.status_code != 200:
            raise SocialPublishError(
                f"Instagram media creation failed: {create_resp.text}"
            )
        container_id = create_resp.json().get("id")
        if not container_id:
            raise SocialPublishError(
                f"No container ID in response: {create_resp.text}"
            )

        publish_resp = requests.post(
            f"https://graph.facebook.com/v25.0/{self._ig_user_id}/media_publish",
            params={
                "creation_id": container_id,
                "access_token": self._access_token,
            },
            timeout=30,
        )
        if publish_resp.status_code != 200:
            body = publish_resp.json()
            err = body.get("error", {})
            if err.get("code") == 2207042:
                raise SocialPublishError("Instagram rate limit (50/day) reached")
            raise SocialPublishError(
                f"Instagram publish failed: {publish_resp.text}"
            )

        result = publish_resp.json()
        return str(result.get("id", ""))
