from unittest.mock import MagicMock, patch

import pytest

from aws.publisher_lambda.linkedin_publisher import LinkedInPublisher
from aws.shared.exceptions import SocialPublishError


class TestLinkedInPublisher:
    def setup_method(self):
        self.credentials = {
            "access_token": "test-token",
            "organization_urn": "urn:li:organization:123",
        }

    def _create_test_video(self, tmp_path, size=4096):
        path = tmp_path / "test.mp4"
        path.write_bytes(b"x" * size)
        return path

    @patch("aws.publisher_lambda.linkedin_publisher.requests.post")
    @patch("aws.publisher_lambda.linkedin_publisher.requests.put")
    def test_publish_success(self, mock_put, mock_post, tmp_path):
        video = self._create_test_video(tmp_path)
        mock_init = MagicMock()
        mock_init.status_code = 200
        mock_init.json.return_value = {
            "value": {
                "video": "urn:li:video:abc",
                "uploadInstructions": [
                    {"firstByte": 0, "lastByte": 2047, "uploadUrl": "https://upload.1"},
                    {"firstByte": 2048, "lastByte": 4095, "uploadUrl": "https://upload.2"},
                ],
                "uploadToken": "token123",
            }
        }
        mock_chunk = MagicMock()
        mock_chunk.status_code = 201
        mock_chunk.headers = {"ETag": "etag1"}
        mock_chunk2 = MagicMock()
        mock_chunk2.status_code = 201
        mock_chunk2.headers = {"ETag": "etag2"}
        mock_finalize = MagicMock()
        mock_finalize.status_code = 200
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 201
        mock_post_resp.json.return_value = {"id": "post-urn:li:post:123"}
        mock_post.side_effect = [mock_init, mock_finalize, mock_post_resp]
        mock_put.side_effect = [mock_chunk, mock_chunk2]

        publisher = LinkedInPublisher(self.credentials)
        result = publisher.publish(video, "Test commentary")
        assert result is not None

    @patch("aws.publisher_lambda.linkedin_publisher.requests.post")
    def test_publish_init_fails(self, mock_post, tmp_path):
        video = self._create_test_video(tmp_path)
        mock_post.return_value = MagicMock(
            status_code=400, text="Init failed"
        )
        publisher = LinkedInPublisher(self.credentials)
        with pytest.raises(SocialPublishError, match="LinkedIn init upload failed"):
            publisher.publish(video, "Test")

    @patch("aws.publisher_lambda.linkedin_publisher.requests.post")
    @patch("aws.publisher_lambda.linkedin_publisher.requests.put")
    def test_publish_chunk_fails(self, mock_put, mock_post, tmp_path):
        video = self._create_test_video(tmp_path, size=2048)
        mock_init = MagicMock()
        mock_init.status_code = 200
        mock_init.json.return_value = {
            "value": {
                "video": "urn:li:video:abc",
                "uploadInstructions": [
                    {"firstByte": 0, "lastByte": 2047, "uploadUrl": "https://upload.1"},
                ],
                "uploadToken": "token123",
            }
        }
        mock_post.return_value = mock_init
        mock_put.return_value = MagicMock(status_code=500, text="Upload failed")
        publisher = LinkedInPublisher(self.credentials)
        with pytest.raises(SocialPublishError, match="LinkedIn chunk upload failed"):
            publisher.publish(video, "Test")
