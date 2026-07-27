from unittest.mock import MagicMock, patch

from aws.publisher_lambda.handler import handler


class TestPublisherHandler:
    @patch("aws.publisher_lambda.handler._get_secret")
    @patch("aws.publisher_lambda.handler.VideoDownloader")
    @patch("aws.publisher_lambda.handler.boto3.client")
    def test_handler_success(
        self, mock_boto, mock_downloader_cls, mock_get_secret
    ):
        mock_downloader = MagicMock()
        mock_downloader_cls.return_value = mock_downloader

        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = "https://presigned.url"
        mock_boto.return_value = mock_s3

        mock_get_secret.side_effect = [
            {"access_token": "ig-token", "ig_user_id": "123"},
            {"access_token": "li-token", "organization_urn": "urn:li:org:1"},
            {
                "access_token": "yt-token",
                "refresh_token": "rt",
                "client_id": "cid",
                "client_secret": "csecret",
            },
        ]

        with patch(
            "aws.publisher_lambda.handler.PublisherConfig"
        ) as mock_config:
            mock_config.return_value.aws_region = "us-east-1"
            mock_config.return_value.content_bucket = "test-bucket"
            mock_config.return_value.instagram_secret_id = "ig-secret"
            mock_config.return_value.linkedin_secret_id = "li-secret"
            mock_config.return_value.youtube_secret_id = "yt-secret"

            event = {
                "jobId": "test-job",
                "bucket": "test-bucket",
                "videoKey": "videos/test.mp4",
            }
            result = handler(event, None)

        assert result["statusCode"] in (200, 207)

    def test_handler_missing_videokey(self):
        result = handler(
            {"jobId": "test-job", "bucket": "test-bucket"}, None
        )
        assert result["statusCode"] == 400
