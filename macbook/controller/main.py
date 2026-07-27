import asyncio
import contextlib
import signal
from typing import Any

from macbook.controller.artifact_manager import ArtifactManager
from macbook.controller.completion_publisher import CompletionPublisher
from macbook.controller.mqtt_client import MQTTClient
from macbook.controller.rsync_client import RsyncClient
from macbook.controller.s3_client import S3Client
from macbook.controller.ssh_renderer import SSHRenderer
from macbook.controller.worker_manager import WorkerManager
from macbook.shared.config import MacBookConfig
from macbook.shared.logger import get_logger
from macbook.shared.models import GenerateEvent

logger = get_logger("macbook_controller")


class Controller:
    def __init__(self) -> None:
        self._config = MacBookConfig()
        self._mqtt = MQTTClient(self._config)
        self._ssh = SSHRenderer(self._config)
        self._rsync = RsyncClient(
            host=self._config.worker_ssh_host,
            timeout=self._config.rsync_timeout_seconds,
        )
        self._s3 = S3Client(region=self._config.aws_region)
        self._artifacts = ArtifactManager(
            artifact_dir=self._config.local_artifact_dir,
            log_dir=self._config.local_log_dir,
        )
        self._worker = WorkerManager(
            config=self._config,
            ssh_renderer=self._ssh,
            rsync=self._rsync,
            s3=self._s3,
            artifacts=self._artifacts,
        )
        self._publisher = CompletionPublisher(self._config, self._mqtt)
        self._job_in_progress: bool = False
        self._shutdown: bool = False

    async def _on_generate(self, payload: dict[str, Any]) -> None:
        if self._shutdown:
            return
        if self._job_in_progress:
            logger.warning(
                "Rejecting job — controller busy",
                extra={"job_id": payload.get("jobId", payload.get("job_id", "unknown"))},
            )
            return

        self._job_in_progress = True
        event = GenerateEvent(**payload)
        try:
            result = await self._worker.process(event)
            await self._publisher.publish(
                job_id=result["job_id"],
                bucket=result["bucket"],
                video_key=result["video_key"],
            )
        except Exception as exc:
            logger.exception(
                "Job failed",
                extra={"job_id": event.job_id, "error": str(exc)},
            )
        finally:
            self._job_in_progress = False

    async def run(self) -> None:
        logger.info("MacBook Controller starting")
        self._artifacts.ensure_dirs()

        await self._mqtt.connect()
        await self._mqtt.subscribe(
            self._config.job_queue_topic,
            self._on_generate,
        )

        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(
                    sig, lambda: asyncio.ensure_future(self._shutdown_handler())
                )

        logger.info("MacBook Controller ready, waiting for jobs")
        while not self._shutdown:
            await asyncio.sleep(1)

    async def _shutdown_handler(self) -> None:
        self._shutdown = True
        logger.info("Shutdown requested")
        await self._mqtt.disconnect()


def main() -> None:
    controller = Controller()
    asyncio.run(controller.run())


if __name__ == "__main__":
    main()
