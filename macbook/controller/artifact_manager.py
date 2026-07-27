import shutil
from pathlib import Path

from macbook.shared.logger import get_logger

logger = get_logger("artifact_manager")


class ArtifactManager:
    def __init__(self, artifact_dir: str = "./artifacts", log_dir: str = "./logs") -> None:
        self._artifact_dir = Path(artifact_dir)
        self._log_dir = Path(log_dir)

    def ensure_dirs(self) -> None:
        self._artifact_dir.mkdir(parents=True, exist_ok=True)
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def get_artifact_path(self, job_id: str) -> Path:
        return self._artifact_dir / f"{job_id}.mp4"

    def get_log_path(self, job_id: str) -> Path:
        path = self._log_dir / job_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def cleanup_artifact(self, job_id: str) -> None:
        path = self.get_artifact_path(job_id)
        if path.exists():
            path.unlink()
            logger.debug("Cleaned up artifact", extra={"job_id": job_id, "path": str(path)})

    def cleanup_logs(self, job_id: str) -> None:
        path = self.get_log_path(job_id)
        if path.exists():
            shutil.rmtree(path)
            logger.debug("Cleaned up logs", extra={"job_id": job_id, "path": str(path)})

    def list_existing_artifacts(self) -> list[str]:
        if not self._artifact_dir.exists():
            return []
        return [
            f.stem for f in self._artifact_dir.iterdir() if f.suffix == ".mp4"
        ]
