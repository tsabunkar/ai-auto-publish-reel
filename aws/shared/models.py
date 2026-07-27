from uuid import uuid4

from pydantic import BaseModel, Field


class PromptPayload(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    voiceover_text: str
    voiceover_url: str
    video_prompt: str
    instagram_caption: str
    linkedin_caption: str
    youtube_description: str
    hashtags: list[str]


class GenerateEvent(BaseModel):
    job_id: str
    bucket: str
    prompt_key: str


class CompletedEvent(BaseModel):
    job_id: str
    bucket: str
    video_key: str


class PublishResult(BaseModel):
    platform: str
    success: bool
    url: str | None = None
    error: str | None = None


class ExecutionSummary(BaseModel):
    job_id: str
    results: list[PublishResult]
