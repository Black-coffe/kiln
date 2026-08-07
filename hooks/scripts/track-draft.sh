#!/usr/bin/env bash
# Kiln PostToolUse hook: record that a draft file was written in this session.
#
# The Stop hook needs to know whether any draft was produced without a review log. PostToolUse
# cannot block, so this only writes the ledger the Stop hook reads.
#
# The ledger is session-scoped and belongs in the project, not under ${CLAUDE_PLUGIN_ROOT}: that
# path changes on every plugin update and the old directory is deleted.

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
KILN_DIR="$PROJECT_DIR/.kiln"
[ -d "$KILN_DIR" ] || exit 0

command -v jq >/dev/null 2>&1 || exit 0

input=$(cat)
path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // ""')
[ -n "$path" ] || exit 0

case "$path" in
  *content/*|*posts/*|*articles/*) ;;
  *) exit 0 ;;
esac
case "$path" in
  *.md|*.mdx|*.html) ;;
  *) exit 0 ;;
esac

mkdir -p "$KILN_DIR/session"
slug=$(basename "$path" | sed 's/\.[^.]*$//')
printf '%s\n' "$slug" >> "$KILN_DIR/session/drafts-touched.txt"

# Keep it unique and bounded so the Stop hook stays cheap.
if [ -f "$KILN_DIR/session/drafts-touched.txt" ]; then
  sort -u "$KILN_DIR/session/drafts-touched.txt" -o "$KILN_DIR/session/drafts-touched.txt"
fi

exit 0
