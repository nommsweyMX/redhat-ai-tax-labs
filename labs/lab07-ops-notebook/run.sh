#!/usr/bin/env bash
# Lab 07 — Ask your own logs (OpenShift AI · OpenShift Logging · Granite)
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../bin/lib.sh"

LAB_STEPS_TOTAL=5
LOKI_URL="${LOKI_URL:-https://loki-gateway.openshift-logging.svc}"
NS="${NS:-tax-inference}"

require_cmd logcli python3

lab_header "07" "Ask your own logs" "OpenShift AI · OpenShift Logging · Granite"

lab_note "Goal: the Lab 04 retrieval pattern pointed at operations itself."
lab_note "Logs, runbooks, incidents and change records become a private notebook"
lab_note "you can question during an incident. The payoff is measured in MTTR."

lab_section "1. The incident — 14:20 on a Tuesday"
step "logcli query '{namespace=\"$NS\"} |= \"ERROR\"' --since 24h --limit 4" <<'OUT'
https://loki-gateway.openshift-logging.svc - tenant: infrastructure
14:02:11Z predictor-7f9cd  CUDA out of memory. Tried to allocate 1.42 GiB
14:02:14Z predictor-7f9cd  vLLM engine loop crashed - restarting
14:07:52Z predictor-b2d14  CUDA out of memory. Tried to allocate 1.42 GiB
14:09:33Z kserve  readiness flapping on 2 of 6 replicas
OUT
lab_note "p99 latency has tripled and predictor pods are restarting."

lab_section "2. Build the operations corpus"
step "python3 ingest_ops.py --loki $LOKI_URL --runbooks ./runbooks --incidents ./postmortems --changes ./change-records" <<'OUT'
Building the operations corpus ...
  loki export       90 days - tax-inference + platform    8,912 chunks
  runbooks          48 documents                            517 chunks
  incident history  312 postmortems                       1,466 chunks
  change records    1,240 entries                         1,240 chunks
  embedding [####################] 12,135 / 12,135
Indexed 12,135 chunks into pgvector.ops_notebook (768-dim, HNSW)
OUT
lab_note "Same stack as Lab 04 - only the corpus changed. Nothing left the cluster."

lab_section "3. Ask the notebook the on-call question"
step "llama-stack-client inference chat-completion --message 'tax-classifier p99 tripled since 14:00 and predictor pods are OOM-restarting. What changed, has this happened before, and which runbook applies?'" <<'OUT'
Probable cause: change CR-9012, applied 13:47 today, raised
max_model_len 8192 -> 16384 on tax-classifier. At the configured
gpu_memory_utilization of 0.90 this leaves too little headroom
for the KV cache, and predictor pods OOM under load.

Precedent: INC-2209 (March filing surge) - identical OOM signature
after a context-length change; resolved by reverting and re-testing
at reduced memory utilization.

Applicable runbook: RB-114 "vLLM memory pressure", steps 3-5.

sources:
  [1] change record CR-9012                      score 0.93
  [2] INC-2209 postmortem - root cause           score 0.91
  [3] runbook RB-114 s.3-5                       score 0.88
  [4] loki predictor-7f9cd 14:02:11Z             score 0.86
OUT
lab_note "Forty minutes of grepping and paging, answered in eleven seconds -"
lab_note "with citations to check before acting."

lab_section "4. Remediate through the Lab 05 automation"
step "awx job_templates launch 'RB-114 - revert model config change' --extra_vars '{\"change\": \"CR-9012\"}' --monitor -f human" <<'OUT'
Resolved change CR-9012 -> revert max_model_len to 8192
job 40417 pending -> running
TASK [Revert InferenceService config] ****************************
changed: [ocp-prod-1] => max_model_len 16384 -> 8192
TASK [Wait for predictors Ready] *********************************
ok: [ocp-prod-1] => 6/6 replicas Ready, 0 restarts in 5m window
TASK [Send canary inquiry] ***************************************
ok: [ocp-prod-1] => classified in 0.29s (threshold 2.00s)
job 40417 successful - evidence lands in controller history (Lab 05)
OUT

lab_section "5. Read the MTTR numbers"
step "python3 mttr_report.py --window last-quarter" <<'OUT'
MTTR decomposition - tax platform production incidents
                        detect   diagnose   fix     verify   total
  4 quarters before       4m      2h 41m    22m      9m     3h 16m
  with the notebook       4m        24m     22m      9m       59m

  incidents this quarter: 17 - diagnosis time -84% - total -70%
OUT
lab_note "Detection was already fast. The hours lived in diagnosis - that is"
lab_note "what a notebook over your own logs removes."

lab_footer
cat <<'TAKEAWAY'
Takeaway
  Dashboards show that something broke. A notebook grounded in your own logs,
  runbooks and incidents tells you why - and diagnosis is where MTTR actually
  lives. Logs carry hostnames and case identifiers: keeping this notebook
  on-cluster is not optional.
TAKEAWAY
