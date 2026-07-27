from pathlib import Path
from typing import Any, cast

import requests
import tenacity

from aws.shared.exceptions import SocialPublishError


class YouTubePublisher:
    def __init__(self, credentials: dict[str, Any]) -> None:
        self._access_token = credentials.get("access_token", "")
        self._refresh_token = credentials.get("refresh_token", "")
        self._client_id = credentials.get("client_id", "")
        self._client_secret = credentials.get("client_secret", "")

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(2),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
        retry=tenacity.retry_if_exception_type(SocialPublishError),
    )
    def publish(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str] | None = None,
    ) -> str:
        metadata = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags or [],
                "categoryId": "27",
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        }

        init_url = (
            "https://www.googleapis.com/upload/youtube/v3/videos"
            "?part=snippet,status&uploadType=resumable"
        )
        init_headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(video_path.stat().st_size),
        }

        init_resp = requests.post(
            init_url, headers=init_headers, json=cast(Any, metadata), timeout=30
        )
        if init_resp.status_code != 200:
            raise SocialPublishError(
                f"YouTube upload init failed: {init_resp.text}"
            )

        upload_url = init_resp.headers.get("Location", "")
        if not upload_url:
            raise SocialPublishError("No upload URL in YouTube response")

        file_size = video_path.stat().st_size
        with open(video_path, "rb") as f:
            upload_resp = requests.put(
                upload_url,
                data=f,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(file_size),
                },
                timeout=600,
            )

        if upload_resp.status_code not in (200, 201):
            raise SocialPublishError(
                f"YouTube upload failed (status={upload_resp.status_code}): "
                f"{upload_resp.text}"
            )

        result = upload_resp.json()
        return str(result.get("id", ""))
