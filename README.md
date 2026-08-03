# AI Auto-Publish Image In-House Server

Automated educational leadership content pipeline: generates AI videos via ComfyUI/Wan2.2 on a dedicated GPU worker, uploads to AWS S3, and publishes to Instagram, LinkedIn, and YouTube — all triggered on a weekly schedule.

## Deployment

- \$ ./scripts/deploy.sh

## In Macbook - To run the Controller locally in tmux

- To see/attach it in your terminal:
  tmux attach -t controller
  Detach (keep it running): Ctrl-b then d
  Stop it: attach and press Ctrl-c, or run tmux kill-session -t controller
- TO run new session: tmux new-session -d -s controller -c "$PWD" ".venv/bin/python -m macbook.controller.main"

## Architecture

```
EventBridge (Mon 10AM IST)
  → Orchestrator Lambda (RSS + Bedrock + Polly → S3 + MQTT)
  → MacBook Controller (MQTT sub → SSH → Kali GPU Worker)
  → Kali Worker (ComfyUI/Wan2.2 → FFmpeg → MP4)
  → MacBook (rsync → S3 upload → MQTT)
  → AWS IoT Rule → Publisher Lambda (Instagram + LinkedIn + YouTube)
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for full diagrams and data flow.

## Components

| Component               | Role                                                               | Tech                                                   |
| ----------------------- | ------------------------------------------------------------------ | ------------------------------------------------------ |
| **Orchestrator Lambda** | RSS crawl, Bedrock content gen, Polly TTS, S3 upload, MQTT publish | Python 3.13, boto3, feedparser                         |
| **MacBook Controller**  | MQTT subscribe, SSH orchestration, rsync, S3 operations            | Python 3.13, AWS IoT Device SDK v2                     |
| **Kali GPU Worker**     | ComfyUI video generation, FFmpeg audio merge                       | Python 3.13, urllib, subprocess (no boto3)             |
| **Publisher Lambda**    | Concurrent publish to 3 platforms                                  | Python 3.13, boto3, requests                           |
| **Terraform**           | Infrastructure as Code                                             | AWS EventBridge, Lambda, IoT Core, S3, Secrets Manager |

## Prerequisites

- Python 3.13+
- [Poetry](https://python-poetry.org/)
- AWS account with permissions for: Lambda, EventBridge, IoT Core, S3, Bedrock, Polly, Secrets Manager
- [Tailscale](https://tailscale.com/) on MacBook and Kali worker
- ComfyUI + Wan2.2 models installed on Kali worker (see [Deployment Guide](#deployment))
- Social media API credentials (Instagram Professional account, LinkedIn Company Page, YouTube Channel)

## Quick Start

```bash
# Install dependencies
make install

# Set up environment
cp .env.example .env
# Edit .env with your AWS config, IoT endpoint, worker host, etc.

# Run the MacBook Controller (long-running process)
make run-controller
```

## Deploy Infrastructure

```bash
# Build Lambda deployment packages
make build-lambdas

# Deploy with Terraform
make terraform-init
make terraform-plan
make terraform-apply
```

## Development

```bash
# Lint
make lint

# Type check
make typecheck

# Run tests with coverage
make coverage
```

## Project Structure

```
repo/
  aws/orchestrator_lambda/     # Event-driven content generation
  aws/publisher_lambda/        # Multi-platform social publishing
  aws/shared/                  # Shared AWS models, config, logging
  macbook/controller/          # Long-running control plane
  macbook/shared/              # MacBook models, config, exceptions
  kali/                        # GPU rendering worker (no AWS SDK)
  infrastructure/terraform/    # Infrastructure as Code
  tests/                       # pytest suite with >90% coverage
```

## Schedule

The pipeline runs **every Monday at 10:00 AM IST** (04:30 UTC) via EventBridge cron: `cron(30 4 ? * MON *)`.
