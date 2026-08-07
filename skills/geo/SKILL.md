---
name: geo
description: Run the AI answer engine citation probe set and score visibility across engines. Use when measuring how often the site is cited by ChatGPT, Perplexity, Claude or AI Overviews, when checking AI crawler reachability, or when investigating a lost citation.
argument-hint: "[--probe|--score|--crawlers]"
allowed-tools: Read, Write, Edit, Bash, WebFetch
---

# AI answer engine visibility

Governing doctrine: `${CLAUDE_PLUGIN_ROOT}/doctrine/09-geo.md`, with `P12` in
`${CLAUDE_PLUGIN_ROOT}/doctrine/00-principles.md` as the constraint on what counts as GEO work at
all.

## GEO is not a separate discipline

Google documents that no additional requirement and no special markup exists for AI Overviews or
AI Mode. Since 2026-07-24 the spam policies cover manipulating generative responses verbatim, so
this operates under the same enforcement regime as everything else. Nothing here is a loophole.

## What is confirmed and therefore acted on

- **Server-side rendering.** AI crawlers do not execute JavaScript. A client-rendered site is
  invisible to ChatGPT, Claude and Perplexity while ranking normally in Google. This is checked at
  onboarding as a blocking gate and re-checked here.
- **robots.txt granularity.** Blocking `GPTBot` does not affect ChatGPT visibility; accidentally
  blocking `OAI-SearchBot` removes it completely. `ClaudeBot` is not `Claude-SearchBot`. Verify
  by name, and compare status code and body size across bots to catch cloaking.
- **First third of the document.** 44.2 % of citations come from the first 30 % of the text.
- **Self-contained passages.** A section opening with "this" or "such an approach" loses its
  meaning when extracted, and extraction is what these engines do.

## What is rejected, and must stay rejected

- `llms.txt` — 97 % of them were never requested once over a month across 137 K domains. Google
  says it neither helps nor hurts. Generate one if you like; treating it as a metric is forbidden.
- Chunking content into bite-sized pieces for LLMs — criticised directly by Google on 2026-01-08,
  and it contradicts half the popular advice for a reason.
- Special schema for AI — no such thing exists, and facts in markup but absent from visible text
  carry cloaking risk.

## Measurement is independent of Search Console

The generative report in Search Console gives impressions only: no queries, no clicks, no CTR, and
AI Overviews merged with AI Mode. So citation measurement runs on its own probe set.

A fixed set of 40 to 100 prompts per locale, run against each engine, repeated at least three
times per measurement because citation drift runs 40 to 60 % month over month. A single reading is
not a measurement. Record whether each reading came through an API or a live interface — the
grounding differs, and mixing them produces a number describing neither.

Cost is two to five dollars a month with our own keys, against subscriptions at 29 to 489.

## Reporting

Share of voice per engine, citation rate, position within the answer, and AI crawler hit counts
from server logs. Engines overlap on roughly 11 % of cited domains, so report per engine and never
average them into one score.
