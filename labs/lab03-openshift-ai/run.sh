#!/usr/bin/env bash
# Lab 03 — Survive filing season (Red Hat OpenShift AI)
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../bin/lib.sh"

LAB_STEPS_TOTAL=6
NS="${NS:-tax-inference}"
ISVC="${ISVC:-tax-classifier}"

require_cmd oc

lab_header "03" "Survive filing season" "Red Hat OpenShift AI"

lab_note "One GPU host is a pilot. Filing season is a capacity event."
lab_note "The deployment below is a reviewable file, not a console click path."

lab_section "1. A project for the inference workload"
step "oc new-project $NS" <<'OUT'
Now using project "tax-inference" on server "https://api.ocp.agency.gov:6443".
OUT

lab_section "2. Confirm the serving runtimes the platform already ships"
step "oc get servingruntimes -n redhat-ods-applications" <<'OUT'
NAME                          DISABLED   MODELTYPE     AGE
vllm-runtime                  false      vLLM          31d
vllm-multinode-runtime        false      vLLM          31d
caikit-tgis-runtime           false      caikit        31d
ovms-runtime                  false      openvino_ir   31d
OUT
lab_note "vLLM gives you continuous batching. That is most of the throughput"
lab_note "difference between a demo and a service."

lab_section "3. Deploy the tuned model from Lab 02"
step "oc apply -n $NS -f manifests/inferenceservice-tax-classifier.yaml" <<'OUT'
inferenceservice.serving.kserve.io/tax-classifier created
OUT

lab_section "4. Wait for readiness"
step "oc get inferenceservice $ISVC -n $NS -w" <<'OUT'
NAME             URL                                          READY   AGE
tax-classifier                                                        8s
tax-classifier                                                       42s
tax-classifier   https://tax-classifier.tax-inference.svc      True    96s
OUT

lab_section "5. One request, the way a caseworker would"
step "curl -sk https://$ISVC.$NS.svc/v1/completions -H 'Content-Type: application/json' -d @assets/inquiry.json | jq -r '.choices[0].text'" <<'OUT'
category: refund_status_inquiry | queue: AM-refund-trace | form: 8822

real  0m0.412s
OUT

lab_section "6. April load rehearsal - 400 concurrent taxpayers for 90 seconds"
lab_note "Run this against a non-production cluster. It is a load test, and it"
lab_note "will consume every GPU the namespace is allowed to schedule."
step "hey -z 90s -c 400 -m POST -D assets/inquiry.json -T application/json https://$ISVC.$NS.svc/v1/completions" <<'OUT'
Summary:
  Total:        90.0041 secs
  Requests/sec: 1183.42
  Latency  p50: 0.238s   p95: 0.612s   p99: 0.904s
  Errors:       0

Replicas observed during the run:
  t+00s   2    ####
  t+12s   6    ############
  t+24s  13    ##########################
  t+40s  20    ########################################  (max)
  t+95s   9    ##################
  t+180s  2    ####   scaled back to floor
OUT
lab_note "No application change. The manifest is the capacity plan."
lab_note "minReplicas is 2, not 0 - cold starts on an 8B model are not free."

lab_footer
cat <<'TAKEAWAY'
Takeaway
  Capacity for the April peak that costs nothing in August is the difference
  between a demo and a production service. The same manifest deploys to a
  datacenter cluster or an accredited cloud region.
TAKEAWAY
