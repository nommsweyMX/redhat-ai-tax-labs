#!/usr/bin/env bash
# Lab 08 — One loop, end to end (OpenShift AI · Ansible Lightspeed · Event-Driven Ansible)
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../bin/lib.sh"

LAB_STEPS_TOTAL=8
LOKI_URL="${LOKI_URL:-https://loki-gateway.openshift-logging.svc}"
NS="${NS:-tax-loop}"
AAP_URL="${AAP_URL:-https://aap.agency.gov}"
LIGHTSPEED_URL="${LIGHTSPEED_URL:-https://lightspeed-api.tax-loop.svc}"
# The wrappers (ingest_estate.py, score.py, lightspeed_draft.py, ask.py) read
# these in live mode; the commands below stay the same in both modes.
export LOKI_URL AAP_URL LIGHTSPEED_URL

require_cmd oc logcli python3 ansible-rulebook ansible-lint git gh awx

lab_header "08" "One loop, end to end" "OpenShift AI · Ansible Lightspeed · Event-Driven Ansible"

lab_note "Goal: Mainframe and server logs come in, a predictive model scores which"
lab_note "systems will fall over next, Ansible Lightspeed drafts the rulebook and"
lab_note "playbook, a person reviews and merges them, Event-Driven Ansible runs them,"
lab_note "and the assistant answers ‘how is server8-audits?’ by probing the estate."
lab_note "One platform carries every step, and the loop is also the knowledge base."

lab_section "1. Two kinds of AI, one namespace"
step "oc get pods -n $NS -o wide | awk '{print \$1, \$3, \$7}' | column -t" <<'OUT'
NAME                                     STATUS   NODE
outage-risk-predictor-00003-deployment   Running  ocp-gpu-02
granite-8b-tax-v1-predictor-00007        Running  ocp-gpu-02
lightspeed-api-6c8f9d                    Running  ocp-worker-05
vector-zos-syslog-0                      Running  ocp-worker-03
loki-gateway-7b9c                        Running  ocp-worker-03
eda-worker-activation-memory-pressure    Running  ocp-worker-05
ops-notebook-assistant-5d7f              Running  ocp-gpu-02
Predictive (sklearn) and generative (vLLM) models on the same GPU node, same registry, same identity.
OUT
lab_note "Two kinds of AI, one namespace: the scorer and the drafter share ocp-gpu-02."

lab_section "2. Three estates, one query"
step "logcli query '{source=~\"zos-syslog|journald|openshift\"} |~ \"OOM|S878|S80A|OOMKilled\"' --since 24h --limit 7" <<'OUT'
https://loki-gateway.openshift-logging.svc - tenant: infrastructure
02:41:07Z MVSA  IEA995I SYMPTOM DUMP OUTPUT  SYSTEM COMPLETION CODE=878  REASON=00000010  JOB IMFBATCH
02:41:09Z MVSA  IEF450I IMFBATCH STEP04 - ABEND=S878 U0000 REASON=00000010
02:58:33Z server8-audits  kernel: Out of memory: Killed process 41823 (java) total-vm:9.2G anon-rss:6.8G
02:58:34Z server8-audits  systemd[1]: audits-case.service: Main process exited, code=killed, status=9/KILL
03:12:50Z server8-audits  kernel: Out of memory: Killed process 42110 (java) total-vm:9.4G anon-rss:7.0G
03:20:02Z tax-inference  predictor-b2d14  container "kserve-container" OOMKilled (exit 137)
09:14:21Z server1-taxreturns  kernel: java invoked oom-killer: gfp_mask=0x140dca  (survived: cgroup limit held)
OUT
lab_note "Three estates, one query: z/OS SYSLOG via Vector, RHEL journald, OpenShift"
lab_note "container logs, all in Loki."

lab_section "3. Data becomes features"
step "python ingest_estate.py --sources zos-syslog,journald,openshift --window 30d --out estate.parquet" <<'OUT'
Reading 30 days from Loki ...
  zos-syslog   MVSA, MVSB               2 LPARs         612,400 lines   S878 · S80A · S0C4 · region · paging
  journald     12 RHEL hosts                           1,384,912 lines   oom-killer · GC pauses · swap
  openshift    tax-inference, tax-loop  2 namespaces    211,748 lines   OOMKilled · restarts · limits
Features per system per hour: mem_headroom, gc_pause_p95, abend_rate, batch_overlap, restarts
Wrote estate.parquet  14 systems x 720 hours = 10,080 rows  (2,209,060 lines in; no line left the cluster)
OUT
lab_note "Data becomes features. Same Loki the ops notebook (Lab 07) reads; nothing"
lab_note "new was installed."

lab_section "4. Information: a number per system"
step "python score.py --model outage-risk --horizon 72h --top 5" <<'OUT'
POST https://outage-risk-predictor.tax-loop.svc/v2/models/outage-risk/infer   (KServe · sklearn runtime)
SYSTEM               72H RISK  DRIVERS                                               TREND
server8-audits         0.91    heap headroom -38% wk/wk · GC p95 2.4s · 2 OOM kills     ^ rising
MVSA / IMFBATCH        0.74    S878 x3 in 7d · region 512M · batch overlap 02:00-03:00   ^ rising
server3-notices        0.41    swap in use 18% · restarts 1                            = flat
server1-taxreturns     0.22    cgroup limit held · 1 oom-killer survived               v falling
server5-transcripts    0.09    -                                                       = flat
Model: outage-risk v14  trained 2026-09-01 on 180d of estate features  AUC 0.93  (tabular; the Lab 02 pattern)
OUT
lab_note "Information: a number per system. Nothing has been decided; a person decides"
lab_note "what 0.91 means tonight."

