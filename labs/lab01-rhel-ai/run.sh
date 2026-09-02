#!/usr/bin/env bash
# Lab 01 — Serve a model inside your boundary (Red Hat AI Inference Server)
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../bin/lib.sh"

LAB_STEPS_TOTAL=5
RHAIIS_IMAGE="${RHAIIS_IMAGE:-registry.redhat.io/rhaiis/vllm-cuda-rhel9:3.2}"
MODEL_REPO="${MODEL_REPO:-RedHatAI/granite-3.3-8b-instruct}"
MODEL_PATH="${MODEL_PATH:-/var/models/granite-3.3-8b-instruct}"

require_cmd podman huggingface-cli curl jq

lab_header "01" "Serve a model inside your boundary" "Red Hat AI Inference Server"

lab_note "Goal: a supported LLM answering agency questions on hardware you control."
lab_note "Nothing in this lab makes an inference call off this host."

lab_section "1. Pull the signed inference server image"
step "podman pull $RHAIIS_IMAGE" <<'OUT'
Trying to pull registry.redhat.io/rhaiis/vllm-cuda-rhel9:3.2 ...
  Getting image source signatures
  Signature verified — policy: signedBy release key
  Copying blob 3f0c41a9 done   |   Copying blob 88d1e2c4 done
  Copying config 51b7ec39 done
Writing manifest to image destination — sha256:51b7ec39
OUT
lab_note "The serving engine is a signed container, patched and lifecycled like"
lab_note "any other RHEL content."

lab_section "2. Download a validated model from the Red Hat AI repository"
step "huggingface-cli download $MODEL_REPO --local-dir $MODEL_PATH" <<'OUT'
Fetching 14 files from RedHatAI/granite-3.3-8b-instruct ...
  model-00001-of-00004.safetensors  [####################]  4.9 GB
  model-00002-of-00004.safetensors  [####################]  4.9 GB
  model-00003-of-00004.safetensors  [####################]  4.6 GB
  model-00004-of-00004.safetensors  [####################]  1.9 GB
Download complete: /var/models/granite-3.3-8b-instruct
OUT
lab_note "Validated and quantized variants ship in the Red Hat AI repository."
lab_note "In an enclave, mirror into your own registry — Lab 06 verifies the signature."

lab_section "3. Serve it locally"
lab_note "In live mode this blocks. Run it in a second terminal, or install the"
lab_note "Quadlet unit so systemd owns the container in production."
step "podman run --rm --device nvidia.com/gpu=all --shm-size 4g -p 127.0.0.1:8000:8000 -v /var/models:/models:Z $RHAIIS_IMAGE --model /models/granite-3.3-8b-instruct" <<'OUT'
INFO  vLLM API server  |  gpu_memory_utilization=0.90  max_model_len=8192
INFO  Loading weights ... 16.3 GB in 14.2s
INFO  Started server — OpenAI-compatible API on port 8000
OUT

lab_section "4. Confirm the endpoint is local only"
step "ss -ltnp | grep ':8000'" <<'OUT'
LISTEN 0  2048  127.0.0.1:8000  0.0.0.0:*  users:(("conmon",pid=48211,fd=9))
OUT
lab_note "Published on 127.0.0.1. There is no egress path. This is the answer to"
lab_note "'where does our data go when someone prompts the model?'"

lab_section "5. Classify a real taxpayer contact"
step "curl -sS http://127.0.0.1:8000/v1/chat/completions -H 'Content-Type: application/json' -d @assets/inquiry.json | jq -r '.choices[0].message.content'" <<'OUT'
category:        refund_status_inquiry
secondary:       address_change
missing_doc:     Form 8822, Change of Address
routing:         Accounts Management - refund trace queue
urgency:         normal
draft_reply:     "We show a refund issued for tax year 2024. Because our
                  records still list your prior address, the check may have
                  been returned. Submit Form 8822 to update your address,
                  then request a refund trace."

tokens: 214 in / 96 out   ·   latency: 1.31s   ·   host: rhaiis-gpu-01
OUT

lab_footer
cat <<'TAKEAWAY'
Takeaway
  A defensible AI pilot starts on one machine you already own, with a supported
  product rather than a pile of Python. The base model does not yet know your
  notice codes or routing queues — that is Lab 02.
TAKEAWAY
