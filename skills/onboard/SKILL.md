---
name: onboard
description: Onboard a project into Kiln. Runs automated site and search-data collection, applies the eligibility gates, then interviews the owner on the five things that cannot be extracted from data, and writes .kiln/project.yml. Use when setting Kiln up on a new site, when re-onboarding after a vertical or product change, or when .kiln/project.yml is missing.
argument-hint: "[domain]"
disable-model-invocation: true
allowed-tools: Read, Write, Edit, WebFetch, AskUserQuestion
---

# Onboard a project

Governing doctrine: `${CLAUDE_PLUGIN_ROOT}/doctrine/01-onboarding-grill.md`.
Read it in full before starting. Every rule `ONB-01`…`ONB-23`, every gate threshold and the
complete `.kiln/project.yml` schema live there. Do not restate them here and do not work from
memory: the thresholds are calibrated and the schema changes between versions.

Root principles that constrain this procedure: `P2` (pace equals verification capacity),
`P11` (a human is mandatory at onboarding), `P12` (server-side rendering is a blocking gate),
`P13` (unique value must be named). See `${CLAUDE_PLUGIN_ROOT}/doctrine/00-principles.md`.

## Why this skill is user-invocable only

The interview needs `AskUserQuestion`, and that tool is stripped from every subagent. The grill
therefore runs in the main thread. It also must never fire on a schedule: an unattended run would
produce a profile nobody agreed to, and `.kiln/project.yml` is the file every other module trusts.

## Order of work

Run the four phases in order. Do not start Phase C before Phase B has passed, and do not skip
Phase D.

**Phase A, automated collection.** Everything derivable from the site, its search data and the
SERP. Follow §1 of the doctrine. Cost is roughly one to three dollars. Nothing here is asked of
the owner: an answer from memory is worse data than a measurement, and asking for it burns the
attention you need for Phase C.

**Phase B, eligibility gates.** Seven blocking gates, `ONB-10`…`ONB-16`, each with a check
command in the doctrine. A failure is a stop, not a warning. Report which gate failed, what was
measured, and what would have to change. Do not proceed to the interview on a project that cannot
be onboarded.

**Phase C, the grill.** Five blocks, roughly thirty questions, target thirty minutes. Ask only
what Phase A could not produce: prohibited claims, product truth, proprietary assets, authorship,
conversion. Use `AskUserQuestion`. Put the recommended answer first in every option list and say
why the system needs it.

Two rules that are easy to violate and expensive to violate:

- `ONB-18` — an empty answer blocks completion. A gate that only fires on a filled field rewards
  silence, so "I don't know" goes into `open_questions` with an owner and a date, never into a
  blank.
- `ONB-23` — if the interview runs past an hour, something extractable leaked into it. That is a
  defect in the doctrine, not a property of the project. Log it to the amendment queue under `P8`.

**Phase D, confirmation.** The owner confirms competitor classification, cluster boundaries,
vertical priority and the computed pace. Roughly ten minutes. Misclassifying a competitor as
`direct` when it is `serp_only` poisons the entire content plan downstream, so this is not a
formality.

## Locales are declared here, and they are blocking

The doctrine is in English. Content is always produced in the language of the site. Every locale
in `project.yml` names a `lang_ruleset`, and if `doctrine/lang/<code>.md` does not exist for it,
that locale cannot be onboarded. Borrowing another language's pack is forbidden — the dash-density
rule alone is correct for English and ungrammatical in Cyrillic.

## Output

`.kiln/project.yml` in the consuming repository, committed to git. Never write project state under
`${CLAUDE_PLUGIN_ROOT}`: that path changes on every plugin update and the old directory is deleted.

Finish by printing the onboarding report: which gates passed with what measurements, what Phase A
found that the owner did not know, the computed `max_pages_per_week`, and the open questions with
their owners.
