# Deployment Runbook

End-to-end deployment of the AI Auto-Publish Image In-House Server for environment
**`prod`** in **`us-east-1`**. Three surfaces: AWS infrastructure (Terraform),
the Kali GPU worker (manual), and the MacBook controller (local process).

## Prerequisites

- AWS CLI authenticated with credentials that can create Lambda, EventBridge, IoT,
  S3, Secrets Manager, IAM, CloudWatch resources. Active region: `us-east-1`.
- Terraform `~> 1.9` (`terraform version`).
- Poetry with the `poetry-plugin-export` plugin:
  `poetry self add poetry-plugin-export`.
- Tailscale on both the MacBook and Kali worker.

---

## Phase 1 — AWS infrastructure

### 1. Build Lambda deployment packages

```bash
make build-lambdas
```

Produces `build/orchestrator.zip` and `build/publisher.zip`. Verify both exist:

```bash
ls -lh build/*.zip
```

### 2. Review / adjust tfvars

`infrastructure/terraform/terraform.tfvars` is gitignored. Confirm:

```hcl
aws_region          = "us-east-1"
environment         = "prod"
content_bucket_name = "ai-content-automation"   # → bucket ai-content-automation-prod
```

### 3. Init, plan, apply

```bash
make terraform-init
make terraform-plan
make terraform-apply -auto-approve
```

Capture the outputs you'll need later:

```bash
terraform output iot_endpoint      # for the MacBook .env
terraform output content_bucket    # for the MacBook .env
```

What gets created:
- S3 bucket `ai-content-automation-prod` (versioned, lifecycle, block public access)
- `ai-content-orchestrator-prod` and `ai-content-publisher-prod` Lambdas
- EventBridge weekly schedule `cron(30 4 ? * MON *)`
- IoT topic rule `image_completed_prod` → publisher Lambda
- IoT policy `macbook_controller_prod` for the MacBook SigV4 connection
- Secrets: `instagram-credentials-prod`, `linkedin-credentials-prod`, `youtube-credentials-prod`
- IAM roles/policies, CloudWatch log groups

### 4. Post-apply AWS console/CLI steps

**a) Enable the Bedrock model** (one-time, console):
Model access → `us.anthropic.claude-sonnet-4-5-20250929-v1:0` in us-east-1.
Without this the orchestrator fails at runtime.

**b) Populate Secrets Manager** (structures documented in `.env.example:38-46`):

```bash
aws secretsmanager put-secret-value \
  --secret-id instagram-credentials-prod \
  --secret-string '{"access_token":"...","ig_user_id":"..."}'

aws secretsmanager put-secret-value \
  --secret-id linkedin-credentials-prod \
  --secret-string '{"access_token":"...","organization_urn":"urn:li:organization:..."}'

aws secretsmanager put-secret-value \
  --secret-id youtube-credentials-prod \
  --secret-string '{"access_token":"...","refresh_token":"...","client_id":"...","client_secret":"..."}'
```

**c) Attach the IoT policy to the MacBook's IAM identity.**
Terraform cannot attach an IoT policy to an IAM principal, so do it once via CLI.
The MacBook authenticates with SigV4 over WebSocket MQTT, so its IAM user/role
(whatever credentials you put in the MacBook's `.env`) must carry this policy:

```bash
aws iot attach-policy \
  --policy-name macbook_controller_prod \
  --target <arn-of-the-macbook-iam-user-or-role>
```

The attached IAM identity also needs `iot:Connect`, `iot:Subscribe`, `iot:Receive`,
`iot:Publish` allowed in its own IAM policy to use the WebSocket endpoint.

---

## Phase 2 — Kali GPU Worker (one-time, manual)

1. Copy the `kali/` directory to `/home/worker/`:
   ```bash
   scp -r kali/ worker.tailnet.ts.net:/home/worker/
   ```
2. On the worker, install runtime deps (no AWS SDK allowed):
   ```bash
   python -m pip install pydantic>=2.0 tenacity>=8.0
   ```
3. Install ComfyUI with the Wan2.2 T2V 14B models and run it with the API enabled,
   e.g. `python main.py --listen 0.0.0.0 --enable-cors-header`.
4. Install ffmpeg (`sudo apt install ffmpeg` on Kali).
5. Ensure the worker is reachable from the MacBook: `ssh worker.tailnet.ts.net`.
6. Smoke test:
   ```bash
   python /home/worker/generate.py --prompt-file /tmp/test.json --output /tmp/test.mp4
   ```
   (`/tmp/test.json` must contain at least `{"video_prompt": "...", "job_id": "test"}`.)

---

## Phase 3 — MacBook Controller

```bash
cp .env.example .env
```

Fill in `.env`:
- `IOT_ENDPOINT` — from `terraform output iot_endpoint`
- `CONTENT_BUCKET` — from `terraform output content_bucket` (default `ai-content-automation-prod`)
- `AWS_REGION=us-east-1`, `AWS_PROFILE=<profile for the IoT-policy-attached identity>`
- `WORKER_SSH_HOST=worker.tailnet.ts.net`

Install and run persistently:

```bash
make install
make run-controller
```

Keep it running with launchd / `nohup` / `tmux` — it is a long-lived MQTT subscriber.
It will reject and drop jobs while busy.

---

## Phase 4 — Verify end-to-end

Trigger the orchestrator manually and watch the chain:

```bash
aws lambda invoke --function-name ai-content-orchestrator-prod \
  --payload '{}' /tmp/out.json && cat /tmp/out.json
```

Follow logs:

```bash
aws logs tail /aws/lambda/ai-content-orchestrator-prod --follow
aws logs tail /aws/lambda/ai-content-publisher-prod --follow
```

Success = orchestrator returns `200` with `job_id` → MacBook SSH-renders on Kali →
video uploaded to S3 `videos/{job_id}.mp4` → `image/completed` → IoT rule → publisher
posts to Instagram, LinkedIn, YouTube. Next automatic run: Monday 04:30 UTC.

---

## Rollback

```bash
make terraform-destroy
```

Secrets created with a 7-day recovery window must be deleted after the window or
with `--force-delete-without-recovery` before re-applying.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `terraform plan` errors on `job_queue_topic` | Stale state/deps — `terraform init -upgrade` |
| Orchestrator logs `AccessDeniedException` on Bedrock | Model not enabled (Phase 1 step 4a) |
| MacBook MQTT connect denied | IoT policy not attached to IAM identity (Phase 1 step 4c) |
| Worker SSH fails | Tailscale down, or `WORKER_SSH_HOST` wrong |
| Publisher skips a platform | Social API 429 or missing/invalid secret JSON |
