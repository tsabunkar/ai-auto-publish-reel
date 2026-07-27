from unittest.mock import MagicMock, patch

import pytest

from kali.ffmpeg import FFmpegError, FFmpegProcessor


class TestFFmpegProcessor:
    def test_merge_audio_success(self, tmp_path):
        video = tmp_path / "input.mp4"
        video.write_text("video-data")
        audio = tmp_path / "input.mp3"
        audio.write_text("audio-data")
        output = tmp_path / "output.mp4"

        processor = FFmpegProcessor()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            output.write_text("merged-data")
            result = processor.merge_audio(video, audio, output)
        assert result == output

    def test_merge_audio_missing_video(self, tmp_path):
        processor = FFmpegProcessor()
        with pytest.raises(FFmpegError, match="Video file not found"):
            processor.merge_audio(
                tmp_path / "missing.mp4",
                tmp_path / "audio.mp3",
                tmp_path / "out.mp4",
            )

    def test_merge_audio_missing_audio(self, tmp_path):
        video = tmp_path / "input.mp4"
        video.write_text("data")
        processor = FFmpegProcessor()
        with pytest.raises(FFmpegError, match="Audio file not found"):
            processor.merge_audio(
                video,
                tmp_path / "missing.mp3",
                tmp_path / "out.mp4",
            )

    def test_merge_audio_ffmpeg_fails(self, tmp_path):
        video = tmp_path / "input.mp4"
        video.write_text("data")
        audio = tmp_path / "input.mp3"
        audio.write_text("data")
        output = tmp_path / "output.mp4"

        processor = FFmpegProcessor()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout="", stderr="FFmpeg error"
            )
            with pytest.raises(FFmpegError, match="FFmpeg failed"):
                processor.merge_audio(video, audio, output)

    def test_merge_audio_output_not_created(self, tmp_path):
        video = tmp_path / "input.mp4"
        video.write_text("data")
        audio = tmp_path / "input.mp3"
        audio.write_text("data")
        output = tmp_path / "output.mp4"

        processor = FFmpegProcessor()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            with pytest.raises(FFmpegError, match="was not created"):
                processor.merge_audio(video, audio, output)
