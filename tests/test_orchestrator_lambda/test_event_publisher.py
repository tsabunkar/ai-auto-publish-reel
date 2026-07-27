from unittest.mock import MagicMock, patch

import pytest

from aws.orchestrator_lambda.event_publisher import EventPublisher
from aws.shared.exceptions import EventPublishError


class TestEventPublisher:
    @patch("aws.orchestrator_lambda.event_publisher.boto3.client")
    def test_publish_success(self, mock_boto):
        mock_iot = MagicMock()
        mock_boto.return_value = mock_iot
        publisher = EventPublisher(region="us-east-1")
        publisher.publish("reel/generate", {"job_id": "123"})
        mock_iot.publish.assert_called_once()

    @patch("aws.orchestrator_lambda.event_publisher.boto3.client")
    def test_publish_failure_raises_error(self, mock_boto):
        mock_iot = MagicMock()
        mock_boto.return_value = mock_iot
        mock_iot.publish.side_effect = Exception("IoT error")
        publisher = EventPublisher(region="us-east-1")
        with pytest.raises(EventPublishError, match="IoT error"):
            publisher.publish("reel/generate", {})
