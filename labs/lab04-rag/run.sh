#!/usr/bin/env bash
# Lab 04 — Ground answers in your own guidance (OpenShift AI + vector store)
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../bin/lib.sh"

LAB_STEPS_TOTAL=5
NS="${NS:-tax-inference}"
CORPUS="${CORPUS:-./corpus}"

require_cmd oc python3

lab_header "04" "Ground answers in your own guidance" "OpenShift AI - retrieval"

lab_note "A model that sounds confident and cites nothing is a liability in a"
lab_note "tax agency. Retrieval is how an answer arrives with its source."

lab_section "1. A vector store on the same cluster as the model"
step "oc apply -n $NS -f manifests/pgvector.yaml && oc get pods -n $NS -l app=pgvector" <<'OUT'
statefulset.apps/pgvector created
service/pgvector created
NAME          READY   STATUS    RESTARTS   AGE
pgvector-0    1/1     Running   0          38s
OUT

lab_section "2. Ingest the publication corpus"
step "python3 ingest.py --source $CORPUS --chunk 800 --overlap 120 --embed-model granite-embedding-125m" <<'OUT'
Scanning ./corpus ...
  Publication 17  General rules              412 pages   1,904 chunks
  Publication 501 Filing status               38 pages     171 chunks
  Publication 594 Collection process          14 pages      62 chunks
  Internal guidance - notices CP01..CP2000   221 pages     998 chunks
  embedding [####################] 3,135 / 3,135
Indexed 3,135 chunks into pgvector.tax_guidance (768-dim, HNSW)
OUT
lab_note "Re-run this when guidance is republished. Publications change far"
lab_note "more often than model weights should."

lab_section "3. Ask something the corpus can answer"
step "python3 query.py 'A taxpayer received a CP14 and cannot pay in full. What are their options and where is that documented?'" <<'OUT'
A CP14 is a notice of unpaid balance. Options for a taxpayer who cannot pay
in full:

  1. Short-term payment plan - up to 180 days, no setup fee.
  2. Installment agreement - monthly payments; setup fee may be waived for
     low-income applicants.
  3. Offer in compromise - settles for less than owed where collectability
     is in doubt.
  4. Currently not collectible status - collection paused where payment
     would prevent meeting basic living expenses.

sources:
  [1] Publication 594, p.4  "Options for paying"         score 0.891
  [2] Publication 594, p.7  "Currently not collectible"  score 0.864
  [3] Internal guidance CP14 section 3.2                 score 0.842
OUT
lab_note "The citation block is the part your reviewers actually need."

lab_section "4. Ask something the corpus cannot answer"
step "python3 query.py 'What is the penalty rate for late filing in the 2031 tax year?'" <<'OUT'
I do not have guidance covering tax year 2031 in the indexed corpus.
The most recent published rates I can cite are for tax year 2025.
Refer this to a specialist rather than relying on this answer.

sources: none above threshold (0.75)
OUT
lab_note "Demo this to your governance board. Refusal is a feature, and it is"
lab_note "the single most important behaviour to verify before you go live."

lab_section "5. Prove the threshold is doing the work"
step "python3 query.py --explain 'What is the penalty rate for late filing in the 2031 tax year?'" <<'OUT'
retrieval trace:
  candidate 1  Publication 17, p.impact-of-late-filing    score 0.712  REJECTED
  candidate 2  Internal guidance, penalties overview      score 0.688  REJECTED
  candidate 3  Publication 594, p.4                       score 0.601  REJECTED
  threshold                                               0.750
  passing candidates                                      0
decision: refuse and refer
OUT

lab_footer
cat <<'TAKEAWAY'
Takeaway
  Retrieval turns a general model into an agency system of reference, and it
  is far cheaper than retraining. It also keeps sensitive text out of training
  entirely - the corpus is queried, never learned.
TAKEAWAY
