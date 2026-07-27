import json
from unittest.mock import MagicMock, patch

import pytest

from macbook.controller.s3_client import S3Client
from macbook.shared.exceptions import S3OperationError


class TestS3Client:
    @patch("macbook.controller.s3_client.boto3.client")
    def test_download_json_success(self, mock_boto):
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        mock_s3.get_object.return_value = {
            "Body": MagicMock(
                read=MagicMock(
                    return_value=json.dumps({"key": "value"}).encode()
                )
            )
        }
        client = S3Client(region="us-east-1")
        result = client.download_json("bucket", "prompts/test.json")
        assert result == {"key": "value"}

    @patch("macbook.controller.s3_client.boto3.client")
    def test_download_json_failure(self, mock_boto):
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        mock_s3.get_object.side_effect = Exception("S3 error")
        client = S3Client(region="us-east-1")
        with pytest.raises(S3OperationError, match="S3 error"):
            client.download_json("bucket", "prompts/test.json")

    @patch("macbook.controller.s3_client.boto3.client")
    def test_upload_file_success(self, mock_boto, tmp_path):
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        test_file = tmp_path / "test.mp4"
        test_file.write_text("data")
        client = S3Client(region="us-east-1")
        result = client.upload_file("bucket", "videos/test.mp4", test_file)
        assert "s3://" in result

    @patch("macbook.controller.s3_client.boto3.client")
    def test_download_file_success(self, mock_boto, tmp_path):
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        dest = tmp_path / "video.mp4"
        client = S3Client(region="us-east-1")
        result = client.download_file("bucket", "videos/test.mp4", dest)
        assert result == dest
