from unittest.mock import MagicMock, patch

import pytest

from aws.orchestrator_lambda.prompt_writer import PromptWriter
from aws.shared.exceptions import PromptWriteError


class TestPromptWriter:
    @patch("aws.orchestrator_lambda.prompt_writer.boto3.client")
    def test_write_prompt_returns_key(self, mock_boto):
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        writer = PromptWriter(region="us-east-1")
        key = writer.write_prompt("test-bucket", {"job_id": "j1", "title": "Test"})
        assert key.startswith("prompts/")
        assert key.endswith(".json")
        mock_s3.put_object.assert_called_once()

    @patch("aws.orchestrator_lambda.prompt_writer.boto3.client")
    def test_write_prompt_failure_raises_error(self, mock_boto):
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        mock_s3.put_object.side_effect = Exception("S3 error")
        writer = PromptWriter(region="us-east-1")
        with pytest.raises(PromptWriteError, match="S3 error"):
            writer.write_prompt("test-bucket", {})

    @patch("aws.orchestrator_lambda.prompt_writer.boto3.client")
    def test_upload_audio_returns_key(self, mock_boto):
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        writer = PromptWriter(region="us-east-1")
        key = writer.upload_audio("test-bucket", "/tmp/audio.mp3", "job-1")
        assert key == "audio/job-1.mp3"
        mock_s3.upload_file.assert_called_once()

    @patch("aws.orchestrator_lambda.prompt_writer.boto3.client")
    def test_generate_presigned_url(self, mock_boto):
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = "https://presigned.url"
        mock_boto.return_value = mock_s3
        writer = PromptWriter(region="us-east-1")
        url = writer.generate_presigned_url("bucket", "audio/test.mp3")
        assert url == "https://presigned.url"
