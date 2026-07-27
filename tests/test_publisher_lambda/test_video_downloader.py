from unittest.mock import MagicMock, patch

import pytest

from aws.publisher_lambda.video_downloader import VideoDownloader
from aws.shared.exceptions import VideoDownloadError


class TestVideoDownloader:
    @patch("aws.publisher_lambda.video_downloader.boto3.client")
    def test_download_success(self, mock_boto, tmp_path):
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        dest = tmp_path / "video.mp4"
        downloader = VideoDownloader(region="us-east-1")
        result = downloader.download("bucket", "videos/test.mp4", dest)
        assert result == dest
        mock_s3.download_file.assert_called_once()

    @patch("aws.publisher_lambda.video_downloader.boto3.client")
    def test_download_failure_raises_error(self, mock_boto, tmp_path):
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        mock_s3.download_file.side_effect = Exception("S3 error")
        downloader = VideoDownloader(region="us-east-1")
        with pytest.raises(VideoDownloadError, match="S3 error"):
            downloader.download("bucket", "key", tmp_path / "video.mp4")
