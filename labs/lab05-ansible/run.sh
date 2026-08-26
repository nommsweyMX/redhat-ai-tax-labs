#!/usr/bin/env bash
# Lab 05 — Automate the toil around the model (Ansible Automation Platform)
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../bin/lib.sh"

LAB_STEPS_TOTAL=4
INVENTORY="${INVENTORY:-inventory/prod.ini}"
CONTROLLER="${CONTROLLER:-https://aap.agency.gov}"

require_cmd ansible-navigator ansible-rulebook

lab_header "05" "Automate the toil around the model" "Ansible Automation Platform"

lab_note "Most of the effort in production AI is not the model. It is"
lab_note "provisioning, patching, scaling and evidence collection."

lab_section "1. Check the endpoint the way a taxpayer would"
step "ansible-navigator run playbooks/model_endpoint_health.yml -i $INVENTORY --mode stdout" <<'OUT'
PLAY [Verify tax inference endpoints] ******************************

TASK [Gathering Facts] *********************************************
ok: [ocp-prod-1]

TASK [Query the model list endpoint] *******************************
ok: [ocp-prod-1] => granite-8b-tax-v1 ready

TASK [Send a canary inquiry] ***************************************
ok: [ocp-prod-1] => classified in 0.31s (threshold 2.00s)

TASK [Verify served model digest matches the approved change record]
ok: [ocp-prod-1] => sha256:4b91c0e2 matches CR-8841

PLAY RECAP *********************************************************
ocp-prod-1   ok=4  changed=0  unreachable=0  failed=0
OUT
lab_note "The digest check is the one people forget. A model that drifted from"
lab_note "the approved artefact is an accreditation finding, not an incident."

lab_section "2. Read the rulebook - it is the runbook"
step "cat rulebooks/inference_saturation.yml" <<'OUT'
- name: Respond to tax inference saturation
  hosts: all
  sources:
    - ansible.eda.alertmanager:
        host: 0.0.0.0
        port: 5000
  rules:
    - name: Queue depth sustained over threshold
      condition: event.alert.labels.alertname == InferenceQueueDepth
      action:
        run_job_template:
          name: Expand tax-inference capacity
          organization: Revenue Modernization
    - name: Endpoint failed its canary
      condition: event.alert.labels.alertname == CanaryFailed
      action:
        run_job_template:
          name: Roll back to last approved model
OUT
lab_note "There is no separate runbook document to go stale. This file is it."

lab_section "3. Start the rules engine and watch it remediate"
step "ansible-rulebook --rulebook rulebooks/inference_saturation.yml -i $INVENTORY --controller-url $CONTROLLER" <<'OUT'
INFO  Starting rules engine ...
INFO  Ruleset "Respond to tax inference saturation" started
INFO  Listening for alertmanager events on 0.0.0.0:5000

[14:38:02] EVENT  InferenceQueueDepth  severity=warning  depth=612
[14:38:02] RULE   "Queue depth sustained over threshold" matched
[14:38:03] ACTION run_job_template -> "Expand tax-inference capacity"
[14:38:19]        job 40213 | scaled maxReplicas 20 -> 32
[14:38:41]        job 40213 | 11 new replicas Ready
[14:39:04] EVENT  InferenceQueueDepth  resolved  depth=38
OUT
lab_note "Alert to resolved: 62 seconds. No ticket, no pager, no war room."

lab_section "4. The audit trail writes itself"
step "awx job list --status successful --created__gte 2026-08-26 -f human" <<'OUT'
id     name                              status       elapsed  launched_by
40213  Expand tax-inference capacity     successful   21.4s    eda-rulebook
40209  Patch GPU nodes (rolling)         successful   14m 02s  scheduled
40204  Collect compliance evidence       successful   3m 11s   scheduled
40198  Mirror model to enclave registry  successful   8m 47s   j.rivera
OUT
lab_note "This list is what your assessor asks for in Lab 06. Nobody assembled"
lab_note "it by hand at the end of the quarter."

lab_footer
cat <<'TAKEAWAY'
Takeaway
  Automation is what makes AI operable at agency scale. Without it every model
  becomes a pet that someone has to feed, and the evidence package becomes a
  quarterly fire drill.
TAKEAWAY
