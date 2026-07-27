from pathlib import Path
from typing import Any

import boto3
import tenacity

from macbook.shared.exceptions import S3OperationError
from macbook.shared.logger import get_logger

logger = get_logger("s3_client")


class S3Client:
    def __init__(self, region: str = "us-east-1") -> None:
        self._s3 = boto3.client("s3", region_name=region)

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type(S3OperationError),
        reraise=True,
    )
    def download_json(self, bucket: str, key: str) -> dict[str, Any]:
        try:
            response = self._s3.get_object(Bucket=bucket, Key=key)
            import json
            result: dict[str, Any] = json.loads(response["Body"].read().decode("utf-8"))
            return result
        except Exception as exc:
            raise S3OperationError(
                f"Failed to download s3://{bucket}/{key}: {exc}"
            ) from exc

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type(S3OperationError),
        reraise=True,
    )
    def upload_file(self, bucket: str, key: str, file_path: Path) -> str:
        try:
            self._s3.upload_file(
                Filename=str(file_path),
                Bucket=bucket,
                Key=key,
            )
        except Exception as exc:
            raise S3OperationError(
                f"Failed to upload {file_path} to s3://{bucket}/{key}: {exc}"
            ) from exc
        return f"s3://{bucket}/{key}"

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type(S3OperationError),
        reraise=True,
    )
    def download_file(self, bucket: str, key: str, dest: Path) -> Path:
        try:
            self._s3.download_file(Bucket=bucket, Key=key, Filename=str(dest))
        except Exception as exc:
            raise S3OperationError(
                f"Failed to download s3://{bucket}/{key}: {exc}"
            ) from exc
        return dest
