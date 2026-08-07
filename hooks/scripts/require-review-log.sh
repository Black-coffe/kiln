#!/usr/bin/env bash
# Kiln Stop / SubagentStop hook: a session that produced a draft may not end with that draft
# sitting unscored and unreviewed.
#
# This closes the gap the publication gate cannot see. Publishing is blocked without a review log,
# but nothing otherwise stops a run from leaving finished-looking drafts lying in the repository
# for someone to ship later by hand, at which point the log is written from memory or not at all.
#
# Blocks by returning {"decision":"block"}, which sends the model back to finish the work.
# Blocks at most once per draft per session, so it cannot trap a run in a loop.

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
KILN_DIR="$PROJECT_DIR/.kiln"
LEDGER="$KILN_DIR/session/drafts-touched.txt"
NAGGED="$KILN_DIR/session/stop-nagged.txt"

[ -f "$LEDGER" ] || exit 0
command -v jq >/dev/null 2>&1 || exit 0

touch "$NAGGED"

pending=""
while IFS= read -r slug; do
  [ -n "$slug" ] || continue
  grep -qxF "$slug" "$NAGGED" 2>/dev/null && continue

  score="$KILN_DIR/scores/$slug.json"
  review="$KILN_DIR/reviews/$slug.yml"

  if [ ! -f "$score" ]; then
    pending="$pending
  - $slug: not scored (no .kiln/scores/$slug.json)"
  elif [ ! -f "$review" ]; then
    blocks=$(jq -r '[.findings[]? | select(.severity=="BLOCK")] | length' "$score" 2>/dev/null || printf '0')
    if [ "$blocks" = "0" ]; then
      pending="$pending
  - $slug: scored clean, but no review pack has been assembled (.kiln/reviews/$slug.yml missing)"
    fi
  fi
done < "$LEDGER"

[ -n "$pending" ] || exit 0

# Record the nag so the next Stop does not repeat it.
while IFS= read -r slug; do
  [ -n "$slug" ] && printf '%s\n' "$slug" >> "$NAGGED"
done < "$LEDGER"
sort -u "$NAGGED" -o "$NAGGED"

reason="Kiln: this session wrote drafts that are not through the gate yet.$pending

Finish the cycle rather than leaving them: score the draft (/kiln:write), then assemble the review packs (/kiln:review). A draft left finished-looking but unlogged tends to get published by hand later, and the review log is then written from memory, which is exactly what P11 and the AI Act exemption require it not to be.

If a draft was abandoned on purpose, record it in the plan's dropped section with the reason. Dropped items are the calibration data for the gate and are never purged."

jq -n --arg r "$reason" '{decision:"block", reason:$r}'
exit 0
