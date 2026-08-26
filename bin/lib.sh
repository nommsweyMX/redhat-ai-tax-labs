#!/usr/bin/env bash
# Shared runtime for the Red Hat AI tax administration labs.
#
# Every lab script is a sequence of steps. A step is a real command plus the
# output you should expect from it. Two modes:
#
#   LAB_MODE=simulate  (default) print the command and its expected output.
#                      Runs anywhere, needs no cluster, no GPU, no credentials.
#   LAB_MODE=live      execute the command for real against your environment.
#
# The simulated output is not decoration: it is the acceptance criterion. If
# live output diverges from it, that divergence is the lab finding.
#
# Environment:
#   LAB_MODE=simulate|live   default simulate
#   LAB_PACE=auto|step       step waits for Enter between commands (default auto)
#   LAB_SPEED=<float>        seconds between simulated output lines (default 0.04)
#   NO_COLOR=1               disable ANSI colour

set -o pipefail

LAB_MODE="${LAB_MODE:-simulate}"
LAB_PACE="${LAB_PACE:-auto}"
LAB_SPEED="${LAB_SPEED:-0.04}"

if [[ -n "${NO_COLOR:-}" || ! -t 1 ]]; then
  C_RESET=''; C_PS1=''; C_CMD=''; C_DIM=''; C_OK=''; C_WARN=''; C_ERR=''; C_KEY=''; C_HEAD=''
else
  C_RESET=$'\033[0m'
  C_PS1=$'\033[38;5;79m'      # prompt green
  C_CMD=$'\033[1;37m'         # bold command
  C_DIM=$'\033[38;5;245m'
  C_OK=$'\033[38;5;79m'
  C_WARN=$'\033[38;5;179m'
  C_ERR=$'\033[38;5;203m'
  C_KEY=$'\033[38;5;110m'
  C_HEAD=$'\033[1;38;5;203m'  # Red Hat red
fi

_LAB_STEP_NO=0
_LAB_FAILURES=0

# lab_header "01" "Serve a model inside your boundary" "Red Hat Enterprise Linux AI"
lab_header() {
  local num="$1" title="$2" product="$3"
  printf '\n%s' "$C_HEAD"
  printf '===============================================================================\n'
  printf ' LAB %s   %s\n' "$num" "$title"
  printf '%s' "$C_RESET"
  printf '%s %s   |   mode: %s   |   pace: %s%s\n' \
    "$C_DIM" "$product" "$LAB_MODE" "$LAB_PACE" "$C_RESET"
  printf '%s===============================================================================%s\n\n' \
    "$C_DIM" "$C_RESET"
}

lab_section() { printf '\n%s--- %s %s\n' "$C_DIM" "$*" "$C_RESET"; }

# lab_note "why this step matters"
lab_note() { printf '%s# %s%s\n' "$C_WARN" "$*" "$C_RESET"; }

_lab_pause() {
  [[ "$LAB_PACE" != "step" ]] && return 0
  printf '%s[Enter] to run, s to skip, q to quit: %s' "$C_DIM" "$C_RESET"
  local key; read -r key
  case "$key" in
    q|Q) printf '\n%sLab stopped by user.%s\n' "$C_DIM" "$C_RESET"; exit 0 ;;
    s|S) return 1 ;;
    *)   return 0 ;;
  esac
}

# step "<command>" <<'OUT'
# expected output line
# OUT
step() {
  local cmd="$1"; shift
  local prompt="${LAB_PROMPT:-$}"
  local expected; expected="$(cat)"

  _LAB_STEP_NO=$((_LAB_STEP_NO + 1))
  # Read the total at call time: lab scripts set LAB_STEPS_TOTAL after sourcing.
  if [[ "${LAB_STEPS_TOTAL:-0}" -gt 0 ]]; then
    printf '%s[step %d/%d]%s\n' "$C_DIM" "$_LAB_STEP_NO" "${LAB_STEPS_TOTAL}" "$C_RESET"
  fi
  printf '%s%s %s%s%s\n' "$C_PS1" "$prompt" "$C_CMD" "$cmd" "$C_RESET"

  if ! _lab_pause; then
    printf '%s(skipped)%s\n\n' "$C_DIM" "$C_RESET"
    return 0
  fi

  if [[ "$LAB_MODE" == "live" ]]; then
    local rc=0
    eval "$cmd" || rc=$?
    if [[ $rc -ne 0 ]]; then
      _LAB_FAILURES=$((_LAB_FAILURES + 1))
      printf '%s! command exited %d — expected output was:%s\n' "$C_ERR" "$rc" "$C_RESET"
      printf '%s%s%s\n' "$C_DIM" "$expected" "$C_RESET"
    fi
  else
    local line
    while IFS= read -r line; do
      printf '%s\n' "$line"
      sleep "$LAB_SPEED" 2>/dev/null || true
    done <<< "$expected"
  fi
  printf '\n'
}

lab_footer() {
  if [[ "$LAB_MODE" == "live" && $_LAB_FAILURES -gt 0 ]]; then
    printf '%s%d of %d steps did not exit cleanly. Review the output above.%s\n\n' \
      "$C_ERR" "$_LAB_FAILURES" "$_LAB_STEP_NO" "$C_RESET"
    return 1
  fi
  printf '%s* Lab complete — %s steps.%s\n\n' "$C_OK" "$_LAB_STEP_NO" "$C_RESET"
}

# Guard rails for live mode: refuse to run against something that is not there.
require_cmd() {
  [[ "$LAB_MODE" != "live" ]] && return 0
  local missing=0 c
  for c in "$@"; do
    if ! command -v "$c" >/dev/null 2>&1; then
      printf '%smissing required command: %s%s\n' "$C_ERR" "$c" "$C_RESET"
      missing=1
    fi
  done
  if [[ $missing -eq 1 ]]; then
    printf '%sRun with LAB_MODE=simulate to walk the lab without these tools.%s\n' "$C_DIM" "$C_RESET"
    exit 2
  fi
}
