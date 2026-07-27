import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import boto3

from aws.publisher_lambda.instagram_publisher import InstagramPublisher
from aws.publisher_lambda.linkedin_publisher import LinkedInPublisher
from aws.publisher_lambda.video_downloader import VideoDownloader
from aws.publisher_lambda.youtube_publisher import YouTubePublisher
from aws.shared.config import PublisherConfig
from aws.shared.exceptions import SocialPublishError
from aws.shared.logger import get_logger
from aws.shared.models import ExecutionSummary, PublishResult

logger = get_logger("publisher")


def _get_secret(secret_id: str, region: str) -> dict[str, Any]:
    client = boto3.client("secretsmanager", region_name=region)
    resp = client.get_secret_value(SecretId=secret_id)
    result: dict[str, Any] = json.loads(resp["SecretString"])
    return result


def _publish_instagram(
    credentials: dict[str, Any],
    video_url: str,
    caption: str,
    job_id: str,
) -> PublishResult:
    publisher = InstagramPublisher(credentials)
    try:
        url = publisher.publish(video_url, caption)
        return PublishResult(platform="instagram", success=True, url=url)
    except SocialPublishError as exc:
        logger.warning(
            "Instagram publish failed",
            extra={"job_id": job_id, "error": str(exc)},
        )
        return PublishResult(platform="instagram", success=False, error=str(exc))
    except Exception as exc:
        logger.error(
            "Instagram unexpected error",
            extra={"job_id": job_id, "error": str(exc)},
        )
        return PublishResult(platform="instagram", success=False, error=str(exc))


def _publish_linkedin(
    credentials: dict[str, Any],
    video_path: str,
    commentary: str,
    job_id: str,
) -> PublishResult:
    publisher = LinkedInPublisher(credentials)
    try:
        url = publisher.publish(Path(video_path), commentary)
        return PublishResult(platform="linkedin", success=True, url=url)
    except SocialPublishError as exc:
        logger.warning(
            "LinkedIn publish failed",
            extra={"job_id": job_id, "error": str(exc)},
        )
        return PublishResult(platform="linkedin", success=False, error=str(exc))
    except Exception as exc:
        logger.error(
            "LinkedIn unexpected error",
            extra={"job_id": job_id, "error": str(exc)},
        )
        return PublishResult(platform="linkedin", success=False, error=str(exc))


def _publish_youtube(
    credentials: dict[str, Any],
    video_path: str,
    title: str,
    description: str,
    hashtags: list[str],
    job_id: str,
) -> PublishResult:
    publisher = YouTubePublisher(credentials)
    try:
        full_description = f"{description}\n\n{' '.join('#' + t for t in hashtags)}"
        url = publisher.publish(
            Path(video_path), title, full_description, tags=hashtags
        )
        return PublishResult(platform="youtube", success=True, url=url)
    except SocialPublishError as exc:
        logger.warning(
            "YouTube publish failed",
            extra={"job_id": job_id, "error": str(exc)},
        )
        return PublishResult(platform="youtube", success=False, error=str(exc))
    except Exception as exc:
        logger.error(
            "YouTube unexpected error",
            extra={"job_id": job_id, "error": str(exc)},
        )
        return PublishResult(platform="youtube", success=False, error=str(exc))


def handler(event: dict[str, Any], _context: object = None) -> dict[str, Any]:
    config = PublisherConfig()
    job_id = event.get("jobId", event.get("job_id", "unknown"))
    bucket = event.get("bucket", config.content_bucket)
    video_key = event.get("videoKey", event.get("video_key", ""))

    logger.info(
        "Publisher Lambda invoked",
        extra={"job_id": job_id, "correlation_id": job_id},
    )

    if not video_key:
        logger.error("No videoKey in event", extra={"job_id": job_id})
        return {"statusCode": 400, "body": "Missing videoKey"}

    video_path = os.path.join(tempfile.gettempdir(), f"{job_id}.mp4")

    downloader = VideoDownloader(region=config.aws_region)
    try:
        downloader.download(bucket, video_key, Path(video_path))
    except Exception as exc:
        logger.error("Video download failed", extra={"job_id": job_id, "error": str(exc)})
        return {"statusCode": 500, "body": str(exc)}

    s3 = boto3.client("s3", region_name=config.aws_region)
    video_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": video_key},
        ExpiresIn=86400,
    )

    instagram_creds = _get_secret(config.instagram_secret_id, config.aws_region)
    linkedin_creds = _get_secret(config.linkedin_secret_id, config.aws_region)
    youtube_creds = _get_secret(config.youtube_secret_id, config.aws_region)

    instagram_caption = event.get("instagram_caption", "")
    linkedin_caption = event.get("linkedin_caption", "")
    youtube_description = event.get("youtube_description", "")
    title = event.get("title", "Leadership Insight")
    hashtags = event.get("hashtags", [])

    results: list[PublishResult] = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(
                _publish_instagram, instagram_creds, video_url, instagram_caption, job_id
            ): "instagram",
            executor.submit(
                _publish_linkedin, linkedin_creds, video_path, linkedin_caption, job_id
            ): "linkedin",
            executor.submit(
                _publish_youtube,
                youtube_creds,
                video_path,
                title,
                youtube_description,
                hashtags,
                job_id,
            ): "youtube",
        }
        for future in as_completed(futures):
            results.append(future.result())

    if os.path.exists(video_path):
        os.remove(video_path)

    summary = ExecutionSummary(job_id=job_id, results=results)
    all_succeeded = all(r.success for r in results)

    logger.info(
        "Publisher completed",
        extra={
            "job_id": job_id,
            "results": summary.model_dump(),
        },
    )

    return {
        "statusCode": 200 if all_succeeded else 207,
        "body": summary.model_dump(),
    }
