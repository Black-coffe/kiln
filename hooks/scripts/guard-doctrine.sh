#!/usr/bin/env bash
# Kiln PreToolUse hook: enforce P10, "the doctrine changes only through a PR carrying evidence".
#
# An agent may prepare a doctrine amendment. An agent may not land one. In an unattended run there
# is no human between the model and the file, so writes to doctrine/ are denied outright.
# Interactively the write is allowed and a reminder of the PR requirements is attached.
#
# Detection of "unattended" is heuristic. There is no documented flag meaning "no human is
# watching", so this keys on the usual CI markers plus the remote-session variable. A local
# headless run started by hand will read as interactive; that is the deliberate direction to err,
# because the alternative blocks legitimate editing.

set -uo pipefail

input=$(cat)

path=""
if command -v jq >/dev/null 2>&1; then
  path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.notebook_path // ""')
else
  # Without jq, do not guess. Fail open and say so: a false block on every edit is worse than a
  # missed guard, and the PR requirement is also enforced in review.
  printf 'Kiln: jq is not installed, so the doctrine write guard is inactive.\n' >&2
  exit 1
fi

[ -n "$path" ] || exit 0

case "$path" in
  */doctrine/*|doctrine/*) ;;
  *) exit 0 ;;
esac

# Threshold files are explicitly exempt: P10 keeps calibrated numbers local and mutable.
case "$path" in
  *thresholds.yml|*thresholds.yaml) exit 0 ;;
esac

automated=0
[ -n "${CI:-}" ] && automated=1
[ -n "${GITHUB_ACTIONS:-}" ] && automated=1
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] && automated=1

reason="Kiln P10: the doctrine changes only through a PR carrying evidence, and this run is unattended (CI, GitHub Actions or a remote session). Automatic amendment is forbidden because the doctrine is shared across every project using Kiln: a change derived from noise on one project moves all of them at once.

Write the proposed amendment to .kiln/rule-changes/ instead and open a PR containing: the recorded observations, data with dates and sources, the affected projects, the metric that will verify the change, and the rollback condition.

Calibrated thresholds are exempt and belong in .kiln/thresholds.yml, which stays local."

if [ "$automated" -eq 1 ]; then
  jq -n --arg r "$reason" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse", permissionDecision:"deny", permissionDecisionReason:$r}}'
  exit 0
fi

jq -n --arg c "Editing the doctrine. P10 requires a PR carrying: recorded observations, dated data with sources, affected projects, the verification metric and the rollback condition. A rule without evidence is an opinion. If this is a threshold rather than a rule, it belongs in .kiln/thresholds.yml." \
  '{hookSpecificOutput:{hookEventName:"PreToolUse", additionalContext:$c}}'
exit 0
