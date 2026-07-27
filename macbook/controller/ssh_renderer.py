import subprocess
import time
from pathlib import Path

from macbook.shared.config import MacBookConfig
from macbook.shared.exceptions import (
    SSHExecutionError,
    VideoTransferError,
    WorkerTimeoutError,
)
from macbook.shared.logger import get_logger
from macbook.shared.models import RenderResult, VideoTransferResult

logger = get_logger("ssh_renderer")


class SSHRenderer:
    def __init__(self, config: MacBookConfig) -> None:
        self._config = config
        self._host = config.worker_ssh_host

    def render(
        self,
        prompt_file: str,
        output_file: str,
        timeout: int | None = None,
    ) -> RenderResult:
        effective_timeout = timeout or self._config.ssh_timeout_seconds
        cmd: list[str] = [
            "caffeinate",
            "-dimsu",
            "--",
            "ssh",
            self._host,
            "python",
            self._config.worker_generate_script,
            "--prompt-file",
            prompt_file,
            "--output",
            output_file,
        ]
        logger.info(
            "Starting SSH render",
            extra={
                "command": " ".join(cmd),
                "timeout": effective_timeout,
                "worker": self._host,
            },
        )
        start = time.monotonic()
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed = time.monotonic() - start
            raise WorkerTimeoutError(cmd, effective_timeout) from exc
        except subprocess.CalledProcessError as exc:
            elapsed = time.monotonic() - start
            raise SSHExecutionError(
                exit_code=exc.returncode,
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
                command=cmd,
                elapsed_seconds=elapsed,
            ) from exc

        elapsed = time.monotonic() - start
        logger.info(
            "SSH render completed",
            extra={
                "exit_code": result.returncode,
                "elapsed_seconds": round(elapsed, 1),
                "worker": self._host,
            },
        )
        return RenderResult(
            exit_code=result.returncode,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            elapsed_seconds=elapsed,
            command=cmd,
        )

    def copy_video(
        self,
        remote_path: str,
        local_dir: str,
        timeout: int | None = None,
    ) -> VideoTransferResult:
        effective_timeout = timeout or self._config.rsync_timeout_seconds
        cmd: list[str] = [
            "rsync",
            "-av",
            f"{self._host}:{remote_path}",
            f"{local_dir}/",
        ]
        logger.info(
            "Starting rsync video transfer",
            extra={"command": " ".join(cmd), "worker": self._host},
        )
        start = time.monotonic()
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            exit_code = getattr(exc, "returncode", -1)
            stderr_data = getattr(exc, "stderr", str(exc))
            stderr_str = stderr_data.decode("utf-8") if isinstance(stderr_data, bytes) else str(stderr_data)
            raise VideoTransferError(cmd, exit_code, stderr_str) from exc

        elapsed = time.monotonic() - start
        local_path = Path(local_dir) / Path(remote_path).name
        size_bytes = local_path.stat().st_size if local_path.exists() else 0
        logger.info(
            "Video transfer completed",
            extra={
                "elapsed_seconds": round(elapsed, 1),
                "size_bytes": size_bytes,
                "local_path": str(local_path),
                "worker": self._host,
            },
        )
        return VideoTransferResult(
            local_path=str(local_path),
            size_bytes=size_bytes,
            elapsed_seconds=elapsed,
        )

    def copy_logs(
        self,
        remote_log_dir: str,
        local_log_dir: str,
        timeout: int | None = None,
    ) -> VideoTransferResult:
        effective_timeout = timeout or self._config.rsync_timeout_seconds
        cmd: list[str] = [
            "rsync",
            "-av",
            f"{self._host}:{remote_log_dir}/",
            f"{local_log_dir}/",
        ]
        start = time.monotonic()
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            exit_code = getattr(exc, "returncode", -1)
            stderr_data = getattr(exc, "stderr", str(exc))
            stderr_str = stderr_data.decode("utf-8") if isinstance(stderr_data, bytes) else str(stderr_data)
            raise VideoTransferError(cmd, exit_code, stderr_str) from exc

        elapsed = time.monotonic() - start
        local_log_path = Path(local_log_dir)
        size_bytes = (
            sum(f.stat().st_size for f in local_log_path.rglob("*") if f.is_file())
            if local_log_path.exists()
            else 0
        )
        return VideoTransferResult(
            local_path=str(local_log_path),
            size_bytes=size_bytes,
            elapsed_seconds=elapsed,
        )
