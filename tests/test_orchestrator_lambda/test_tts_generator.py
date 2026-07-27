import io
from unittest.mock import MagicMock, patch

import pytest

from aws.orchestrator_lambda.tts_generator import TTSGenerator
from aws.shared.exceptions import TTSGenerationError


class TestTTSGenerator:
    @patch("aws.orchestrator_lambda.tts_generator.boto3.client")
    def test_synthesize_returns_path(self, mock_boto, tmp_path):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.synthesize_speech.return_value = {
            "AudioStream": io.BytesIO(b"fake-audio-data")
        }
        tts = TTSGenerator(voice_id="Matthew", region="us-east-1")
        output = tmp_path / "test.mp3"
        result = tts.synthesize("Hello world", output)
        assert result == output
        assert output.read_bytes() == b"fake-audio-data"

    @patch("aws.orchestrator_lambda.tts_generator.boto3.client")
    def test_synthesize_truncates_long_text(self, mock_boto, tmp_path):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.synthesize_speech.return_value = {
            "AudioStream": io.BytesIO(b"data")
        }
        tts = TTSGenerator(voice_id="Matthew", region="us-east-1")
        long_text = "x" * 5000
        output = tmp_path / "test.mp3"
        tts.synthesize(long_text, output)
        called_text = mock_client.synthesize_speech.call_args[1]["Text"]
        assert len(called_text) <= 3000

    @patch("aws.orchestrator_lambda.tts_generator.boto3.client")
    def test_synthesize_api_error(self, mock_boto, tmp_path):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.synthesize_speech.side_effect = Exception("Polly error")
        tts = TTSGenerator(voice_id="Matthew", region="us-east-1")
        with pytest.raises(TTSGenerationError, match="Polly error"):
            tts.synthesize("Hello", tmp_path / "test.mp3")

    @patch("aws.orchestrator_lambda.tts_generator.boto3.client")
    def test_synthesize_no_audio_stream(self, mock_boto, tmp_path):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.synthesize_speech.return_value = {}
        tts = TTSGenerator(voice_id="Matthew", region="us-east-1")
        with pytest.raises(TTSGenerationError, match="No AudioStream"):
            tts.synthesize("Hello", tmp_path / "test.mp3")
