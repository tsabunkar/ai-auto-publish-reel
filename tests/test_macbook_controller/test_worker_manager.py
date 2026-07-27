from unittest.mock import AsyncMock, MagicMock

import pytest

from macbook.controller.worker_manager import WorkerManager
from macbook.shared.models import GenerateEvent


@pytest.fixture
def config():
    cfg = MagicMock()
    cfg.worker_prompt_dir = "/tmp"
    cfg.worker_output_dir = "/tmp"
    cfg.local_artifact_dir = "./artifacts"
    cfg.local_log_dir = "./logs"
    cfg.worker_log_dir = "/home/worker/logs"
    cfg.ssh_timeout_seconds = 3600
    cfg.rsync_timeout_seconds = 300
    return cfg


class TestWorkerManager:
    @pytest.mark.asyncio
    async def test_process_success(self, config):
        ssh_renderer = AsyncMock()
        rsync = MagicMock()
        rsync.pull.return_value = MagicMock(
            local_path="./artifacts/output.mp4", size_bytes=1000, elapsed_seconds=10.0
        )
        s3 = MagicMock()
        s3.download_json.return_value = {"job_id": "j1", "title": "Test"}
        artifacts = MagicMock()

        manager = WorkerManager(config, ssh_renderer, rsync, s3, artifacts)
        event = GenerateEvent(job_id="j1", bucket="b1", prompt_key="prompts/j1.json")

        result = await manager.process(event)
        assert result["job_id"] == "j1"
        assert "video_key" in result

    @pytest.mark.asyncio
    async def test_process_ssh_failure(self, config):
        from macbook.shared.exceptions import SSHExecutionError

        ssh_renderer = AsyncMock()
        ssh_renderer.render.side_effect = SSHExecutionError(
            1, "", "error", ["ssh"], 5.0
        )
        rsync = MagicMock()
        s3 = MagicMock()
        s3.download_json.return_value = {"job_id": "j1"}
        artifacts = MagicMock()

        manager = WorkerManager(config, ssh_renderer, rsync, s3, artifacts)
        event = GenerateEvent(job_id="j1", bucket="b1", prompt_key="prompts/j1.json")

        with pytest.raises(SSHExecutionError):
            await manager.process(event)
