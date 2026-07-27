import os
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from aws.orchestrator_lambda.content_generator import ContentGenerator
from aws.orchestrator_lambda.event_publisher import EventPublisher
from aws.orchestrator_lambda.prompt_writer import PromptWriter
from aws.orchestrator_lambda.topic_crawler import TopicCrawler
from aws.orchestrator_lambda.tts_generator import TTSGenerator
from aws.shared.config import OrchestratorConfig
from aws.shared.logger import get_logger
from aws.shared.models import GenerateEvent

logger = get_logger("orchestrator")


def _build_content(
    crawler: TopicCrawler,
    generator: ContentGenerator,
    feed_urls: str,
) -> dict[str, Any]:
    urls = [u.strip() for u in feed_urls.split(",") if u.strip()]
    topics = crawler.crawl(urls, max_items=5)
    return generator.generate(topics)


def _create_audio(
    tts: TTSGenerator,
    voiceover_text: str,
    tmp_dir: str,
    job_id: str,
) -> str:
    audio_path = os.path.join(tmp_dir, f"{job_id}.mp3")
    tts.synthesize(voiceover_text, Path(audio_path))
    return audio_path


def handler(_event: dict[str, Any], _context: object = None) -> dict[str, Any]:
    config = OrchestratorConfig()
    job_id = str(uuid4())

    logger.info(
        "Orchestrator started",
        extra={"job_id": job_id, "correlation_id": job_id},
    )

    crawler = TopicCrawler()
    generator = ContentGenerator(
        model_id=config.bedrock_model_id, region=config.aws_region
    )
    tts = TTSGenerator(voice_id=config.polly_voice_id, region=config.aws_region)
    writer = PromptWriter(region=config.aws_region)
    publisher = EventPublisher(region=config.aws_region)

    try:
        content = _build_content(crawler, generator, config.rss_feed_urls)
        content["job_id"] = job_id
    except Exception as exc:
        logger.error("Content generation failed", extra={"job_id": job_id, "error": str(exc)})
        return {"statusCode": 500, "body": str(exc)}

    audio_key = None
    voiceover_text = content.get("voiceover_text", "")
    if voiceover_text:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = tmp_dir
            try:
                audio_path = _create_audio(tts, voiceover_text, tmp_path, job_id)
                audio_key = writer.upload_audio(
                    config.content_bucket, audio_path, job_id
                )
                voiceover_url = writer.generate_presigned_url(
                    config.content_bucket, audio_key
                )
                content["voiceover_url"] = voiceover_url
            except Exception as exc:
                logger.warning(
                    "TTS generation failed, continuing without audio",
                    extra={"job_id": job_id, "error": str(exc)},
                )
                content["voiceover_url"] = ""
    else:
        content["voiceover_url"] = ""

    try:
        prompt_key = writer.write_prompt(config.content_bucket, content)
    except Exception as exc:
        logger.error("Prompt write failed", extra={"job_id": job_id, "error": str(exc)})
        return {"statusCode": 500, "body": str(exc)}

    event_payload = GenerateEvent(
        job_id=job_id,
        bucket=config.content_bucket,
        prompt_key=prompt_key,
    )

    try:
        publisher.publish(config.job_queue_topic, event_payload.model_dump())
    except Exception as exc:
        logger.error("Event publish failed", extra={"job_id": job_id, "error": str(exc)})
        return {"statusCode": 500, "body": str(exc)}

    logger.info(
        "Orchestrator completed",
        extra={
            "job_id": job_id,
            "prompt_key": prompt_key,
            "audio_key": audio_key or "none",
        },
    )

    return {
        "statusCode": 200,
        "body": event_payload.model_dump(),
    }
