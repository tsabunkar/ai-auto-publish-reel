from pydantic_settings import BaseSettings


class OrchestratorConfig(BaseSettings):
    model_config = {"env_prefix": "", "case_sensitive": False}

    aws_region: str = "us-east-1"
    content_bucket: str = ""
    rss_feed_urls: str = (
        "https://feeds.hbr.org/harvardbusiness,https://www.forbes.com/leadership/feed/"
    )
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    polly_voice_id: str = "Matthew"
    job_queue_topic: str = "reel/generate"


class PublisherConfig(BaseSettings):
    model_config = {"env_prefix": "", "case_sensitive": False}

    aws_region: str = "us-east-1"
    content_bucket: str = ""
    instagram_secret_id: str = "instagram-credentials"
    linkedin_secret_id: str = "linkedin-credentials"
    youtube_secret_id: str = "youtube-credentials"
