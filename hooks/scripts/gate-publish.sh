#!/usr/bin/env bash
# Kiln PreToolUse hook: nothing reaches publication without a passing machine gate and a logged
# human review.
#
# This is the point where the doctrine stops being advisory. The predecessor system carried the
# same rules as guidance with the hook left unbuilt, and the whole thing rested on one person's
# discipline.
#
# Fires on two shapes of publishing action:
#   1. a Bash command that looks like publishing (a publish script, an API call to the publish
#      endpoint, a deploy of content)
#   2. a Write or Edit under the project's published-content path, which is read from
#      publishing.content_root in .kiln/project.yml and is never guessed
#
# Requires, per .kiln/project.yml and the doctrine:
#   - score.json for the slug, with no BLOCK findings          (05-writing-core.md)
#   - .kiln/reviews/<slug>.yml with substantive_changes present (06-review-lenses.md, P11)
#   - the weekly publishing cap not exceeded                    (P2)

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
KILN_DIR="$PROJECT_DIR/.kiln"

[ -d "$KILN_DIR" ] || exit 0   # Kiln not used here.

input=$(cat)

command -v jq >/dev/null 2>&1 || {
  printf 'Kiln: jq is not installed, so the publication gate cannot run. Install jq: without it nothing enforces the gate and the doctrine is advisory again.\n' >&2
  exit 2
}

tool=$(printf '%s' "$input" | jq -r '.tool_name // ""')
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""')
path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // ""')

deny() {
  jq -n --arg r "$1" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse", permissionDecision:"deny", permissionDecisionReason:$r}}'
  exit 0
}

slug=""

if [ "$tool" = "Bash" ]; then
  case "$cmd" in
    *kiln*publish*|*publish.py*|*publish.sh*|*"--publish"*|*kiln:publish*) ;;
    *) exit 0 ;;
  esac
  slug=$(printf '%s' "$cmd" | grep -oE '(^|[[:space:]])--slug[= ][A-Za-z0-9_-]+' | tail -1 | grep -oE '[A-Za-z0-9_-]+$' || true)
else
  # Write/Edit under published content.
  #
  # The content root is DECLARED in .kiln/project.yml, never inferred from folder names.
  # A gate that guesses its own scope stops guarding the moment a project renames a
  # directory, and it does so silently, which is the worst way for a gate to fail.
  [ -n "$path" ] || exit 0

  content_root=""
  if command -v yq >/dev/null 2>&1; then
    content_root=$(yq -r '.publishing.content_root // ""' "$KILN_DIR/project.yml" 2>/dev/null || printf '')
  else
    # Minimal fallback parse so a missing yq degrades to "fail closed", not "guess".
    content_root=$(sed -n 's/^[[:space:]]*content_root:[[:space:]]*["'\'']\{0,1\}\([^"'\''#]*\)["'\'']\{0,1\}.*/\1/p' \
      "$KILN_DIR/project.yml" 2>/dev/null | head -1 | sed 's/[[:space:]]*$//')
  fi

  if [ -z "$content_root" ] || [ "$content_root" = "null" ]; then
    deny "Kiln gate: publishing.content_root is not declared in .kiln/project.yml, so the gate cannot tell which paths are publishable content and is failing closed.

This is deliberate. The gate previously inferred the content root from common folder names (content/, posts/, articles/), which meant that renaming a directory silently disabled the guard. Declare the path explicitly, per 01-onboarding-grill.md and adapter/SPEC.md §1.0."
  fi

  case "$path" in
    *"$content_root"*) ;;
    *) exit 0 ;;
  esac
  slug=$(basename "$path" | sed 's/\.[^.]*$//')
fi

[ -n "$slug" ] || deny "Kiln gate: could not determine which slug this publishing action refers to, so the machine gate and review log cannot be checked. Pass --slug explicitly, or publish through the documented endpoint in .kiln/project.yml."

SCORE="$KILN_DIR/scores/$slug.json"
REVIEW="$KILN_DIR/reviews/$slug.yml"

if [ ! -f "$SCORE" ]; then
  deny "Kiln gate: no machine score for '$slug' at .kiln/scores/$slug.json. A draft has to pass draft_score.py before it can consume human review time, let alone be published. Run /kiln:write to score it."
fi

blocks=$(jq -r '[.findings[]? | select(.severity == "BLOCK")] | length' "$SCORE" 2>/dev/null || printf 'err')
if [ "$blocks" = "err" ]; then
  deny "Kiln gate: .kiln/scores/$slug.json is unreadable or malformed. Re-run scoring; a gate that cannot read its own evidence must not pass the draft."
fi
if [ "$blocks" != "0" ]; then
  detail=$(jq -r '[.findings[]? | select(.severity=="BLOCK") | .rule + ": " + .summary] | join("; ")' "$SCORE" 2>/dev/null || printf '')
  deny "Kiln gate: '$slug' has $blocks blocking finding(s). $detail
A BLOCK is never softened because the draft is otherwise good. The funnel of what was rejected, and why, is this system's primary measure of itself."
fi

if [ ! -f "$REVIEW" ]; then
  deny "Kiln gate: no human review log for '$slug' at .kiln/reviews/$slug.yml. P11 requires substantive human review before publication. It is also what grants exemption from labelling under EU AI Act Art. 50, in force since 2026-08-02: a footer or general terms do not qualify, examination of the substance does."
fi

if command -v yq >/dev/null 2>&1; then
  subs=$(yq -r '[.lenses[]?.substantive_changes[]?] | length' "$REVIEW" 2>/dev/null || printf '0')
  if [ "${subs:-0}" = "0" ]; then
    deny "Kiln gate: the review log for '$slug' records no substantive changes across any lens. An empty log is a BLOCKER, not a formality: a purely formal review is more dangerous than none, because it produces a document that looks like grounds for an AI Act exemption without being one."
  fi
fi

exit 0
