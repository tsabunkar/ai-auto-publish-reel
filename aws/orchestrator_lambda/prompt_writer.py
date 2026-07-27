import json
from typing import Any
from uuid import uuid4

import boto3
import tenacity

from aws.shared.exceptions import PromptWriteError


class PromptWriter:
    def __init__(self, region: str = "us-east-1") -> None:
        self._s3 = boto3.client("s3", region_name=region)

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type(PromptWriteError),
    )
    def write_prompt(self, bucket: str, content: dict[str, Any]) -> str:
        job_id = content.get("job_id", str(uuid4()))
        key = f"prompts/{job_id}.json"
        try:
            self._s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(content, default=str),
                ContentType="application/json",
            )
        except Exception as exc:
            raise PromptWriteError(f"Failed to upload prompt to S3: {exc}") from exc
        return key

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type(PromptWriteError),
    )
    def upload_audio(self, bucket: str, audio_path: str, job_id: str) -> str:
        key = f"audio/{job_id}.mp3"
        try:
            self._s3.upload_file(
                Filename=str(audio_path),
                Bucket=bucket,
                Key=key,
            )
        except Exception as exc:
            raise PromptWriteError(f"Failed to upload audio to S3: {exc}") from exc
        return key

    def generate_presigned_url(
        self, bucket: str, key: str, expiration: int = 21600
    ) -> str:
        return str(
            self._s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expiration,
            )
        )
