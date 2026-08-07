---
name: link
description: Internal linking and cannibalization work — build the corpus graph, propose donor to target links, detect competing pages and prepare merge or redirect decisions. Use when adding internal links, when two pages compete for one query, when auditing orphan pages, or when planning a linking wave.
argument-hint: "[slug|--wave|--audit]"
allowed-tools: Read, Write, Edit, Grep, Glob
---

# Internal linking and anti-cannibalization

Governing doctrine: `${CLAUDE_PLUGIN_ROOT}/doctrine/07-linking.md`.
Read §2 (the seven donor-to-target gates, in order), §4 (limits) and §6 (the cannibalization
decision tree) before proposing anything.

Root principles: `P6` (one page, one intent, one URL), `P7` (an irrelevant internal link is
harmful, not neutral), `P11` (merges, redirects and deletions need a human).

## Embeddings retrieve candidates; they do not decide

Cosine similarity operates at gate 1 only. It measures sameness, and a useful link needs
complementarity — the target should cover something the current paragraph mentions but does not
explain. A mechanical threshold systematically picks pairs that are about the same subject and
help nobody.

The decision criterion is a question, not a number: **would reading the target help the reader
understand the paragraph they are in right now?**

Linking everything to everything on a cosine threshold is forbidden. `anchorMismatchDemotion` in
the Content Warehouse leak is a demotion, which makes an irrelevant link a cost rather than a
wasted opportunity. Internal anchors are counted separately from external ones, so the internal
profile degrades on its own.

## Position matters more than count

Priority links go in the first third of the document, inside the body of a paragraph. Split tests
put top-of-body at +25 % organic against +5 % for the footer, and 44.2 % of LLM citations come
from the first 30 % of the text. Extraction works at passage level, which is why "related reading"
blocks, sidebars and footers do not exist for citation purposes.

A test that **reduced** the number of links returned a positive result. More linking is not better
linking.

## Limits accumulate over 90 days

`LNK-15`. A per-run limit alone is trivially circumvented by running three times. Count on a
rolling window.

## The invariant that automation breaks by itself

One normalised anchor phrase resolves to exactly one URL within a locale. Automated linking
violates this on its own, because neighbouring pages in a cluster generate identical natural
anchors — so the anchor gate runs at every placement, not in a periodic audit that finds the
damage later.

Normalisation, including lemmatisation, is defined in the language pack. Without it the invariant
silently fails for inflected languages: two inflected forms of one phrase never collide, so the
conflict is never detected.

## Cannibalization decisions are human decisions

Detection is code, from 90 days of Search Console data with the preprocessing in §6.1 — deduplicate
before aggregating, treat the anonymous query as an empty string rather than NULL, cut the last
three to four days, filter to the non-brand segment. `flip_rate` is the honest signal.

The three outcomes are differentiate, 301, and consolidate. All three are irreversible operations
on an existing corpus. Prepare the decision with its evidence; a human approves it.

## Waves

At most 10 % of the corpus per wave, and every wave needs a control group of untouched pages in
the same section. Without group C, dilution is invisible and the measured effect is wrong rather
than merely noisy.
