import subprocess
import time as time_module
from pathlib import Path

import tenacity

from macbook.shared.exceptions import VideoTransferError
from macbook.shared.logger import get_logger
from macbook.shared.models import VideoTransferResult

logger = get_logger("rsync_client")


class RsyncClient:
    def __init__(self, host: str, timeout: int = 300) -> None:
        self._host = host
        self._timeout = timeout

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=20),
        retry=tenacity.retry_if_exception_type(VideoTransferError),
    )
    def pull(self, remote_path: str, local_dir: str) -> VideoTransferResult:
        Path(local_dir).mkdir(parents=True, exist_ok=True)
        cmd: list[str] = [
            "rsync",
            "-av",
            "--progress",
            f"{self._host}:{remote_path}",
            f"{local_dir}/",
        ]
        start = time_module.monotonic()
        try:
            subprocess.run(
                cmd, check=True, capture_output=True, text=True, timeout=self._timeout
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            exit_code = getattr(exc, "returncode", -1)
            stderr = getattr(exc, "stderr", str(exc))
            raise VideoTransferError(cmd, exit_code, stderr) from exc

        elapsed = time_module.monotonic() - start
        local_path = Path(local_dir) / Path(remote_path).name
        size_bytes = local_path.stat().st_size if local_path.exists() else 0
        logger.info(
            "rsync pull completed",
            extra={
                "elapsed_seconds": round(elapsed, 1),
                "size_bytes": size_bytes,
                "local_path": str(local_path),
                "remote_path": remote_path,
            },
        )
        return VideoTransferResult(
            local_path=str(local_path),
            size_bytes=size_bytes,
            elapsed_seconds=elapsed,
        )

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=20),
        retry=tenacity.retry_if_exception_type(VideoTransferError),
    )
    def push(self, local_path: str, remote_dir: str) -> None:
        cmd: list[str] = [
            "rsync",
            "-av",
            local_path,
            f"{self._host}:{remote_dir}/",
        ]
        try:
            subprocess.run(
                cmd, check=True, capture_output=True, text=True, timeout=self._timeout
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            exit_code = getattr(exc, "returncode", -1)
            stderr = getattr(exc, "stderr", str(exc))
            raise VideoTransferError(cmd, exit_code, stderr) from exc

        logger.info(
            "rsync push completed",
            extra={"local_path": local_path, "remote_dir": remote_dir},
        )
