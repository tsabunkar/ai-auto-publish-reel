from typing import Any

import pytest


@pytest.fixture
def sample_prompt() -> dict[str, Any]:
    return {
        "job_id": "test-job-001",
        "title": "The Art of Delegation",
        "voiceover_text": "Great leaders know how to delegate effectively.",
        "voiceover_url": "https://s3.amazonaws.com/bucket/audio/test.mp3",
        "video_prompt": "Animated visualization of a leader delegating tasks",
        "instagram_caption": "Master the art of delegation #leadership",
        "linkedin_caption": "Effective delegation is a cornerstone of leadership.",
        "youtube_description": "Learn the art of delegation in leadership.",
        "hashtags": ["leadership", "delegation", "management"],
    }


@pytest.fixture
def sample_generate_event() -> dict[str, Any]:
    return {
        "jobId": "test-job-001",
        "bucket": "test-bucket",
        "promptKey": "prompts/test-job-001.json",
    }


@pytest.fixture
def sample_completed_event() -> dict[str, Any]:
    return {
        "jobId": "test-job-001",
        "bucket": "test-bucket",
        "videoKey": "videos/test-job-001.mp4",
    }


@pytest.fixture
def sample_workflow() -> dict[str, Any]:
    return {
        "1": {
            "class_type": "LoadDiffusionModel",
            "inputs": {"model_name": "test_model.safetensors"},
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "", "clip": ["3", 0]},
        },
        "7": {
            "class_type": "EmptyHunyuanLatentVideo",
            "inputs": {"width": 720, "height": 1280, "length": 81},
        },
    }


@pytest.fixture
def mock_rss_content() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item><title>Leading Through Change</title></item>
    <item><title>The Future of Remote Work</title></item>
  </channel>
</rss>"""


@pytest.fixture
def bedrock_response() -> dict[str, Any]:
    return {
        "title": "Leading Through Change",
        "voiceover_text": "Change is the only constant in leadership.",
        "video_prompt": "A leader guiding a team through transformation",
        "instagram_caption": "Lead through change #leadership",
        "linkedin_caption": "Change management is essential for leaders.",
        "youtube_description": "Learn to lead through organizational change.",
        "hashtags": ["change", "leadership", "transformation"],
    }
