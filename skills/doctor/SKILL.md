---
name: doctor
description: Diagnose whether a project can run Kiln at all and whether its configuration is coherent — eligibility gates, credentials, locale packs, state files and script prerequisites. Use before onboarding, when a skill fails for unclear reasons, or after changing credentials or plugin versions.
allowed-tools: Read, Bash, Grep, Glob
---

# Diagnose the installation

Fast, read-only, no network cost beyond a handful of HEAD requests. Run this before blaming a
skill.

## 1. Eligibility

The seven blocking gates from `${CLAUDE_PLUGIN_ROOT}/doctrine/01-onboarding-grill.md` §2,
`ONB-10`…`ONB-16`, each with its check command there. Report the measurement, not a verdict alone:
"38 % of body words present in raw HTML, threshold 30 %, pass" is actionable; "SSR: ok" is not.

Server-side rendering and AI crawler reachability are the two that silently cost the most. A
client-rendered site ranks in Google and is invisible to every AI answer engine, and the site
owner usually does not know.

## 2. Configuration coherence

- `.kiln/project.yml` exists, parses, and matches the current `schema_version`
- every locale in it names a `lang_ruleset` that exists at
  `${CLAUDE_PLUGIN_ROOT}/doctrine/lang/<code>.md` — a missing pack is a `BLOCK`, and borrowing
  another language's pack is forbidden under `P5`
- `.kiln/thresholds.yml` exists; report which thresholds are still at doctrine defaults and have
  never been calibrated
- `max_pages_per_week` was computed from review capacity and not typed in by hand
- `publishing.mode` matches what the repository can actually do. Under `mode: manual`, automated
  linking and bulk refresh are off, and that is a different product with different promises — say
  so plainly rather than in a footnote

## 3. Credentials and runtimes

Report presence, never values. `CLAUDE_PLUGIN_OPTION_*` for the configured keys; the Search
Console service account file resolves and is readable; Python is available for the layer 2
scripts.

Secrets go in through plugin configuration, not into `.kiln/`. Note that project-level settings
files are ignored for plugin configuration by design, so a value committed to the repository will
never be read.

## 4. Platform footguns worth checking

- Is a project-level agent shadowing a Kiln agent by name? Plugin agents are the lowest priority
  and are overridden silently.
- Is anything writing state under `${CLAUDE_PLUGIN_ROOT}`? That path changes on every plugin
  update and the old directory is deleted. State belongs in `.kiln/`.
- Does this project need to run in CI or a cloud session? Those do not read user-scope plugins, so
  the marketplace and plugin must be declared in the repository's own settings.

## Output

A table: check, measured value, threshold, verdict, and the fix. End with the single most
important thing blocking progress. If nothing is blocking, say that Kiln is ready and name the
next command.
