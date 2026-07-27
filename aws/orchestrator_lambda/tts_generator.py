from pathlib import Path

import boto3
import tenacity

from aws.shared.exceptions import TTSGenerationError


class TTSGenerator:
    def __init__(self, voice_id: str, region: str = "us-east-1") -> None:
        self._voice_id = voice_id
        self._client = boto3.client("polly", region_name=region)

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(2),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type(TTSGenerationError),
        reraise=True,
    )
    def synthesize(self, text: str, output_path: Path) -> Path:
        max_chars = 3000
        if len(text) > max_chars:
            text = text[:max_chars]
        try:
            resp = self._client.synthesize_speech(
                Engine="neural",
                LanguageCode="en-US",
                OutputFormat="mp3",
                Text=text,
                VoiceId=self._voice_id,
            )
        except Exception as exc:
            raise TTSGenerationError(f"Polly synthesis failed: {exc}") from exc

        audio_stream = resp.get("AudioStream")
        if audio_stream is None:
            raise TTSGenerationError("No AudioStream in Polly response")

        output_path.write_bytes(audio_stream.read())
        return output_path