lab_section "5. Generative: a draft, with citations"
step "python lightspeed_draft.py --prompt prompts/memory-pressure.txt --out drafts/" <<'OUT'
Ansible Lightspeed (on-prem)  model: granite-8b-code-instruct  served by: OpenShift AI (ocp-gpu-02)
prompt: relieve JVM memory pressure on a RHEL host inside the cgroup limit, restart in a maintenance
        window, verify with a probe; for a z/OS S878 abend notify the mainframe on-call
generated  drafts/playbooks/relieve_memory_pressure.yml   42 lines  (hosts, become, 5 tasks, a probe)
generated  drafts/rulebooks/memory_pressure.yml           31 lines  (sources: alertmanager, webhook)
  - name: Outage risk above threshold
    condition: event.alert.labels.alertname == "OutageRiskHigh" and event.alert.labels.score > 0.8
    action: run_job_template: { name: "Relieve memory pressure", extra_vars: { host: "{{ event.alert.labels.instance }}" } }
  - name: Mainframe storage abend
    condition: event.payload.abend == "S878"
    action: run_job_template: { name: "Notify mainframe on-call" }
citations: RB-207 (JVM sizing) · CR-9120 (audits heap change) · INC-2311 (last OOM on server8-audits)
OUT
lab_note "Generative: a draft, with citations. Nobody has run it. Lightspeed's model"
lab_note "is served by the same OpenShift AI as the scorer."

lab_section "6. Judgement: review, approve, merge"
step "ansible-lint drafts/ && git checkout -b eda/memory-pressure && git add drafts/ && git commit -qm 'EDA: memory pressure (Lightspeed draft)' && gh pr create -f -r sre-lead" <<'OUT'
ansible-lint  Passed: 0 failure(s), 0 warning(s) on 2 files.  Profile: production
[eda/memory-pressure 3f1c2a9] EDA: memory pressure (Lightspeed draft)   2 files changed, 73 insertions(+)
https://git.agency.gov/ops/loop-ops/pull/482
  review  sre-lead  requested changes: threshold 0.8 -> 0.85; add maintenance_window guard   (+11 min)
  review  sre-lead  approved after 2 edits                                                 (14:07)
  merged  main <- eda/memory-pressure   #482   by j.rivera
awx project update loop-ops                       -> synced rev 3f1c2a9 (14:08)
awx rulebook activation restart memory-pressure   -> running, rulebook memory_pressure.yml
km_publish: PR #482 + review thread indexed as RB-214 in pgvector.ops_notebook  (cites CR-9120, INC-2311)
OUT
lab_note "Judgement: a person edits, approves and merges. The merge is the promotion:"
lab_note "into the repo, into AAP, and into the knowledge base."

lab_section "7. The loop closes"
step "ansible-rulebook --rulebook rulebooks/memory_pressure.yml -i inventory/prod --controller-url $AAP_URL" <<'OUT'
INFO  Ruleset "Memory pressure" started   sources: alertmanager:5000, webhook:5001
[03:12:51] EVENT   OutageRiskHigh  instance=server8-audits  score=0.91
[03:12:51] RULE    "Outage risk above threshold" matched   (maintenance_window: true)
[03:12:52] ACTION  run_job_template -> "Relieve memory pressure"  host=server8-audits
[03:13:29]         job 40512 | Xmx 6g -> 7g (cgroup 9g) | audits-case.service restarted | probe 200 OK in 0.31s
[03:13:33]         job 40512 | ServiceNow INC-2340 opened and closed | KM record RB-214 updated (outcome: success)
Elapsed from event to verified: 42 seconds. No page. server8-audits re-scored: 0.91 -> 0.34
OUT
lab_note "The loop closes: event, approved playbook, ticket, knowledge record. Same"
lab_note "job history as Lab 05."

lab_section "8. Ask the platform what it knows"
step "python ask.py \"How is server1-taxreturns? How is server8-audits? Which servers are showing online?\"" <<'OUT'
ops assistant  (Granite on OpenShift AI · tools: job_template.launch, loki.query, km.search)
[tool] job_template.launch "Probe host"  host=server1-taxreturns    -> job 40518  4.1s
server1-taxreturns: online, up 41d, mem 62% (cgroup limit held), last oom-killer 09:14 today (survived),
  72h risk 0.22 and falling; last change CR-9088 (kernel patch, 09-02).   [journald · score.py · RB-214]
[tool] job_template.launch "Probe host"  host=server8-audits        -> job 40519  3.8s
server8-audits: online, restored 03:13 by job 40512 (Xmx 7g); no OOM since; risk 0.91 -> 0.34;
  change PR #482 merged, INC-2340 closed.   [job 40512 · PR #482 · INC-2340]
[tool] job_template.launch "Estate ping"  hosts=all                 -> job 40520  6.2s
online 13/14: server1..server12 ok · MVSA reachable (z/OSMF) · MVSB in planned IPL window until 06:00  [CR-9131]
The assistant probes and reports. It changes nothing except through a job template a person approved.
OUT
lab_note "Ask the platform what it knows. The tools are Ansible jobs; the memory is"
lab_note "the knowledge base the loop wrote."

lab_footer
cat <<'TAKEAWAY'
Takeaway
  One platform runs the predictive model, the generative model, the automation
  and the knowledge base, so the loop that keeps systems up is also the
  documentation, and the assistant answers from what the loop wrote.
TAKEAWAY
