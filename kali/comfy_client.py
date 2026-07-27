import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import tenacity


class ComfyUIError(Exception):
    """ComfyUI API call failed."""


class WorkflowError(ComfyUIError):
    """Workflow execution failed with an error."""


class ComfyClient:
    def __init__(self, base_url: str = "http://localhost:8188") -> None:
        self.base_url = base_url.rstrip("/")
        self._client_id = str(uuid4())

    def submit_workflow(self, workflow: dict[str, Any]) -> str:
        payload = json.dumps(
            {"prompt": workflow, "client_id": self._client_id}
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/prompt",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ComfyUIError(f"Failed to submit workflow: {exc}") from exc
        if "prompt_id" not in body:
            raise ComfyUIError(f"Unexpected response: {body}")
        return str(body["prompt_id"])

    def wait_until_complete(
        self, prompt_id: str, poll_interval: int = 5, timeout: int = 600
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = self._get_history(prompt_id)
            if result is not None:
                if "error" in result:
                    err = result["error"]
                    raise WorkflowError(
                        f"Workflow failed: {err.get('message', err)}"
                    )
                return result
            time.sleep(poll_interval)
        raise ComfyUIError(
            f"Workflow {prompt_id} did not complete within {timeout}s"
        )

    def _get_history(self, prompt_id: str) -> dict[str, Any] | None:
        req = urllib.request.Request(f"{self.base_url}/history/{prompt_id}")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError:
            return None
        return cast(dict[str, Any] | None, body.get(prompt_id))

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type(ComfyUIError),
    )
    def download_video(
        self, prompt_id: str, node_id: str, output_dir: Path
    ) -> Path:
        history = self._get_history(prompt_id)
        if history is None:
            raise ComfyUIError(f"No history for {prompt_id}")
        outputs = history.get("outputs", {})
        node_output = outputs.get(node_id, {})
        images = node_output.get("images", [])
        if not images:
            raise ComfyUIError(f"No images in output for node {node_id}")
        image = images[0]
        filename = image["filename"]
        subfolder = image.get("subfolder", "")
        download_url = (
            f"{self.base_url}/view?filename={filename}"
            f"&subfolder={subfolder}&type=output"
        )
        dest = output_dir / filename
        req = urllib.request.Request(download_url)
        try:
            with urllib.request.urlopen(req, timeout=300) as src:
                dest.write_bytes(src.read())
        except urllib.error.URLError as exc:
            raise ComfyUIError(f"Failed to download video: {exc}") from exc
        return Path(dest)
