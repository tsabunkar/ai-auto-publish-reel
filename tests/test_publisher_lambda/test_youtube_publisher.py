from unittest.mock import MagicMock, patch

import pytest

from aws.publisher_lambda.youtube_publisher import YouTubePublisher
from aws.shared.exceptions import SocialPublishError


class TestYouTubePublisher:
    def setup_method(self):
        self.credentials = {
            "access_token": "test-token",
            "refresh_token": "refresh-token",
            "client_id": "client-id",
            "client_secret": "client-secret",
        }

    def _create_test_video(self, tmp_path, size=1024):
        path = tmp_path / "test.mp4"
        path.write_bytes(b"x" * size)
        return path

    @patch("aws.publisher_lambda.youtube_publisher.requests.post")
    @patch("aws.publisher_lambda.youtube_publisher.requests.put")
    def test_publish_success(self, mock_put, mock_post, tmp_path):
        video = self._create_test_video(tmp_path)
        mock_init = MagicMock()
        mock_init.status_code = 200
        mock_init.headers = {"Location": "https://upload.youtube.com/session"}
        mock_upload = MagicMock()
        mock_upload.status_code = 200
        mock_upload.json.return_value = {"id": "youtube-video-id"}
        mock_post.return_value = mock_init
        mock_put.return_value = mock_upload

        publisher = YouTubePublisher(self.credentials)
        result = publisher.publish(video, "Test Title", "Test description", ["tag1"])
        assert result == "youtube-video-id"

    @patch("aws.publisher_lambda.youtube_publisher.requests.post")
    def test_publish_init_fails(self, mock_post, tmp_path):
        video = self._create_test_video(tmp_path)
        mock_post.return_value = MagicMock(
            status_code=400, text="Init error"
        )
        publisher = YouTubePublisher(self.credentials)
        with pytest.raises(SocialPublishError, match="YouTube upload init failed"):
            publisher.publish(video, "Title", "Desc")

    @patch("aws.publisher_lambda.youtube_publisher.requests.post")
    @patch("aws.publisher_lambda.youtube_publisher.requests.put")
    def test_publish_upload_fails(self, mock_put, mock_post, tmp_path):
        video = self._create_test_video(tmp_path)
        mock_init = MagicMock()
        mock_init.status_code = 200
        mock_init.headers = {"Location": "https://upload.youtube.com/session"}
        mock_upload = MagicMock()
        mock_upload.status_code = 400
        mock_upload.text = "Upload error"
        mock_post.return_value = mock_init
        mock_put.return_value = mock_upload

        publisher = YouTubePublisher(self.credentials)
        with pytest.raises(SocialPublishError, match="YouTube upload failed"):
            publisher.publish(video, "Title", "Desc")

    @patch("aws.publisher_lambda.youtube_publisher.requests.post")
    def test_publish_no_location_header(self, mock_post, tmp_path):
        video = self._create_test_video(tmp_path)
        mock_post.return_value = MagicMock(
            status_code=200, headers={}, json=lambda: {}
        )
        publisher = YouTubePublisher(self.credentials)
        with pytest.raises(SocialPublishError, match="No upload URL"):
            publisher.publish(video, "Title", "Desc")
