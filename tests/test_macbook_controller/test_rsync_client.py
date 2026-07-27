import subprocess
from unittest.mock import MagicMock, patch

import pytest

from macbook.controller.rsync_client import RsyncClient
from macbook.shared.exceptions import VideoTransferError


class TestRsyncClient:
    def test_pull_success(self, tmp_path):
        client = RsyncClient(host="worker.test", timeout=30)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            (tmp_path / "output.mp4").write_text("test")
            result = client.pull(
                remote_path="/tmp/output.mp4",
                local_dir=str(tmp_path),
            )
        assert result.local_path.endswith(".mp4")

    def test_pull_failure(self):
        client = RsyncClient(host="worker.test", timeout=30)
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(
            1, "rsync", stderr="error"
        )), pytest.raises(VideoTransferError):
            client.pull("/tmp/output.mp4", "/tmp/artifacts")

    def test_pull_timeout(self):
        client = RsyncClient(host="worker.test", timeout=1)
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("rsync", 1)), pytest.raises(VideoTransferError):
                client.pull("/tmp/output.mp4", "/tmp/artifacts")

    def test_push_success(self, tmp_path):
        client = RsyncClient(host="worker.test", timeout=30)
        local_file = tmp_path / "test.txt"
        local_file.write_text("data")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            client.push(str(local_file), "/tmp")
        mock_run.assert_called_once()
