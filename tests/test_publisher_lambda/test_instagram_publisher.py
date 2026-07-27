from unittest.mock import MagicMock, patch

import pytest

from aws.publisher_lambda.instagram_publisher import InstagramPublisher
from aws.shared.exceptions import SocialPublishError


class TestInstagramPublisher:
    def setup_method(self):
        self.credentials = {
            "access_token": "test-token",
            "ig_user_id": "12345",
        }

    @patch("aws.publisher_lambda.instagram_publisher.requests.post")
    def test_publish_success(self, mock_post):
        mock_create = MagicMock()
        mock_create.status_code = 200
        mock_create.json.return_value = {"id": "container-1"}
        mock_publish = MagicMock()
        mock_publish.status_code = 200
        mock_publish.json.return_value = {"id": "media-1"}
        mock_post.side_effect = [mock_create, mock_publish]

        publisher = InstagramPublisher(self.credentials)
        result = publisher.publish("https://video.url", "Test caption")
        assert result == "media-1"

    @patch("aws.publisher_lambda.instagram_publisher.requests.post")
    def test_publish_media_creation_fails(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=400, text="Bad request", json=lambda: {}
        )
        publisher = InstagramPublisher(self.credentials)
        with pytest.raises(SocialPublishError, match="Instagram media creation failed"):
            publisher.publish("https://video.url", "Test")

    @patch("aws.publisher_lambda.instagram_publisher.requests.post")
    def test_publish_rate_limited(self, mock_post):
        mock_create = MagicMock()
        mock_create.status_code = 200
        mock_create.json.return_value = {"id": "container-1"}
        mock_publish = MagicMock()
        mock_publish.status_code = 400
        mock_publish.json.return_value = {
            "error": {"code": 2207042, "message": "Rate limit"}
        }
        mock_post.side_effect = [mock_create, mock_publish]

        publisher = InstagramPublisher(self.credentials)
        with pytest.raises(SocialPublishError, match="rate limit"):
            publisher.publish("https://video.url", "Test")

    @patch("aws.publisher_lambda.instagram_publisher.requests.post")
    def test_publish_no_container_id(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200, json=lambda: {"no_id": True}
        )
        publisher = InstagramPublisher(self.credentials)
        with pytest.raises(SocialPublishError, match="No container ID"):
            publisher.publish("https://video.url", "Test")
