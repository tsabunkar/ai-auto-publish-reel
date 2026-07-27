import json
import time
from pathlib import Path
from typing import Any

from macbook.controller.artifact_manager import ArtifactManager
from macbook.controller.rsync_client import RsyncClient
from macbook.controller.s3_client import S3Client
from macbook.controller.ssh_renderer import SSHRenderer
from macbook.shared.config import MacBookConfig
from macbook.shared.exceptions import (
    S3OperationError,
    SSHExecutionError,
    VideoTransferError,
    WorkerTimeoutError,
)
from macbook.shared.logger import get_logger
from macbook.shared.models import GenerateEvent

logger = get_logger("worker_manager")


class WorkerManager:
    def __init__(
        self,
        config: MacBookConfig,
        ssh_renderer: SSHRenderer,
        rsync: RsyncClient,
        s3: S3Client,
        artifacts: ArtifactManager,
    ) -> None:
        self._config = config
        self._ssh = ssh_renderer
        self._rsync = rsync
        self._s3 = s3
        self._artifacts = artifacts

    async def process(self, event: GenerateEvent) -> dict[str, Any]:
        job_id = event.job_id
        bucket = event.bucket
        prompt_key = event.prompt_key

        logger.info(
            "Processing job",
            extra={
                "job_id": job_id,
                "bucket": bucket,
                "prompt_key": prompt_key,
            },
        )

        self._artifacts.ensure_dirs()
        start_time = time.monotonic()

        try:
            prompt_data = self._download_prompt(bucket, prompt_key)
            remote_prompt_path = self._rsync_prompt_to_worker(job_id, prompt_data)
            remote_output_path = f"{self._config.worker_output_dir}/{job_id}.mp4"
            self._ssh.render(
                prompt_file=remote_prompt_path,
                output_file=remote_output_path,
            )
            transfer_result = self._rsync.pull(
                remote_output_path,
                self._config.local_artifact_dir,
            )
            self._copy_worker_logs(job_id)
            video_key = self._upload_video(
                job_id, bucket, transfer_result.local_path
            )
            self._cleanup(job_id)

            elapsed = time.monotonic() - start_time
            logger.info(
                "Job completed",
                extra={
                    "job_id": job_id,
                    "elapsed_seconds": round(elapsed, 1),
                    "video_key": video_key,
                    "size_bytes": transfer_result.size_bytes,
                },
            )
            return {
                "job_id": job_id,
                "bucket": bucket,
                "video_key": video_key,
            }

        except (SSHExecutionError, WorkerTimeoutError) as exc:
            self._copy_worker_logs(job_id)
            logger.error(
                "Worker execution failed",
                extra={
                    "job_id": job_id,
                    "error": str(exc),
                    "elapsed_seconds": round(time.monotonic() - start_time, 1),
                },
            )
            raise

        except (S3OperationError, VideoTransferError) as exc:
            logger.error(
                "Infrastructure error during job",
                extra={
                    "job_id": job_id,
                    "error": str(exc),
                    "elapsed_seconds": round(time.monotonic() - start_time, 1),
                },
            )
            raise

    def _download_prompt(self, bucket: str, prompt_key: str) -> dict[str, Any]:
        return self._s3.download_json(bucket, prompt_key)

    def _rsync_prompt_to_worker(self, job_id: str, prompt_data: dict[str, Any]) -> str:
        local_prompt = self._artifacts.get_artifact_path(job_id).with_suffix(".json")
        local_prompt.parent.mkdir(parents=True, exist_ok=True)
        local_prompt.write_text(json.dumps(prompt_data, default=str))
        remote_dir = self._config.worker_prompt_dir
        self._rsync.push(str(local_prompt), remote_dir)
        return f"{remote_dir}/{local_prompt.name}"

    def _copy_worker_logs(self, job_id: str) -> None:
        try:
            local_log_dir = str(self._artifacts.get_log_path(job_id))
            self._ssh.copy_logs(
                self._config.worker_log_dir,
                local_log_dir,
                timeout=60,
            )
        except VideoTransferError as exc:
            logger.warning(
                "Failed to copy worker logs",
                extra={"job_id": job_id, "error": str(exc)},
            )

    def _upload_video(
        self, job_id: str, bucket: str, local_path: str
    ) -> str:
        video_key = f"videos/{job_id}.mp4"
        self._s3.upload_file(
            bucket=bucket,
            key=video_key,
            file_path=Path(local_path),
        )
        return video_key

    def _cleanup(self, job_id: str) -> None:
        self._artifacts.cleanup_artifact(job_id)
