import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from kali.comfy_client import ComfyClient, WorkflowError
from kali.ffmpeg import FFmpegProcessor

_AWS_MODULES = {"boto3", "botocore", "s3fs", "awscli", "moto"}
for _mod in list(sys.modules.keys()):
    if any(forbidden in _mod for forbidden in _AWS_MODULES):
        raise RuntimeError(f"Forbidden AWS dependency detected: {_mod}")


def load_workflow(workflow_path: Path) -> dict[str, Any]:
    with workflow_path.open("r") as f:
        result: dict[str, Any] = json.load(f)
        return result


def inject_prompt(
    workflow: dict[str, Any],
    video_prompt: str,
    seed: int = 42,
    width: int = 720,
    height: int = 1280,
    length: int = 81,
) -> dict[str, Any]:
    modified: dict[str, Any] = json.loads(json.dumps(workflow))
    for _node_id, node in modified.items():
        inputs = node.get("inputs", {})
        has_text = "text" in inputs
        is_clip_node = "clip" in inputs or "CLIP" in str(node.get("class_type", ""))
        if has_text and not is_clip_node:
            inputs["text"] = video_prompt
        if "seed" in inputs:
            inputs["seed"] = seed
        if "width" in inputs:
            inputs["width"] = width
        if "height" in inputs:
            inputs["height"] = height
        if "length" in inputs:
            inputs["length"] = length
    return modified


def download_audio(voiceover_url: str, dest: Path, timeout: int = 120) -> Path:
    req = urllib.request.Request(voiceover_url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as src:
            dest.write_bytes(src.read())
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to download audio: {exc}") from exc
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description="Kali GPU Worker")
    parser.add_argument("--prompt-file", required=True, help="Path to prompt.json")
    parser.add_argument("--output", required=True, help="Output MP4 path")
    args = parser.parse_args()

    prompt_path = Path(args.prompt_file)
    output_path = Path(args.output)

    if not prompt_path.exists():
        print(f"ERROR: prompt file not found: {prompt_path}", file=sys.stderr)
        return 1

    with prompt_path.open("r") as f:
        prompt: dict[str, Any] = json.load(f)

    job_id = prompt.get("job_id", "unknown")
    video_prompt = prompt.get("video_prompt", "")
    voiceover_url = prompt.get("voiceover_url", "")

    if not video_prompt:
        print("ERROR: no video_prompt in prompt file", file=sys.stderr)
        return 1

    temp_dir = output_path.parent
    temp_dir.mkdir(parents=True, exist_ok=True)

    audio_path = temp_dir / f"{job_id}.mp3"
    if voiceover_url:
        try:
            download_audio(voiceover_url, audio_path)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    workflow_dir = Path(__file__).resolve().parent / "workflow"
    workflow_file = workflow_dir / "wan22.json"
    if not workflow_file.exists():
        print(f"ERROR: workflow file not found: {workflow_file}", file=sys.stderr)
        return 1

    workflow = load_workflow(workflow_file)
    workflow = inject_prompt(workflow, video_prompt)

    client = ComfyClient()
    try:
        prompt_id = client.submit_workflow(workflow)
        print(f"Workflow submitted: prompt_id={prompt_id}", file=sys.stderr)
    except Exception as exc:
        print(f"ERROR: failed to submit workflow: {exc}", file=sys.stderr)
        return 1

    try:
        result = client.wait_until_complete(prompt_id)
        print("Workflow completed", file=sys.stderr)
    except WorkflowError as exc:
        print(f"ERROR: workflow failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: workflow wait failed: {exc}", file=sys.stderr)
        return 1

    outputs = result.get("outputs", {})
    video_node_id = list(outputs.keys())[0] if outputs else ""
    if not video_node_id:
        print("ERROR: no outputs in workflow result", file=sys.stderr)
        return 1

    try:
        raw_video = client.download_video(prompt_id, video_node_id, temp_dir)
        print(f"Raw video downloaded: {raw_video}", file=sys.stderr)
    except Exception as exc:
        print(f"ERROR: failed to download video: {exc}", file=sys.stderr)
        return 1

    if voiceover_url and audio_path.exists():
        ffmpeg = FFmpegProcessor()
        try:
            ffmpeg.merge_audio(raw_video, audio_path, output_path)
            print(f"Audio merged: {output_path}", file=sys.stderr)
        except Exception as exc:
            print(f"ERROR: FFmpeg merge failed: {exc}", file=sys.stderr)
            return 1
    else:
        raw_video.rename(output_path)
        print(f"Output (no audio): {output_path}", file=sys.stderr)

    print(f"SUCCESS: {output_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
