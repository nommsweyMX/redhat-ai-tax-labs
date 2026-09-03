#!/usr/bin/env bash
# Lab 02 — Teach it your notice taxonomy (SDG Hub + Training Hub on Red Hat AI)
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../bin/lib.sh"

LAB_STEPS_TOTAL=5
SEEDS="${SEEDS:-./taxonomy/knowledge/gov/tax/notices}"
SDG_OUT="${SDG_OUT:-./sdg}"
TEACHER_ENDPOINT="${TEACHER_ENDPOINT:-http://127.0.0.1:8000/v1}"
BASE_MODEL="${BASE_MODEL:-/var/models/granite-3.3-8b-instruct}"

require_cmd python3

lab_header "02" "Teach it your notice taxonomy" "SDG Hub + Training Hub on Red Hat AI"

lab_note "Goal: agency knowledge enters the model as seed YAML a subject matter"
lab_note "expert can read and a reviewer can approve in a pull request."
lab_note "Live mode needs the sdg-hub and training-hub Python libraries and hours"
lab_note "of GPU time; simulate mode walks the same path in minutes."

lab_section "1. The knowledge a subject matter expert writes"
step "cat $SEEDS/qna.yaml | head -24" <<'OUT'
version: 3
domain: tax_administration
created_by: revenue-modernization-team
document_outline: |
  Agency notice families, their meaning in plain language, the response
  window each carries, and the queue that owns them.
seed_examples:
  - context: |
      Notice CP2000 proposes changes to a return based on third-party income
      reporting that does not match the return as filed. It is a proposal,
      not a bill, and carries a 30-day response window.
    questions_and_answers:
      - question: A taxpayer asks why they received a CP2000. What is it?
        answer: |
          It is a proposed change, not a bill. Third-party income records do
          not match the return as filed. They have 30 days to agree or to
          respond with documentation.
OUT

lab_section "2. Validate the contribution before anything expensive runs"
step "python3 check_seeds.py --seeds $SEEDS" <<'OUT'
taxonomy/knowledge/gov/tax/notices/qna.yaml
Seed data is valid.
1 topic - 12 seed examples - schema v3 - no errors
OUT
lab_note "This is the gate that belongs in CI. A bad contribution fails here,"
lab_note "not after four hours of GPU time."

lab_section "3. Synthetic data generation - 12 examples become thousands"
step "python3 generate.py --seeds $SEEDS --endpoint $TEACHER_ENDPOINT --scale 30 --output $SDG_OUT" <<'OUT'
INFO  sdg_hub flow: knowledge_generation
INFO  Generating against granite-3.3-8b-instruct via http://127.0.0.1:8000/v1 (the Lab 01 endpoint)
  knowledge generation   [####################]  1,842 samples
  skills generation      [####################]    714 samples
  quality filter         [####################]  2,556 -> 2,203 kept
Wrote ./sdg/knowledge_train_msgs_2026-09-02T14_02_11.jsonl
OUT
lab_note "Every generated sample traces to a seed example a human wrote."
lab_note "Nobody labelled ten thousand rows by hand."

lab_section "4. Tune"
step "python3 train.py --base $BASE_MODEL --data $SDG_OUT --method lora" <<'OUT'
INFO  training_hub sft  |  LoRA rank 32  -  bf16  -  1x H100
  epoch 1/3  loss 1.884 -> 0.913   [####################]  4m 12s
  epoch 2/3  loss 0.913 -> 0.604   [####################]  4m 08s
  epoch 3/3  loss 0.604 -> 0.471   [####################]  4m 10s
Checkpoint: ./checkpoints/granite-8b-tax-v1/samples_2203
OUT

lab_section "5. Prove the tuned model beats the one you started with"
step "python3 evaluate.py --base $BASE_MODEL --tuned ./checkpoints/granite-8b-tax-v1" <<'OUT'
Evaluating tuned against base on held-out agency questions (LLM-as-judge) ...
                              base     tuned    delta
  notice family accuracy      0.61     0.94     +0.33
  correct routing queue       0.58     0.91     +0.33
  cites the right form        0.44     0.89     +0.45
  plain-language readability  0.72     0.86     +0.14
  overall judge score         6.1      7.8      +1.7
OUT
lab_note "This table is the artefact your governance board asks for. Keep the"
lab_note "held-out set out of the seed data or the numbers mean nothing."

lab_footer
cat <<'TAKEAWAY'
Takeaway
  Domain adaptation becomes a pull request a subject matter expert can review
  rather than a data science project. Promote the checkpoint to the model
  registry - Lab 03 serves it at filing-season scale.
TAKEAWAY
