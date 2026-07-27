from unittest.mock import MagicMock, patch

from aws.orchestrator_lambda.handler import _build_content, _create_audio, handler


class TestHandler:
    @patch("aws.orchestrator_lambda.handler.TopicCrawler")
    @patch("aws.orchestrator_lambda.handler.ContentGenerator")
    @patch("aws.orchestrator_lambda.handler.TTSGenerator")
    @patch("aws.orchestrator_lambda.handler.PromptWriter")
    @patch("aws.orchestrator_lambda.handler.EventPublisher")
    def test_handler_success(
        self,
        mock_publisher_cls,
        mock_writer_cls,
        mock_tts_cls,
        mock_gen_cls,
        mock_crawler_cls,
        bedrock_response,
    ):
        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = ["Topic 1"]
        mock_crawler_cls.return_value = mock_crawler

        mock_gen = MagicMock()
        mock_gen.generate.return_value = bedrock_response
        mock_gen_cls.return_value = mock_gen

        mock_writer = MagicMock()
        mock_writer.write_prompt.return_value = "prompts/test.json"
        mock_writer.upload_audio.return_value = "audio/test.mp3"
        mock_writer.generate_presigned_url.return_value = "https://presigned.url"
        mock_writer_cls.return_value = mock_writer

        mock_tts = MagicMock()
        mock_tts.synthesize.return_value = "/tmp/test.mp3"
        mock_tts_cls.return_value = mock_tts

        mock_publisher = MagicMock()
        mock_publisher_cls.return_value = mock_publisher

        with patch(
            "aws.orchestrator_lambda.handler.OrchestratorConfig"
        ) as mock_config:
            mock_config.return_value.content_bucket = "test-bucket"
            mock_config.return_value.rss_feed_urls = "https://feed.com"
            mock_config.return_value.bedrock_model_id = "test-model"
            mock_config.return_value.polly_voice_id = "Matthew"
            mock_config.return_value.job_queue_topic = "reel/generate"
            mock_config.return_value.aws_region = "us-east-1"

            result = handler({}, None)

        assert result["statusCode"] == 200
        assert "jobId" in result["body"] or "job_id" in result["body"]

    def test_build_content(self):
        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = ["Topic 1"]
        mock_generator = MagicMock()
        mock_generator.generate.return_value = {"title": "Test"}
        result = _build_content(mock_crawler, mock_generator, "https://feed1.com,https://feed2.com")
        assert result["title"] == "Test"
        mock_crawler.crawl.assert_called_once()

    def test_create_audio(self, tmp_path):
        mock_tts = MagicMock()
        mock_tts.synthesize.return_value = str(tmp_path / "audio.mp3")
        result = _create_audio(mock_tts, "Hello", str(tmp_path), "job-123")
        assert result == str(tmp_path / "job-123.mp3")
        mock_tts.synthesize.assert_called_once()
