#!/usr/bin/env bash
# Report which labs can run live in this environment, and which cannot.
# Never fails: its job is to tell you where you stand before a session.
set -uo pipefail

check() {
  local lab="$1"; shift
  local missing=()
  for cmd in "$@"; do
    command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
  done
  if [[ ${#missing[@]} -eq 0 ]]; then
    printf '  %-22s live ready\n' "$lab"
  else
    printf '  %-22s simulate only (missing: %s)\n' "$lab" "${missing[*]}"
  fi
}

echo "Lab readiness for LAB_MODE=live:"
check "lab01-rhel-ai"      podman huggingface-cli curl jq
check "lab02-instructlab"  python3
check "lab03-openshift-ai" oc curl jq hey
check "lab04-rag"          oc python3
check "lab05-ansible"      ansible-navigator ansible-rulebook
check "lab06-trust"        oc cosign ssh
check "lab07-ops-notebook" logcli python3
echo
echo "Every lab runs today in simulate mode, which needs nothing above."
echo "  ./bin/run-all-labs.sh"
