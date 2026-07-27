import subprocess
from pathlib import Path


class FFmpegError(Exception):
    """FFmpeg processing failed."""


class FFmpegProcessor:
    def __init__(self, ffmpeg_path: str = "ffmpeg") -> None:
        self._ffmpeg = ffmpeg_path

    def merge_audio(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
    ) -> Path:
        if not video_path.exists():
            raise FFmpegError(f"Video file not found: {video_path}")
        if not audio_path.exists():
            raise FFmpegError(f"Audio file not found: {audio_path}")
        cmd: list[str] = [
            self._ffmpeg,
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            "-y",
            str(output_path),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            raise FFmpegError(
                f"FFmpeg failed (exit={result.returncode}): {result.stderr}"
            )
        if not output_path.exists():
            raise FFmpegError(f"Output file was not created: {output_path}")
        return output_path
