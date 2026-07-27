

class MacBookError(Exception):
    """Base MacBook controller error."""


class SSHExecutionError(MacBookError):
    def __init__(
        self,
        exit_code: int,
        stdout: str,
        stderr: str,
        command: list[str],
        elapsed_seconds: float,
    ) -> None:
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.command = command
        self.elapsed_seconds = elapsed_seconds
        super().__init__(
            f"SSH command failed (exit={exit_code}, elapsed={elapsed_seconds:.1f}s): "
            f"{' '.join(command)}"
        )


class WorkerTimeoutError(MacBookError):
    def __init__(self, command: list[str], timeout: int) -> None:
        self.command = command
        self.timeout = timeout
        super().__init__(f"SSH command timed out after {timeout}s: {' '.join(command)}")


class VideoTransferError(MacBookError):
    def __init__(self, command: list[str], exit_code: int, stderr: str) -> None:
        self.command = command
        self.exit_code = exit_code
        self.stderr = stderr
        super().__init__(
            f"Video transfer failed (exit={exit_code}): {' '.join(command)}"
        )


class MQTTConnectionError(MacBookError):
    """MQTT connection to AWS IoT Core failed."""


class S3OperationError(MacBookError):
    """S3 download or upload failed."""
