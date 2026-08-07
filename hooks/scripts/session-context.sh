#!/usr/bin/env bash
# Kiln SessionStart hook.
#
# A plugin's own CLAUDE.md is never loaded, so this is the only way project state reaches the
# model before the first prompt. Keep the payload small: it is paid for in every session.
#
# Emits a compact digest of .kiln/project.yml and .kiln/thresholds.yml as additionalContext.
# Never blocks: SessionStart cannot block, and a missing profile is a normal pre-onboarding state.

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
KILN_DIR="$PROJECT_DIR/.kiln"
PROFILE="$KILN_DIR/project.yml"

emit() {
  # $1 = context string
  if command -v jq >/dev/null 2>&1; then
    jq -n --arg ctx "$1" \
      '{hookSpecificOutput:{hookEventName:"SessionStart", additionalContext:$ctx}}'
  else
    printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":%s}}\n' \
      "$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/$/\\n/' | tr -d '\n' | sed 's/^/"/; s/$/"/')"
  fi
  exit 0
}

if [ ! -f "$PROFILE" ]; then
  [ -d "$KILN_DIR" ] || exit 0   # Kiln not used in this repo; stay silent.
  emit "Kiln: .kiln/ exists but project.yml is missing. The project is not onboarded. Run /kiln:onboard before any content work; every other skill reads this file."
fi

# yq is optional. Without it, point at the file rather than guessing its contents.
if ! command -v yq >/dev/null 2>&1; then
  emit "Kiln is active. Project profile: .kiln/project.yml (yq not installed, so it was not parsed here). Read it before content work: it carries locales, prohibited claims, product truth, authors and the publishing cap."
fi

get() { yq -r "$1 // \"?\"" "$PROFILE" 2>/dev/null || printf '?'; }

DOMAIN=$(get '.project.domain')
MODE=$(get '.project.mode')
YMYL=$(get '.niche.ymyl')
PUBLIC_INTEREST=$(get '.niche.public_interest')
LOCALES=$(yq -r '[.locales[] | .code + "(" + .lang_ruleset + ")"] | join(", ")' "$PROFILE" 2>/dev/null || printf '?')
CAP=$(get '.publishing.max_pages_per_week')
PUB_MODE=$(get '.publishing.mode')
HOURS=$(get '.review.capacity_hours_per_week')
OPEN_Q=$(yq -r '(.open_questions // []) | length' "$PROFILE" 2>/dev/null || printf '0')

CTX="Kiln is active on ${DOMAIN} (mode: ${MODE}).
Locales: ${LOCALES}. The doctrine is English; content is written in the locale's own language, using that locale's language pack.
YMYL: ${YMYL}. EU AI Act public-interest scope: ${PUBLIC_INTEREST}.
Publishing: ${PUB_MODE}, capped at ${CAP} pages/week, derived from ${HOURS} review hours/week. The cap is not raised because production is fast.
Open questions from onboarding: ${OPEN_Q}.

Before content work read .kiln/project.yml (prohibited claims, product truth, proprietary assets, authors) and the governing doctrine file for the task. Rules live in the doctrine and are not restated in skills.
Publication requires a passing machine gate and a logged human review. Never gate on an AI detector or a third-party content score."

if [ "$MODE" = "audit_only" ]; then
  CTX="$CTX
This project is audit_only: produce findings and proposals, never material prepared for publication."
fi

emit "$CTX"
