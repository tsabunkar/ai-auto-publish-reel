import subprocess
from unittest.mock import MagicMock, patch

import pytest

from macbook.controller.ssh_renderer import SSHRenderer
from macbook.shared.config import MacBookConfig
from macbook.shared.exceptions import SSHExecutionError, WorkerTimeoutError


@pytest.fixture
def config():
    cfg = MagicMock(spec=MacBookConfig)
    cfg.worker_ssh_host = "worker.test"
    cfg.worker_generate_script = "/home/worker/generate.py"
    cfg.ssh_timeout_seconds = 3600
    cfg.rsync_timeout_seconds = 300
    return cfg


class TestSSHRenderer:
    def test_render_success(self, config):
        renderer = SSHRenderer(config)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="SUCCESS", stderr=""
            )
            result = renderer.render(
                prompt_file="/tmp/prompt.json",
                output_file="/tmp/output.mp4",
            )
        assert result.exit_code == 0
        assert "SUCCESS" in result.stdout
        assert "caffeinate" in result.command[0]

    def test_render_timeout(self, config):
        renderer = SSHRenderer(config)
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 10)), pytest.raises(WorkerTimeoutError, match="timed out"):
                renderer.render("/tmp/prompt.json", "/tmp/output.mp4", timeout=10)

    def test_render_non_zero_exit(self, config):
        renderer = SSHRenderer(config)
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "ssh", stdout="", stderr="Error occurred"
            )
            with pytest.raises(SSHExecutionError, match="non-zero"):
                renderer.render("/tmp/prompt.json", "/tmp/output.mp4")

    def test_copy_video_success(self, config, tmp_path):
        renderer = SSHRenderer(config)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            (tmp_path / "artifacts").mkdir()
            result = renderer.copy_video(
                remote_path="/tmp/output.mp4",
                local_dir=str(tmp_path / "artifacts"),
            )
        assert result.size_bytes == 0

    def test_copy_video_failure(self, config):
        renderer = SSHRenderer(config)
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(
            1, "rsync", stderr="Connection refused"
        )), pytest.raises(SSHExecutionError):
            renderer.copy_video("/tmp/output.mp4", "./artifacts")
