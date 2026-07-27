class OrchestratorError(Exception):
    """Base orchestrator error."""


class TopicCrawlError(OrchestratorError):
    """RSS feed crawl failed."""


class ContentGenerationError(OrchestratorError):
    """Bedrock content generation failed."""


class TTSGenerationError(OrchestratorError):
    """Amazon Polly synthesis failed."""


class PromptWriteError(OrchestratorError):
    """S3 upload of prompt.json failed."""


class EventPublishError(OrchestratorError):
    """MQTT publish to reel/generate failed."""


class PublisherError(Exception):
    """Base publisher error."""


class VideoDownloadError(PublisherError):
    """S3 download of video failed."""


class SocialPublishError(PublisherError):
    """Social media API publish failed."""
