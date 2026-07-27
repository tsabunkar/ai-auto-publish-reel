import json
from typing import Any

import boto3
import tenacity

from aws.shared.exceptions import EventPublishError


class EventPublisher:
    def __init__(self, region: str = "us-east-1") -> None:
        self._client = boto3.client("iot-data", region_name=region)

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type(EventPublishError),
    )
    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        try:
            self._client.publish(
                topic=topic,
                qos=1,
                payload=json.dumps(payload, default=str).encode("utf-8"),
            )
        except Exception as exc:
            raise EventPublishError(
                f"Failed to publish to {topic}: {exc}"
            ) from exc
