
import tenacity

from macbook.controller.mqtt_client import MQTTClient
from macbook.shared.config import MacBookConfig
from macbook.shared.logger import get_logger
from macbook.shared.models import CompletedEventPayload

logger = get_logger("completion_publisher")


class CompletionPublisher:
    def __init__(self, config: MacBookConfig, mqtt: MQTTClient) -> None:
        self._config = config
        self._mqtt = mqtt

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
    )
    async def publish(
        self,
        job_id: str,
        bucket: str,
        video_key: str,
    ) -> None:
        event = CompletedEventPayload(
            job_id=job_id,
            bucket=bucket,
            video_key=video_key,
        )
        await self._mqtt.publish(
            self._config.completion_topic,
            event.model_dump(),
        )
        logger.info(
            "Published completion event",
            extra={
                "job_id": job_id,
                "topic": self._config.completion_topic,
                "video_key": video_key,
            },
        )
