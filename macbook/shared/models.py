from uuid import uuid4

from pydantic import BaseModel, Field


class GenerateEvent(BaseModel):
    job_id: str
    bucket: str
    prompt_key: str


class CompletedEventPayload(BaseModel):
    job_id: str
    bucket: str
    video_key: str


class JobState(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid4()))
    status: str = "pending"  # pending | in_progress | completed | failed
    bucket: str = ""
    prompt_key: str = ""
    video_key: str = ""
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class RenderResult(BaseModel):
    exit_code: int
    stdout: str
    stderr: str
    elapsed_seconds: float
    command: list[str]


class VideoTransferResult(BaseModel):
    local_path: str
    size_bytes: int
    elapsed_seconds: float
