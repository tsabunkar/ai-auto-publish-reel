import json
from typing import Any

import boto3
import tenacity

from aws.shared.exceptions import ContentGenerationError


class ContentGenerator:
    def __init__(self, model_id: str, region: str = "us-east-1") -> None:
        self._model_id = model_id
        self._client = boto3.client("bedrock-runtime", region_name=region)

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=30),
        retry=tenacity.retry_if_exception_type(ContentGenerationError),
        reraise=True,
    )
    def generate(self, topics: list[str]) -> dict[str, Any]:
        prompt = self._build_prompt(topics)
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}],
        }
        try:
            resp = self._client.invoke_model(
                modelId=self._model_id,
                contentType="application/json",
                body=json.dumps(body),
            )
        except Exception as exc:
            raise ContentGenerationError(f"Bedrock invoke failed: {exc}") from exc

        response_body = json.loads(resp["body"].read())
        content = response_body.get("content", [])
        text = " ".join(block.get("text", "") for block in content)

        try:
            parsed: dict[str, Any] = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ContentGenerationError(
                f"Failed to parse Bedrock response as JSON: {exc}"
            ) from exc

        required = [
            "title",
            "voiceover_text",
            "video_prompt",
            "instagram_caption",
            "linkedin_caption",
            "youtube_description",
            "hashtags",
        ]
        for key in required:
            if key not in parsed:
                raise ContentGenerationError(
                    f"Missing required field '{key}' in Bedrock response"
                )
        return parsed

    def _build_prompt(self, topics: list[str]) -> str:
        topic_list = "\n".join(
            f"- {t}" for t in topics
        ) if topics else "- General leadership development"
        return f"""You are an expert educational content creator.

Based on these trending leadership topics:
{topic_list}

Generate educational content in valid JSON format (no markdown, no code fences).

{{
    "title": "Engaging video title",
    "voiceover_text": "Narration script (30-45 seconds, conversational, educational)",
    "video_prompt": "Detailed text-to-video prompt showing an educational leadership concept visually",
    "instagram_caption": "Instagram caption with relevant hashtags (max 2200 chars)",
    "linkedin_caption": "Professional LinkedIn post (max 3000 chars)",
    "youtube_description": "YouTube video description with chapters and links",
    "hashtags": ["5-8", "relevant", "hashtags"]
}}
"""
