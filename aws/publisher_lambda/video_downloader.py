from pathlib import Path

import boto3
import tenacity

from aws.shared.exceptions import VideoDownloadError


class VideoDownloader:
    def __init__(self, region: str = "us-east-1") -> None:
        self._s3 = boto3.client("s3", region_name=region)

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type(VideoDownloadError),
    )
    def download(self, bucket: str, key: str, dest: Path) -> Path:
        try:
            self._s3.download_file(Bucket=bucket, Key=key, Filename=str(dest))
        except Exception as exc:
            raise VideoDownloadError(
                f"Failed to download s3://{bucket}/{key}: {exc}"
            ) from exc
        return dest
