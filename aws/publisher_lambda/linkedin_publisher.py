from pathlib import Path
from typing import Any

import requests
import tenacity

from aws.shared.exceptions import SocialPublishError


class LinkedInPublisher:
    def __init__(self, credentials: dict[str, Any]) -> None:
        self._access_token = credentials["access_token"]
        self._org_urn = credentials["organization_urn"]
        self._headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Linkedin-Version": "202604",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(2),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
        retry=tenacity.retry_if_exception_type(SocialPublishError),
    )
    def publish(self, video_path: Path, commentary: str) -> str:
        file_size = video_path.stat().st_size

        init_resp = requests.post(
            "https://api.linkedin.com/rest/videos?action=initializeUpload",
            headers=self._headers,
            json={
                "initializeUploadRequest": {
                    "owner": self._org_urn,
                    "fileSizeBytes": file_size,
                    "uploadCaptions": False,
                    "uploadThumbnail": False,
                }
            },
            timeout=30,
        )
        if init_resp.status_code != 200:
            raise SocialPublishError(
                f"LinkedIn init upload failed: {init_resp.text}"
            )

        init_data = init_resp.json()
        video_urn = init_data["value"]["video"]
        upload_instructions = init_data["value"]["uploadInstructions"]
        upload_token = init_data["value"].get("uploadToken", "")

        etags: list[str] = []
        for instruction in upload_instructions:
            first_byte = instruction["firstByte"]
            last_byte = instruction["lastByte"]
            upload_url = instruction["uploadUrl"]

            chunk_size = last_byte - first_byte + 1
            with open(video_path, "rb") as f:
                f.seek(first_byte)
                chunk = f.read(chunk_size)

            chunk_resp = requests.put(
                upload_url,
                data=chunk,
                headers={
                    "Content-Type": "application/octet-stream",
                    "Content-Range": f"bytes {first_byte}-{last_byte}/{file_size}",
                },
                timeout=120,
            )
            if chunk_resp.status_code not in (200, 201):
                raise SocialPublishError(
                    f"LinkedIn chunk upload failed (status={chunk_resp.status_code})"
                )
            etag = chunk_resp.headers.get("ETag", "")
            if etag:
                etags.append(etag)

        finalize_resp = requests.post(
            "https://api.linkedin.com/rest/videos?action=finalizeUpload",
            headers=self._headers,
            json={
                "finalizeUploadRequest": {
                    "video": video_urn,
                    "uploadToken": upload_token,
                    "uploadedPartIds": etags,
                }
            },
            timeout=30,
        )
        if finalize_resp.status_code != 200:
            raise SocialPublishError(
                f"LinkedIn finalize upload failed: {finalize_resp.text}"
            )

        post_resp = requests.post(
            "https://api.linkedin.com/rest/posts",
            headers={**self._headers, "Content-Type": "application/json"},
            json={
                "author": self._org_urn,
                "commentary": commentary,
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": [],
                },
                "content": {
                    "media": {
                        "title": "Leadership Insight",
                        "id": video_urn,
                    }
                },
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False,
            },
            timeout=30,
        )
        if post_resp.status_code != 201:
            raise SocialPublishError(
                f"LinkedIn post creation failed: {post_resp.text}"
            )

        result = post_resp.json()
        return str(result.get("id", ""))
