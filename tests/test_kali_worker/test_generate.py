import json
from unittest.mock import MagicMock, patch

import pytest

from kali.generate import (
    download_audio,
    inject_prompt,
    load_workflow,
    main,
)


class TestGenerate:
    def test_load_workflow(self, tmp_path, sample_workflow):
        wf = tmp_path / "workflow.json"
        wf.write_text(json.dumps(sample_workflow))
        result = load_workflow(wf)
        assert "1" in result
        assert result["1"]["class_type"] == "LoadDiffusionModel"

    def test_inject_prompt_replaces_text(self, sample_workflow):
        result = inject_prompt(
            sample_workflow,
            video_prompt="A new prompt",
            seed=99,
            width=720,
            height=1280,
            length=81,
        )
        assert result["5"]["inputs"]["text"] == "A new prompt"

    def test_inject_prompt_sets_seed(self, sample_workflow):
        result = inject_prompt(sample_workflow, video_prompt="test", seed=42)
        assert result.get("9", {}).get("inputs", {}).get("seed") != 42  # no seed node in sample
        # Test with a workflow that has seed
        wf_with_seed = {
            "1": {"class_type": "KSamplerAdvanced", "inputs": {"seed": 0}}
        }
        result2 = inject_prompt(wf_with_seed, video_prompt="test", seed=77)
        assert result2["1"]["inputs"]["seed"] == 77

    def test_inject_prompt_sets_dimensions(self, sample_workflow):
        result = inject_prompt(
            sample_workflow,
            video_prompt="test",
            width=320,
            height=640,
            length=41,
        )
        assert result["7"]["inputs"]["width"] == 320
        assert result["7"]["inputs"]["height"] == 640
        assert result["7"]["inputs"]["length"] == 41

    def test_download_audio_success(self, tmp_path):
        dest = tmp_path / "audio.mp3"
        with patch("urllib.request.urlopen") as mock_get:
            mock_response = MagicMock()
            mock_response.read.return_value = b"audio-data"
            mock_get.return_value.__enter__.return_value = mock_response
            result = download_audio("https://example.com/audio.mp3", dest)
        assert result.read_bytes() == b"audio-data"

    def test_download_audio_failure(self, tmp_path):
        from urllib.error import URLError
        dest = tmp_path / "audio.mp3"
        with patch(
            "urllib.request.urlopen",
            side_effect=URLError("Timeout"),
        ), pytest.raises(RuntimeError, match="Failed to download audio"):
            download_audio("https://example.com/audio.mp3", dest)

    def test_main_missing_prompt_file(self, tmp_path):
        prompt_file = str(tmp_path / "nonexistent.json")
        output_file = str(tmp_path / "out.mp4")
        test_args = ["generate.py", "--prompt-file", prompt_file, "--output", output_file]
        with patch("sys.argv", test_args):
            result = main()
        assert result == 1
