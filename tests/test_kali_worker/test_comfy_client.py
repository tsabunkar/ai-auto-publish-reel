import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest

from kali.comfy_client import ComfyClient, ComfyUIError, WorkflowError


class TestComfyClient:
    def test_submit_workflow_success(self):
        client = ComfyClient(base_url="http://localhost:8188")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"prompt_id": "abc-123"}
            ).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_response

            prompt_id = client.submit_workflow({"1": {"class_type": "Test"}})
        assert prompt_id == "abc-123"

    def test_submit_workflow_missing_prompt_id(self):
        client = ComfyClient(base_url="http://localhost:8188")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({}).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_response

            with pytest.raises(ComfyUIError, match="Unexpected response"):
                client.submit_workflow({"1": {"class_type": "Test"}})

    def test_submit_workflow_network_error(self):
        client = ComfyClient(base_url="http://localhost:8188")
        with patch(
            "urllib.request.urlopen",
            side_effect=URLError("Connection refused"),
        ), pytest.raises(ComfyUIError, match="Failed to submit"):
            client.submit_workflow({"1": {"class_type": "Test"}})

    def test_wait_until_complete_success(self):
        client = ComfyClient(base_url="http://localhost:8188")
        with patch.object(client, "_get_history") as mock_history:
            mock_history.side_effect = [
                None,
                None,
                {"outputs": {"1": {"images": [{"filename": "out.png"}]}}},
            ]
            result = client.wait_until_complete(
                "abc-123", poll_interval=0.01, timeout=10
            )
        assert "outputs" in result

    def test_wait_until_complete_timeout(self):
        client = ComfyClient(base_url="http://localhost:8188")
        with patch.object(client, "_get_history", return_value=None), pytest.raises(ComfyUIError, match="did not complete"):
                client.wait_until_complete(
                    "abc-123", poll_interval=0.01, timeout=0.1
                )

    def test_wait_until_complete_workflow_error(self):
        client = ComfyClient(base_url="http://localhost:8188")
        with patch.object(client, "_get_history") as mock_history:
            mock_history.side_effect = [
                None,
                {"error": {"message": "CUDA out of memory"}},
            ]
            with pytest.raises(WorkflowError, match="CUDA out of memory"):
                client.wait_until_complete(
                    "abc-123", poll_interval=0.01, timeout=10
                )

    def test_download_video_success(self, tmp_path):
        client = ComfyClient(base_url="http://localhost:8188")
        with patch.object(client, "_get_history") as mock_history:
            mock_history.return_value = {
                "outputs": {
                    "1": {
                        "images": [
                            {"filename": "output.mp4", "subfolder": ""}
                        ]
                    }
                }
            }
            with patch("urllib.request.urlopen") as mock_dl:
                mock_response = MagicMock()
                mock_response.read.return_value = b"video-data"
                mock_dl.return_value.__enter__.return_value = mock_response

                result = client.download_video("abc-123", "1", tmp_path)
        assert result.exists()
        assert result.read_bytes() == b"video-data"

    def test_download_video_no_images(self):
        client = ComfyClient(base_url="http://localhost:8188")
        with patch.object(client, "_get_history") as mock_history:
            mock_history.return_value = {
                "outputs": {"1": {"images": []}}
            }
            with pytest.raises(ComfyUIError, match="No images"):
                client.download_video("abc-123", "1", Path("/tmp"))
