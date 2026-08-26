#!/usr/bin/env bash
# Lab 01 — Serve a model inside your boundary (Red Hat Enterprise Linux AI)
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../bin/lib.sh"

LAB_STEPS_TOTAL=5
MODEL_REPO="${MODEL_REPO:-docker://registry.redhat.io/rhelai1/granite-8b-lab-v1}"
MODEL_NAME="${MODEL_NAME:-granite-8b-lab-v1}"
MODEL_PATH="${MODEL_PATH:-$HOME/.cache/instructlab/models/$MODEL_NAME}"

require_cmd ilab

lab_header "01" "Serve a model inside your boundary" "Red Hat Enterprise Linux AI"

lab_note "Goal: a supported LLM answering agency questions on hardware you control."
lab_note "Nothing in this lab makes an inference call off this host."

lab_section "1. Initialize the toolchain and detect the accelerator"
step "ilab config init" <<'OUT'
Welcome to InstructLab CLI. This guide will help you set up your environment.
Generating config file and profiles:
    /home/admin/.config/instructlab/config.yaml
Detecting hardware profile...
    Detected: NVIDIA H100 80GB HBM3 x1  ->  profile applied
Initialization complete.
OUT

lab_section "2. Pull a signed model from the Red Hat registry"
step "ilab model download --repository $MODEL_REPO" <<'OUT'
Downloading model from registry.redhat.io ...
  manifest      sha256:9c41ab7f  verified
  layer 1/4     [####################]  4.1 GB
  layer 2/4     [####################]  3.8 GB
  layer 3/4     [####################]  2.2 GB
  layer 4/4     [####################]  1.4 GB
Model saved to /var/home/admin/.cache/instructlab/models/granite-8b-lab-v1
OUT

lab_section "3. Serve it locally"
lab_note "In live mode this blocks. Run it in a second terminal, or use the systemd unit:"
lab_note "  sudo systemctl enable --now instructlab-serve"
step "ilab model serve --model-path $MODEL_PATH" <<'OUT'
INFO  Using model /var/home/admin/.cache/instructlab/models/granite-8b-lab-v1
INFO  vLLM engine starting  |  gpu_memory_utilization=0.90  max_model_len=8192
INFO  Loading weights ... 8.1 GB in 11.4s
INFO  Started server process — listening on http://127.0.0.1:8000/v1
OUT

lab_section "4. Confirm the endpoint is local only"
step "ss -ltnp | grep ':8000'" <<'OUT'
LISTEN 0  2048  127.0.0.1:8000  0.0.0.0:*  users:(("python3",pid=48211,fd=9))
OUT
lab_note "Bound to 127.0.0.1. There is no egress path. This is the answer to"
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

tokens: 214 in / 96 out   ·   latency: 1.31s   ·   host: rhelai-gpu-01
OUT

lab_footer
cat <<'TAKEAWAY'
Takeaway
  A defensible AI pilot starts on one machine you already own, with a supported
  product rather than a pile of Python. The base model does not yet know your
  notice codes or routing queues — that is Lab 02.
TAKEAWAY
