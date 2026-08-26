#!/usr/bin/env bash
# Lab 06 — Prove it to your ISSO (RHEL, Compliance Operator, TrustyAI, Sigstore)
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../bin/lib.sh"

LAB_STEPS_TOTAL=5
NS="${NS:-tax-inference}"
MODEL_REF="${MODEL_REF:-registry.agency.gov/models/granite-8b-tax-v1}"
GPU_NODE="${GPU_NODE:-ocp-gpu-04}"

require_cmd oc cosign

lab_header "06" "Prove it to your ISSO" "RHEL - Compliance Operator - TrustyAI"

lab_note "These are the exact checks an authorizing official runs. Every one of"
lab_note "them is a platform feature you switch on, not a project you fund."

lab_section "1. Is this the model we approved?"
step "cosign verify --key agency-model-signing.pub $MODEL_REF" <<'OUT'
Verification for registry.agency.gov/models/granite-8b-tax-v1 --
The cosign claims were validated
The signatures were verified against the specified public key
  digest:    sha256:4b91c0e2f7a3...
  signed by: revenue-modernization-release
  timestamp: 2026-08-19T18:22:04Z
  change:    CR-8841 (approved by AO 2026-08-20)
OUT
lab_note "Provenance is checked before admission, not audited after the fact."

lab_section "2. Is the cryptography validated, and is the host enforcing?"
step "ssh $GPU_NODE 'fips-mode-setup --check; sestatus | head -3'" <<'OUT'
FIPS mode is enabled.

SELinux status:                 enabled
SELinuxfs mount:                /sys/fs/selinux
Current mode:                   enforcing
OUT

lab_section "3. Is the platform still hardened this quarter?"
step "oc get compliancescan -n openshift-compliance" <<'OUT'
NAME                     PHASE   RESULT
ocp4-moderate            DONE    NON-COMPLIANT
ocp4-moderate-node       DONE    COMPLIANT
rhcos4-moderate-worker   DONE    COMPLIANT
OUT
lab_note "NON-COMPLIANT is the honest result, and it is the useful one."
lab_note "A scan that always passes is a scan nobody is reading."

lab_section "4. What exactly failed?"
step "oc get compliancecheckresult -n openshift-compliance -l compliance.openshift.io/check-status=FAIL" <<'OUT'
NAME                                              STATUS   SEVERITY
ocp4-moderate-audit-log-forwarding-enabled        FAIL     medium

1 of 217 checks failed. Remediation is available:
  oc apply -f complianceremediation/audit-log-forwarding
OUT
lab_note "Or let the Lab 05 rulebook apply it, which records the job and gives"
lab_note "you the evidence at the same time. Same fix, with a paper trail."

lab_section "5. Is the model behaving the way it did at accreditation?"
step "oc apply -n $NS -f manifests/trustyai-service.yaml && curl -sk https://trustyai.$NS.svc/metrics | grep -E 'drift|fairness'" <<'OUT'
trustyaiservice.trustyai.opendatahub.io/tax-trustyai created

trustyai_meanshift_drift{model="granite-8b-tax-v1",feature="inquiry_len"}   0.031
trustyai_meanshift_drift{model="granite-8b-tax-v1",feature="channel_mix"}   0.212
trustyai_fairness_dir{model="granite-8b-tax-v1",group="filing_status"}      0.968
trustyai_fairness_spd{model="granite-8b-tax-v1",group="filing_status"}     -0.014

channel_mix drift 0.212 exceeds the 0.150 alert threshold.
OUT
lab_note "Nothing is wrong with the model. More taxpayers moved to the portal."
lab_note "Drift monitoring tells you the world changed - that is the point."

lab_footer
cat <<'TAKEAWAY'
Takeaway
  Signed artefacts, validated crypto, continuous scanning and live drift
  metrics are platform features, not project work. That is what
  enterprise-ready has to mean before an AO will sign anything.
TAKEAWAY
