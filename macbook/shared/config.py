from pydantic_settings import BaseSettings


class MacBookConfig(BaseSettings):
    model_config = {"env_prefix": "", "case_sensitive": False}

    aws_region: str = "us-east-1"
    iot_endpoint: str = ""
    content_bucket: str = ""
    job_queue_topic: str = "image/generate"
    completion_topic: str = "image/completed"
    worker_ssh_host: str = "worker.tailnet.ts.net"
    worker_generate_script: str = "/home/worker/generate.py"
    worker_prompt_dir: str = "/tmp"
    worker_output_dir: str = "/tmp"
    worker_log_dir: str = "/home/worker/logs"
    local_artifact_dir: str = "./artifacts"
    local_log_dir: str = "./logs"
    ssh_timeout_seconds: int = 3600
    rsync_timeout_seconds: int = 300
