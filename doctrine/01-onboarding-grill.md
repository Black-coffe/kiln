# 01 · Project Onboarding and the Owner Grill

> Subordinate to `00-principles.md`. Where the two disagree, the principles win.
> Implements **P11.1** (a human is mandatory at the onboarding point) and **P13** (unique value must be named).

**Version:** 0.1.0 · **Date:** 2026-08-07 · **Revision due:** every 90 days

---

## Header

|                       |                                                                                                                                                                                                |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Purpose**           | Bring a new project into Kiln: gather everything the data can yield, reject unsuitable projects, and extract from the owner **only what the data cannot produce**.                             |
| **Inputs**            | Domain. Search Console access. Access to the repository or to the publishing channel. Optional: Ahrefs/Semrush CSV exports, an existing keyword set, analytics.                                |
| **Outputs**           | `.kiln/project.yml` (profile), `.kiln/thresholds.yml` (starting thresholds), `.kiln/corpus.json` (corpus map), `.kiln/competitors/candidates.json`, eligibility report `onboarding-report.md`. |
| **Performed by**      | Phases A and B — code and agents, no human. Phase C — human, mandatory. Phase D — human, confirmation.                                                                                         |
| **Human time budget** | ~40 minutes (broken down in §7).                                                                                                                                                               |
| **Frequency**         | Once per project. Repeats only on the triggers in §6.                                                                                                                                          |

**The governing decision of this doctrine (D9).** The grill — a structured, adversarial interview
with the project owner — asks **only about what cannot be extracted**. Competitors, keywords,
technical defects, corpus composition and coverage gaps are obtained from data more accurately
and more cheaply than from the owner's memory, and are handed to the human for confirmation
rather than for guesswork. The difference in human hours: forty minutes instead of three hours,
with fewer errors.

---

## 0. Phase map

```
Phase A · automated collection   code + agents, ~20–40 min machine time, ~$1–3
    │                            artefacts: corpus.json, tech-audit.json, competitors/candidates.json
    ▼
Phase B · eligibility gates      code, ~2 min
    │                            BLOCK → onboarding halts, a repair list is issued
    ▼
Phase C · owner grill            human, ~30 min — FIVE BLOCKS OF THE NON-EXTRACTABLE
    │                            prohibited claims · product truth · proprietary assets · authorship · conversion
    ▼
Phase D · confirmation           human, ~10 min
    │                            competitor classification, cluster boundaries, vertical priority
    ▼
.kiln/project.yml                the project profile; everything downstream lives off it
```

The order is mandatory. The grill comes **after** automated collection, never before: half the
questions normally asked at a client briefing have already been answered by the data at that
point, and asking them anyway buys a worse answer at twice the cost.

---

## 1. Phase A — automated collection

Runs without human involvement. Every item produces a machine-readable artefact.

### 1.1 Site technical layer

| What                                        | How                                                           | Cost | Artefact                            |
| ------------------------------------------- | ------------------------------------------------------------- | ---- | ----------------------------------- |
| `robots.txt`                                | direct fetch                                                  | $0   | `tech-audit.json:robots`            |
| `sitemap.xml` + recursion through the index | direct fetch                                                  | $0   | `tech-audit.json:sitemap`, URL list |
| SSR/CSR rendering                           | fetch without executing JS, compare text volume with a render | $0   | `tech-audit.json:render`            |
| AI crawler accessibility                    | fetch with each bot's UA, compare status code and body size   | $0   | `tech-audit.json:bots`              |
| Locales and `hreflang`                      | parse HTML across several samples                             | $0   | `tech-audit.json:locales`           |
| schema.org markup                           | parse JSON-LD                                                 | $0   | `tech-audit.json:schema`            |
| Stack and CMS fingerprints                  | response headers, cookies, asset paths                        | $0   | `tech-audit.json:stack`             |
| RSS/Atom, `lastmod`                         | fetch                                                         | $0   | `tech-audit.json:freshness`         |

**ONB-01 · INFO · Recursion through the sitemap index is mandatory.**
A naive parser that reads only the first file undercounts the corpus by multiples. Recorded
precedent: a sitemap was read as 308 URLs when the real figure was 4,075 — everything else sat
in nested index files. An error at this step poisons every downstream coverage calculation.

**ONB-02 · INFO · Unicode-aware tokenisation for every length measurement.**
A direct consequence of **P5**. `wc -w` does not split Cyrillic into words; on a live measurement
this reported the English locale as six times larger than the Ukrainian one when the two were at
parity, and the conclusion came out inverted. Every word counter in Kiln uses Unicode segmentation.

### 1.2 Corpus

| What                 | How                                                                                                                             | Cost                                                                                                       | Artefact                     |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ---------------------------- |
| Full URL list        | sitemap + crawl from root, depth ≤3                                                                                             | $0 (Jina Reader, 500 RPM on a free key) [source: EVIDENCE.md#e12-data-apis-and-pricing]                    | `corpus.json`                |
| Per-page skeleton    | title, meta, heading stack, word count, canonical, robots meta, schema types, internal links, `published`/`modified`, text hash | $0–$16 (Firecrawl Free 1000 credits/mo, then Hobby $16/5k) [source: EVIDENCE.md#e12-data-apis-and-pricing] | `corpus.json`                |
| Internal link graph  | derived from skeletons                                                                                                          | $0                                                                                                         | `corpus.json:links`          |
| Orphans, click depth | computed over the graph                                                                                                         | $0                                                                                                         | `corpus.json:graph_health`   |
| Page embeddings      | local model                                                                                                                     | $0                                                                                                         | `.kiln/semantics/embeddings` |

**ONB-03 · WARN · Store the skeleton, not the HTML.**
Raw HTML is kept no longer than 7 days; the skeleton is kept indefinitely, because the value is
in the time series. [source: EVIDENCE.md#e07-competitive-intelligence]

**ONB-04 · WARN · Do not trust `lastmod` or `dateModified` without verification.**
Recorded precedent: `dateModified` was being filled with the request time — two fetches 27 seconds
apart returned different values, and 54 of 58 sitemap entries were stamped with the current day.
Where this is detected, change detection switches to the text hash, and the defect itself joins
the first-wave repair list.

### 1.3 First-party search data

| What                           | How                                                                                                | Cost          | Artefact                                    |
| ------------------------------ | -------------------------------------------------------------------------------------------------- | ------------- | ------------------------------------------- |
| 16-month Search Console export | Search Analytics API, `rowLimit` up to 25,000 per request [source: EVIDENCE.md#e04-search-console] | $0            | `.kiln/measurements/gsc-baseline.json`      |
| Enabling BigQuery bulk export  | one-time setup on the owner's side                                                                 | BigQuery cost | —                                           |
| Index coverage                 | the "Pages" report                                                                                 | $0            | `tech-audit.json:index_coverage`            |
| Manual actions                 | Manual Actions API                                                                                 | $0            | `tech-audit.json:manual_actions`            |
| Baseline findings              | striking distance, cannibalisation, CTR outliers, decay, coverage gaps                             | $0            | `.kiln/measurements/findings-baseline.json` |

**ONB-05 · BLOCK · The absence of a manual action does not mean the absence of a penalty.**
"Scaled content abuse" is **not present** in the official Search Console manual actions list —
the penalty for mass low-quality content arrives algorithmically and silently. The baseline
detector is therefore built on cohort dynamics of impressions and clicks, synchronised against
update dates; Manual Actions is a supplementary signal, not the primary one. [source: EVIDENCE.md#e13-policy-and-risk, G11]

**ONB-06 · WARN · A first-party history store is mandatory from day one.**
Search Console retains 16 months and erases anything older irrecoverably. Relying on the API alone
means that in eighteen months there will be no baseline left for year-over-year comparison. Bulk
export gives no retrospective — it accumulates from the moment it is switched on. [source: EVIDENCE.md#e04-search-console]

**ONB-07 · INFO · URL Inspection is a scarce resource.**
2,000 requests per day per site. Spend it only on URLs flagged by other checks; blanket sweeps
are forbidden. [source: EVIDENCE.md#e04-search-console]

### 1.4 Niche reconnaissance

| What                                  | How                                                   | Cost                                                                                                              | Artefact                        |
| ------------------------------------- | ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| Seed queries                          | Search Console top + corpus headings + product names  | $0                                                                                                                | `.kiln/semantics/seeds.json`    |
| Expansion                             | autosuggest, "people also ask"                        | ~$0                                                                                                               | `.kiln/semantics/expanded.json` |
| SERP sweep                            | 200–500 queries [expert judgement, needs calibration] | ~$0.50 per 500 queries on Serper; 2,500 queries free on signup [source: EVIDENCE.md#e07-competitive-intelligence] | `.kiln/serp/snapshots/`         |
| Domain frequency in the top 10        | computed from the sweep                               | $0                                                                                                                | `competitors/candidates.json`   |
| Preliminary competitor classification | agent, across the 5 classes                           | tokens                                                                                                            | `competitors/candidates.json`   |
| Coverage gaps                         | corpus compared against the top                       | tokens                                                                                                            | `onboarding-report.md`          |

Full organic reconnaissance for a project costs roughly **$2 per month**. [source: EVIDENCE.md#e07-competitive-intelligence]
That is two orders of magnitude below subscription pricing, which is what makes this step
mandatory rather than optional.

**ONB-08 · INFO · A competitor is a domain, not a company.**
Five classes: `direct`, `serp_only` (shares the SERP but not the business), `platform` (Reddit,
YouTube, reference projects), `aggregator`, `ai_only` (cited by answer engines but absent from
the top 10). A flat list is useless — the strategies against each class differ. [source: EVIDENCE.md#e07-competitive-intelligence]

**ONB-09 · INFO · Candidate threshold.**
A domain becomes a candidate once it appears in the top 10 for ≥5% of core queries, or for ≥20
queries in absolute terms. [expert judgement, needs calibration; proposed in EVIDENCE.md#e07-competitive-intelligence as an
engineering decision, not as an industry standard]

### 1.5 What automated collection does NOT give you

An explicit list, so that nobody mistakes this for completeness:

- search volumes and traffic estimates (requires an Ahrefs/Semrush export or a paid data source);
- the backlink profile;
- true positions in the national SERP, if reconnaissance ran through a third-party index;
- citation rate in answer engines (requires a first-party prompt set, see `09-geo.md`);
- everything in Phase C.

---

## 2. Phase B — eligibility gates

Checked automatically, before any human is involved. Any `BLOCK` halts onboarding: Kiln issues
a repair list and offers to resume once it is done.

### ONB-10 · BLOCK · Server-side rendering of content

If the main body text is absent from the HTML without executing JavaScript, the project is
unsuitable for the GEO loop.

**Rationale.** No major AI crawler executes JavaScript: `OAI-SearchBot`, `ChatGPT-User`, `GPTBot`,
`ClaudeBot`, `PerplexityBot`. The site stays visible to Google and completely invisible to ChatGPT,
Claude and Perplexity. [source: EVIDENCE.md#e01-geo-answer-engines, Vercel+MERJ measurement across 500M fetches] This is **P12**.

**Check:**

```bash
# Words in raw HTML without executing JS (Unicode-aware, see ONB-02)
curl -sL -A "OAI-SearchBot/1.0" "$URL" \
| python3 -c "import sys,re;h=sys.stdin.read();h=re.sub(r'(?is)<(script|style|noscript).*?</\1>',' ',h);print(len(re.sub(r'(?s)<[^>]+>',' ',h).split()))"
```

Threshold: if raw HTML yields fewer than **30%** of the rendered version's words — `BLOCK`.
[expert judgement, needs calibration]

### ONB-11 · BLOCK · Search-oriented AI crawlers must be reachable

Neither `robots.txt` nor the CDN may block `OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`
or `Googlebot`.

**Rationale.** The granularity is critical and is the single most commonly confused point:
`GPTBot` ≠ `OAI-SearchBot`, `ClaudeBot` ≠ `Claude-SearchBot`. Blocking the training crawler
(`GPTBot`) has no effect on appearance in ChatGPT; accidentally blocking the search crawler
(`OAI-SearchBot`) produces total invisibility. `Google-Extended` governs only the training of
Google's other systems, not appearance in Search AI features. [source: EVIDENCE.md#e01-geo-answer-engines]

Blocking **training** crawlers is a legitimate owner choice and does not violate this gate.

**Check:**

```bash
curl -s "$ORIGIN/robots.txt" | grep -iE "OAI-SearchBot|Claude-SearchBot|PerplexityBot|GPTBot|ClaudeBot|Google-Extended|CCBot|Googlebot"

# Actual reachability and cloaking indicators: status code and body size must match
for UA in "Googlebot/2.1" "OAI-SearchBot/1.0" "PerplexityBot/1.0" "Claude-SearchBot/1.0" "Mozilla/5.0"; do
  printf '%-24s ' "$UA"
  curl -s -o /dev/null -w '%{http_code} %{size_download}\n' -A "$UA" "$URL"
done
```

A body-size discrepancy between a bot and a browser is a cloaking indicator; that is a separate
`BLOCK` carrying the marker `cloaking_suspected`.

### ONB-12 · BLOCK · Programmatic read access to the corpus

Kiln must be able to obtain the full page list and their content programmatically. Without it,
internal linking, cannibalisation control and corpus refresh are impossible in principle — what
remains is a text generator, not Kiln.

Any one of the following is sufficient: a repository holding content files, a readable API,
read access to the database, or a complete and correct `sitemap.xml`.

### ONB-13 · BLOCK · Publishing channel

There must be a way to create a page **in draft status** programmatically, and a separate way to
move it to published.

**Rationale.** The separation is mandatory: the `nothing auto-publishes` rule is enforced here,
not in operator discipline. Proven pattern: `POST` creates a draft, a separate `PUT` changes status;
idempotency keyed on `slug`; localhost and `draft` as defaults; production credentials only from
environment variables. [internal observation, unpublished]

If publishing is possible only by hand through an admin panel, the severity depends on the size of
the existing corpus, because that is what decides whether the disabled modules are the ones the
project most needs:

| Corpus at onboarding | Severity | Reasoning                                                                                                             |
| -------------------- | -------- | --------------------------------------------------------------------------------------------------------------------- |
| Under 100 URLs       | `WARN`   | Little to link and little to refresh. Kiln still delivers planning, writing, review and measurement.                  |
| 100 URLs or more     | `BLOCK`  | Internal linking, refresh and consolidation all require programmatic writes, and at this size they are the main value |

Recorded in the profile as `publish.mode: manual` either way. Automated internal linking and bulk
corpus refresh are **disabled** in that mode. On a large corpus this is not a reduced-capability
mode, it is the removal of the modules that justify the installation: a 4,000-URL site cannot have
its link graph repaired by hand, and manual refresh of a stale corpus does not converge.

This maps to conformance level L3 in `adapter/SPEC.md` §6.2. Manual mode forfeits L3 entirely, and
one specific loss deserves naming: the cannibalization decision tree loses its 301 branch, so every
recommendation it makes will bias toward keeping duplicate pages alive.

**The consequence goes in the onboarding report as a headline finding, not a footnote.** "Full Kiln"
and "Kiln in manual mode" are two different products making two different promises, and the owner
decides which one they are buying on day one rather than discovering it in month two.

### ONB-14 · BLOCK · The domain is not under an active penalty

If Search Console shows an active manual action: lift it first, then Kiln.

**Rationale.** Recovery from site reputation abuse took 14+ months and was complete for nobody:
Forbes Advisor recovered roughly 10% of its peak, CNN Underscored roughly 39%. Publishing on top
of a live penalty is burning budget. [source: EVIDENCE.md#e13-policy-and-risk]

### ONB-15 · BLOCK · The domain is not a repurposed expired domain

If the domain was bought and repurposed for a topic unrelated to its history, Kiln is not deployed.

**Rationale.** Expired domain abuse is "purchased and repurposed primarily to manipulate search
rankings". [source: EVIDENCE.md#e13-policy-and-risk] Check: domain history in the web archive.

### ONB-16 · BLOCK · First party

Kiln does not publish content on a domain where the owner is not the first party, unless the
content's topic matches the host's primary topic.

**Rationale.** Site reputation abuse is the one policy with a documented rout. As of 2024-11-19
Google examined white-label arrangements, licensing agreements and equity participation and ruled
that **no degree of first-party involvement** excuses the abuse. [source: EVIDENCE.md#e13-policy-and-risk]

### ONB-17 · WARN · Review gap

If the declared human review capacity is zero, Kiln runs in `audit_only` mode: it finds and
proposes, but prepares nothing for publication.

**Rationale.** **P2** and **P11.2**. Without a human the publishing pace is zero by definition,
and pretending otherwise is self-deception.

---

## 3. Phase C — the owner grill

Thirty minutes. Five blocks. Only what the data does not contain.

**Question format.** The recommended option comes first and is marked as such, with an explanation
of why it is recommended _for this project_. Neutral lists of equivalent options do not exist here —
the owner must always be given a position to argue against.

**ONB-24 · BLOCK · The locale set is declared, and every locale has a language pack.**

Before any block is answered, the site's content language and full set of locales must be declared
and written into `project.yml:locales`. Kiln's doctrine is written in English; **the content Kiln
produces is always written in the language of the target site**, and for multilingual sites in each
declared locale's language. The language pack applied to a locale is `doctrine/lang/<code>.md`,
selected by that locale's `lang_ruleset`.

A declared locale with no corresponding pack in `doctrine/lang/` **blocks onboarding of that locale**
until the pack exists. Without it the language-dependent rules of **P5** are silently absent, or
worse, borrowed from a neighbouring language — and the recorded precedent for borrowing is a rule
that converted 349 grammatically required dashes into commas.

Automated collection can propose the locale list from `hreflang` and URL patterns (§1.1); the owner
confirms it, because inferred locales are frequently incomplete. The block is per locale, not per
project: a site may onboard its Ukrainian locale and hold its Polish one pending a pack.

**ONB-18 · BLOCK · An empty answer is not accepted in any block.**
"I don't know" is a valid answer, but it is recorded in the profile explicitly as `unknown` and
creates a task to find out. A field left silently blank blocks completion of onboarding.
Rationale: a gate that only engages once a field is filled rewards silence.

---

### Block 1 · Prohibited claims — what we are not allowed to say

Written to `project.yml:taboo`. Every item becomes a blocking rule in the pre-publication gate.

**Q1.1. Which claims are prohibited in your niche by a regulator or by law?**
→ _Recommended answer format:_ a list of phrasings, each citing the specific provision.
_Why the system needs it:_ without this, a model working on a YMYL topic will confidently write
something it does not carry the liability for. In finance, medicine and law this is the first
thing to enter the blocking list.

**Q1.2. Which promises of outcome are prohibited?**
→ _Recommended:_ list them verbatim ("approval guaranteed", "returns from X%", "complete
protection"). _Why:_ this is the most common way a text generator manufactures a legal problem
out of nothing.

**Q1.3. Which disclosures must be present on the page?**
→ _Recommended:_ affiliate income, licence, risk warning, data-as-of date. _Why:_ each becomes a
mandatory element of the page template and is checked by code. Separately: a credible affiliate
page must add something of its own — pricing, testing, comparison — otherwise it is thin
affiliation. [source: EVIDENCE.md#e13-policy-and-risk]

**Q1.4. Who and what do we not write about?**
→ _Recommended:_ name them explicitly — clients under NDA, partners, specific competitors.
_Why:_ otherwise competitor reconnaissance will surface material about someone we are barred from
covering, and it will only come out at review.

**Q1.5. Are there topics prohibited for reputational rather than legal reasons?**
→ _Recommended:_ politics, war, public figures, religion — unless they are explicitly part of the
subject matter. _Why:_ topical dispersion is penalised algorithmically. The February 2026 Discover
update introduced "topic-specific expertise within publications covering multiple subjects".
[source: EVIDENCE.md#e13-policy-and-risk]

**Q1.6. Who is accountable for a factual error in a publication?**
→ _Recommended:_ name a person, not a role. _Why:_ that same name goes into the human review log,
and the log is the artefact that supports the EU AI Act Article 50 exemption.

---

### Block 2 · Product truth — where we are worse

Written to `project.yml:product_truth`. Consumed directly by the writer.

Why this block exists: a model will not, by default, write against the product it is promoting.
A paragraph about who the product is _not_ for is almost impossible to generate by inertia — which
makes it simultaneously the strongest trust signal and the strongest anti-AI marker available.
A formulation proven on a live product, given here in its general shape: _"This is not for
everyone. Below [threshold], [the free alternative] works fine. Do not pay for [our category] you
do not need."_ Three moves in two sentences — a named disqualifying threshold, a named free
alternative, and an explicit instruction not to buy. A model does not produce that by inertia.
[internal observation, unpublished]

**Q2.1. Who is your product not for?**
→ _Recommended:_ name a concrete segment and a threshold ("below N, you don't need this").
_Why:_ this becomes a mandatory paragraph on commercial pages.

**Q2.2. Where is a competitor objectively better than you?**
→ _Recommended:_ name the competitor and the capability. _Why:_ "X vs Y" pages without honest
weaknesses on our own side read as advertising and do not get cited. The rule: "Never mentioning
that competitors exist" is a defect. [internal observation, unpublished]

**Q2.3. Which advertised feature performs worse than customers expect?**
→ _Recommended:_ name it. _Why:_ this is the subject of an honest article no competitor will
write — a direct source of information gain under **P13**.

**Q2.4. Which customer objection can you not close?**
→ _Why:_ if you cannot close it, do not try to close it with prose; naming it honestly is better.

**Q2.5. What do you not do, although people expect you to?**
→ _Why:_ this eliminates a whole class of pages that would have brought unqualified traffic and
degraded behavioural signals.

**Q2.6. What is the pricing model and why is it that way?**
→ _Recommended:_ state it openly. _Why:_ "hiding prices = hiding something". [internal observation, unpublished]

---

### Block 3 · Proprietary assets — the source of information gain

Written to `project.yml:unique_assets`. This is **the most valuable block of the grill**.

Why: true information gain cannot be computed (**P13**), but its presence can be guaranteed
materially. The only cheap and non-reproducible source is what only you have. A crawler cannot
find it, which is exactly why it is asked.

**Q3.1. What data does your product or business see that nobody else does?**
→ _Recommended:_ name a specific slice that can be anonymised and published. _Why:_ this is the
foundation of the entire content programme. Live examples from our own projects: a backlink
monitoring service sees real link mortality; a systems integrator sees deployment statistics;
a financial marketplace sees real terms and how they move. No competitor can reproduce that material.

**Q3.2. Which people can you reach for an interview or a comment?**
→ _Recommended:_ list them with job titles. _Why:_ a quote from a named person with a verifiable
role is something a model cannot invent without fabricating. From our own corpus: one project
already has three external experts with publicly verifiable titles, and the asset is entirely unused.

**Q3.3. Which internal documents could be anonymised and published?**
→ _Recommended:_ methodologies, checklists, calculations, contract templates. _Why:_ cheaper than
any research project, and non-reproducible.

**Q3.4. Which experiment could you run within a week?**
→ _Recommended:_ name one concrete experiment. _Why:_ a first-party measurement is the strongest
of the permitted values for `unique_value_source`.

**Q3.5. What can you photograph or screen-capture that competitors cannot?**
→ _Why:_ proprietary media. Stock imagery is forbidden in Kiln (see §9).

**Q3.6. What failure story do you have that could be told?**
→ _Recommended:_ an honest one, with numbers and without a happy ending. _Why:_ this is the
specification of a genuine case study — unrounded figures, what did not work, how many people
never replied, what took longer than expected. Such details cannot be synthesised; they can only
be possessed. [internal observation, unpublished]

---

### Block 4 · Authorship — whose name goes on it

Written to `project.yml:authors`.

**Q4.1. Who signs the material? Name the person.**
→ _Recommended:_ a real person with publicly verifiable credentials. _Why:_ Google requires
authorship — "Is it self-evident to your visitors who authored your content?"; on news surfaces a
byline and date are mandatory, and "repeated or egregious violations" lead to **permanent**
ineligibility. [source: EVIDENCE.md#e13-policy-and-risk, §8] Publishing with an AI as the named author is explicitly
discouraged by Google.

**Q4.2. How are those credentials verifiable in public sources?**
→ _Recommended:_ a professional network profile, publications, a public register, a certification —
anything that can go into `sameAs`. _Why:_ this is the machine proxy for expertise.

**Q4.3. Who is the subject-matter expert for each vertical?**
→ _Recommended:_ different people for different verticals. _Why:_ one of the four review lenses is
subject-matter expertise; without an assigned person, that lens does not function.

**Q4.4. Is the author willing to answer reader questions in public?**
→ _Why:_ if not, this is a signature rather than authorship, and on YMYL topics the difference shows.

**Q4.5. Whose authority are we building — the company's or the person's?**
→ _Recommended:_ both, with an explicit priority. _Why:_ it determines where mentions are directed
and how organisation and person markup is structured.

**Q4.6. Who logs their review, and how?**
→ _Recommended:_ through a diff in version control, or through an entry in `.kiln/reviews/`.
_Why:_ **P11**. The exemption from AI-content labelling under EU AI Act Article 50 is granted for
substantive human review specifically; blanket disclaimers in the footer or terms of service are
**not sufficient** under the European Commission guidance of 2026-07-20. Content created before
2026-08-02 does not require retroactive labelling. [source: EVIDENCE.md#e13-policy-and-risk]

---

### Block 5 · Conversion — what counts as a result

Written to `project.yml:conversion`.

**Q5.1. What has to happen on a page for it to count as having worked?**
→ _Recommended:_ name one action per page type. _Why:_ without it the system optimises impressions,
which is to say nothing.

**Q5.2. How is that measured technically, right now?**
→ _Recommended:_ name an event that already exists in analytics. _Why:_ if the measurement does not
exist, that is the first implementation task, and it needs to surface at onboarding rather than
three months in.

**Q5.3. What is one such action worth to the business?**
→ _Recommended:_ an order of magnitude is enough. _Why:_ it supplies the weights for cluster
prioritisation.

**Q5.4. Which pages should not convert at all?**
→ _Recommended:_ reference pages, glossary entries, definitions. _Why:_ otherwise calls to action
land on them and destroy trust in precisely the section that works for citation.

**Q5.5. In a conflict, which matters more — conversion or reader trust?**
→ _Recommended:_ trust. _Why:_ this is the tie-breaking rule between review lenses, which would
otherwise have to be settled by a vote every time. The data favours trust: the primary dividing
line between growing and declining sites is the share of pages that let the reader finish the task
on the spot.

**Q5.6. What minimum signal within 90 days would convince you the system works?**
→ _Recommended:_ leading indicators — new pages indexed, position shift on target clusters,
citation rate in AI answers, technical defects closed. _Why:_ **D8**. On an aged or abandoned
domain, traffic cannot respond within 90 days, and judging by it makes it easy to write off a
working system. Precedent from a live project: "the domain is 6 months old, position ~56 is
expected and is not a fixable defect; measure leading indicators, not clicks." [internal observation, unpublished]

---

## 4. Phase D — confirming what was collected

Ten minutes. The human is not answering questions here — they are correcting what Kiln already
assembled.

### 4.1 Competitor classification

Kiln shows the candidate list with a provisional class and share of voice. The human confirms or
changes the class.

**ONB-19 · BLOCK · Competitor classification is confirmed by a human.**
This is not a formality. Confusing `direct` with `serp_only` poisons the entire content plan:
against a direct competitor you write comparisons and teardowns, against a platform you build
presence, against an aggregator you build depth. Get the class wrong and the system spends months
producing well-written but strategically useless material. [source: EVIDENCE.md#e07-competitive-intelligence, step D8]

### 4.2 Cluster boundaries

Kiln shows the clusters derived from SERP overlap and flags those where the decision is unstable
(overlap sitting on the threshold).

The human confirms merges and splits for large clusters only.

**ONB-20 · WARN · The dominant clustering defect is over-merging.**
Top-10 URL overlap threshold: 3 is permissive, **4 is the working default**, 5+ suits competitive
niches. The threshold must be a project parameter, never a tool constant. [source: EVIDENCE.md#e05-semantics-and-clustering]

### 4.3 Vertical priority

The human orders the verticals. For each one Kiln displays: corpus volume, Search Console findings,
an estimate of how penetrable the top is, and whether a proprietary asset from Block 3 exists for it.

**ONB-21 · WARN · A vertical with no proprietary asset is demoted in priority.**
A direct consequence of **P13**: if Block 3 produced nothing that can be put into this vertical,
material written for it will be a rehash — which is precisely the "without adding value" case.

### 4.4 Confirming the pace

Kiln computes the pace ceiling as a function of the declared review capacity and shows the
resulting number. The human confirms it or lowers it. Raising it above the verification capacity
is not possible — that is blocked under **P2**.

---

## 5. The onboarding artefact: `.kiln/project.yml`

```yaml
# .kiln/project.yml — the project profile. The single source of truth about the project.
# Lives in git inside the project repository. Edited by a human, read by everything else.

schema_version: 1
created_at: 2026-08-07
onboarded_by: "name of the person who ran onboarding"

project:
  name: "short name"
  domain: "example.com"
  # Kiln operating mode:
  #   full       — the complete cycle, including preparing publications
  #   audit_only — findings and proposals only, nothing is prepared for publication
  #                (set automatically when review.capacity_hours_per_week = 0, ONB-17)
  mode: full

locales:
  # MANDATORY. Declared at onboarding and confirmed by a human (Phase C).
  # Kiln's doctrine is written in English; CONTENT IS ALWAYS PRODUCED IN THE SITE'S OWN
  # LANGUAGE — for a multilingual site, in the language of each declared locale.
  # Order matters: the first locale is primary; thresholds are calibrated against it.
  # BLOCK: if lang_ruleset has no matching file in doctrine/lang/<code>.md, the locale
  # cannot be onboarded. Language-dependent rules (P5) must never be absent or borrowed
  # from another language — the em-dash density rule alone breaks Cyrillic grammar.
  - code: uk # ISO 639-1
    url_pattern: "/" # how the locale is expressed in the URL
    lang_ruleset: uk # which pack from doctrine/lang/ applies (P5)
    is_primary: true
  - code: en
    url_pattern: "/en/"
    lang_ruleset: en
    is_primary: false

niche:
  description: "one line, in plain language"
  # YMYL switches on the mandatory editorial loop and raises the bar for sources
  # and authorship. Set according to the actual subject matter, not by preference.
  ymyl: true
  # "Matters of public interest" under EU AI Act Article 50. Overlaps with YMYL
  # but is not identical to it. Determines whether visible AI-involvement labelling
  # is required for material created on or after 2026-08-02.
  public_interest: true
  # Topical boundaries. Material outside this list requires explicit confirmation (Q1.5).
  topic_boundaries:
    - "consumer financial products"
    - "financial market regulation"

sections:
  # The section map. Required on any multi-vertical site.
  # SAF-09 (10-safety-gates.md) measures topical distance against the centroid of an
  # item's OWN section, never against a single site-wide centroid: on a site legitimately
  # covering several verticals the site centroid sits in empty space between them, so a
  # site-wide radius fires on nearly everything and trains the team to ignore it.
  # radius is calibrated on the existing corpus BEFORE the first wave. Until a section is
  # calibrated, SAF-09 records INFO for that section rather than WARN.
  - id: banks
    url_patterns: ["/bank/"]
    radius: null # null = not yet calibrated
  - id: mfo
    url_patterns: ["/mfo/"]
    radius: null
  - id: insurance
    url_patterns: ["/insurance/"]
    radius: null
  - id: wiki
    url_patterns: ["/wiki/"]
    radius: null
  - id: news
    url_patterns: ["/news/"]
    radius: null

taboo:
  # Grill Block 1. Every item becomes a blocking rule in the pre-publication gate.
  forbidden_claims:
    - claim: "guaranteed loan approval"
      basis: "reference to the provision or to an internal decision"
  forbidden_topics:
    - topic: "politics"
      reason: "reputational"
  mandatory_disclosures:
    # Checked by code on every page of the relevant type.
    - id: affiliate_income
      applies_to: [comparison, listing]
      text_ref: "docs/legal/affiliate-disclosure.md"
    - id: risk_warning
      applies_to: [all]
      text_ref: "docs/legal/risk-warning.md"
  do_not_mention:
    - "name of the company under NDA"
  responsible_person: "name — accountable for factual errors (Q1.6)"

product_truth:
  # Block 2. Used directly by the writer; mandatory on commercial pages.
  not_for:
    - segment: "who this is not for"
      threshold: "the concrete threshold, if one exists"
  competitors_better_at:
    - competitor: "domain"
      aspect: "where they are objectively better"
  known_weaknesses:
    - "an advertised feature that performs below expectations"
  unclosable_objections:
    - "an objection we cannot close"
  we_do_not_do:
    - "what people expect from us that we do not do"
  pricing_model: "an open description of the pricing model"

unique_assets:
  # Block 3. The only cheap source of information gain (P13).
  # An empty list means the vertical cannot be prioritised (ONB-21).
  - id: own_data_link_mortality
    type: own_data # own_data | own_experiment | interview | internal_doc | own_media | failure_story
    description: "what the data actually is"
    access: "how to obtain it: request, export, a specific person"
    publishable: true # can it be anonymised and published
    refresh: quarterly # how often it can be refreshed

authors:
  # Block 4. Feeds both the markup and the review log.
  # Policy first, then the people it governs. The two cannot be siblings in one sequence:
  # a bare list under `authors:` leaves nowhere to put the policy that applies to all of them.
  byline_policy: named_human # named_human | organization — publishing as an AI author is forbidden
  authority_target: both # company | person | both
  authority_priority: person
  people:
    - id: author_1
      name: "First Last"
      role: "job title"
      credentials: "what substantiates the qualification"
      same_as:
        - "https://..." # publicly verifiable profiles
      verticals: [credits, deposits] # where this person is the subject-matter expert
      answers_publicly: true

conversion:
  # Block 5.
  primary_action:
    - page_type: comparison
      action: "click through to the partner"
      tracked_as: "the event name in analytics"
      value_estimate: "order of magnitude"
  no_conversion_pages: [glossary, definition, reference]
  conflict_rule: trust_over_conversion # which wins when lenses conflict (Q5.5)
  success_90d:
    # D8: leading indicators, not traffic.
    - metric: indexed_new_pages
      target: "number"
    - metric: cluster_position_shift
      target: "number"
    - metric: ai_citation_rate
      target: "number"
    - metric: tech_defects_closed
      target: "number"

review:
  # P2 and P11.2. The publishing pace ceiling is computed from here.
  capacity_hours_per_week: 10
  lenses:
    # Four distinct lenses, not four readings of the same text (D6).
    # Each lens names a primary AND a backup; the backups form a ring
    # (06-review-lenses.md §9.1.1). A lens with no backup is WARN at onboarding
    # and BLOCK once the corpus passes the ONB-13 threshold (REV-B1).
    - id: facts
      primary: "name"
      backup: "name"
      hours_per_week: 2.5
      description: "every figure and condition checked against a primary source"
    - id: domain
      primary: "name"
      backup: "name" # WEAKEST LINK: hardest expertise to substitute.
      # On YMYL the backup must hold verifiable domain qualification, or the
      # lens has no valid backup at all and REV-B1 applies.
      hours_per_week: 2.5
      description: "subject-matter expertise — meaning errors fact-checking will not catch"
    - id: voice
      primary: "name"
      backup: "name"
      hours_per_week: 2.5
      description: "does it read as a living text"
    - id: utility
      primary: "name"
      backup: "name"
      hours_per_week: 2.5
      description: "does the page close the reader's task; is the product truth present"
  log_mode: git_diff # git_diff | kiln_reviews — where the review trace lives (P11)

publishing:
  mode: repo # repo | api | db | manual
  # Under mode: manual, automated internal linking and bulk corpus refresh are disabled (ONB-13).
  # On a corpus of 100+ URLs, manual mode is a BLOCK, not a WARN (ONB-13, adapter/SPEC.md §6.2).
  content_root: "content/" # REQUIRED. Repo-relative path holding publishable content.
  # Declared, never guessed. hooks/gate-publish.sh reads this value and fails
  # closed when it is absent: a gate that infers its own scope from folder
  # names silently stops guarding the moment a project renames a directory.
  # For mode: api | db, set the value the adapter reports (adapter/SPEC.md §1.0).
  draft_endpoint: "how a draft is created"
  publish_endpoint: "how a draft is moved to published"
  idempotency_key: slug
  # The pace ceiling. Computed by code from review.capacity_hours_per_week;
  # a human may only lower it (P2, §4.4).
  max_pages_per_week: 0 # filled in during onboarding, never by hand

access:
  gsc:
    property: "sc-domain:example.com"
    bigquery_export: true # enable on day one (ONB-06)
  analytics: "which system, and whether access exists"
  ahrefs: ui_only # api | ui_only | none
  serp_provider: dataforseo
  crawl_ladder: [jina, firecrawl, scrapingdog]

thresholds_ref: .kiln/thresholds.yml # thresholds live separately and are calibrated locally (P10)

open_questions:
  # Everything answered "I don't know" during onboarding (ONB-18). Never leave silently empty.
  - question: "..."
    owner: "who finds out"
    due: "date"
```

---

## 6. Triggers for re-running the grill

The full grill is not repeated on a calendar. **Individual blocks** are repeated, on events.

| Trigger                                                  | What gets re-grilled                                  | Severity                                  |
| -------------------------------------------------------- | ----------------------------------------------------- | ----------------------------------------- |
| A new vertical or topical branch opens                   | Blocks 1, 3, 4 (prohibited claims, assets, SME)       | `BLOCK` until the first publication in it |
| Niche regulation changes                                 | Block 1 in full                                       | `BLOCK`                                   |
| The product changes: new feature, new price, new segment | Block 2 in full                                       | `WARN`                                    |
| An author or reviewer leaves or joins                    | Block 4 + `review.lenses`                             | `BLOCK`                                   |
| A `success_90d` metric is missed                         | Block 5 + vertical priority (Phase D)                 | `WARN`                                    |
| Review capacity changes                                  | `review.capacity_hours_per_week` + pace recomputation | `BLOCK`                                   |
| A new locale is added to the site                        | `locales` + the language pack check (Phase C)         | `BLOCK` until the pack exists             |
| The site migrates: stack, rendering or domain change     | Phases A and B in full                                | `BLOCK`                                   |
| An active manual action appears                          | all work is suspended                                 | `BLOCK`                                   |
| 90 days have passed since the last profile revision      | quick reconciliation of every field                   | `INFO`                                    |

**ONB-22 · WARN · Revise the profile every 90 days.**
Rationale: in the owner's live system a strategy document was marked "Next Review: March 2026",
ran five months past due, and went on recommending markup types Google had already withdrawn.
A profile without a revision date rots silently. [internal observation, unpublished: §6.5]

---

## 7. Time budget

| Phase            | Machine time     | Human time                             | Money                     |
| ---------------- | ---------------- | -------------------------------------- | ------------------------- |
| A · collection   | 20–40 min        | 0                                      | $1–3 (SERP sweep + crawl) |
| B · gates        | ~2 min           | 0 (reading the report only on `BLOCK`) | $0                        |
| C · grill        | —                | **~30 min**                            | $0                        |
| D · confirmation | 2 min to prepare | **~10 min**                            | $0                        |
| **Total**        | ~45 min          | **~40 min**                            | **$1–3**                  |

Separately, outside the onboarding budget: enabling BigQuery bulk export and granting Search
Console access — both one-time actions on the owner's side.

**ONB-23 · INFO · If the grill ran longer than an hour, extractable material leaked into it.**
That signals a defect in the doctrine, not a peculiarity of the project: some question needs to
move from Phase C to Phase A. Such cases are logged and enter the rule-amendment queue under **P8**.

---

## 8. What code does, what the agent does, where a human is mandatory

| Step                                              | Code            | Agent    | Human                                    |
| ------------------------------------------------- | --------------- | -------- | ---------------------------------------- |
| Parsing `robots.txt`, sitemap, locales            | ✅              |          | confirms the locale list (§3)            |
| SSR/CSR check                                     | ✅              |          |                                          |
| Bot reachability and cloaking check               | ✅              |          |                                          |
| Crawling the corpus, building skeletons and graph | ✅              |          |                                          |
| Search Console export, baseline findings          | ✅              |          |                                          |
| SERP sweep, domain frequency                      | ✅              |          |                                          |
| Competitor classification across 5 classes        |                 | ✅       | confirms (ONB-19)                        |
| Clustering by SERP overlap                        | ✅              |          | confirms large-cluster boundaries (§4.2) |
| Identifying coverage gaps                         |                 | ✅       |                                          |
| Running Phase B eligibility gates                 | ✅              |          | reads the report on `BLOCK`              |
| Conducting the grill (Phase C)                    |                 | ✅       | **answers — mandatory**                  |
| Populating `project.yml`                          | ✅ from answers |          | **checks and signs off**                 |
| Computing the pace ceiling                        | ✅              |          | may only lower it                        |
| Vertical priority                                 |                 | proposes | **decides**                              |

The split follows the three-tier model: automation gets read-only, semi-automation creates a draft
from a single human action, and the manual tier is where the human acts and the system keeps state.
`nothing auto-publishes`. [internal observation, unpublished]

---

## 9. Prohibited

| Prohibition                                                         | Rationale                                                                                                                                                 |
| ------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Asking the owner anything the data can yield                        | D9. The answer will be worse than the data and will contaminate the inputs. Precedent: a single agent run found site defects the owner did not know about |
| Starting the grill before Phase A                                   | half the questions disappear, and the rest get sharper                                                                                                    |
| Accepting an empty field in any grill block                         | ONB-18. A gate that engages only on a filled field rewards silence                                                                                        |
| Onboarding a locale with no language pack in `doctrine/lang/`       | P5. Language-dependent rules would be absent or borrowed from another language — see the `locales` schema note                                            |
| Producing content in a language other than the target site's        | the doctrine is in English; the output is always in the site's own language(s)                                                                            |
| Onboarding a project that renders content client-side               | ONB-10, P12. AI crawlers do not execute JavaScript                                                                                                        |
| Onboarding a domain under an active penalty                         | ONB-14. Recovery takes 14+ months and is never complete                                                                                                   |
| Deploying on a repurposed expired domain                            | ONB-15, expired domain abuse                                                                                                                              |
| Publishing on someone else's domain outside its topic               | ONB-16. First-party involvement has not been a defence since 2024-11-19                                                                                   |
| Setting the publishing pace by hand above the verification capacity | P2                                                                                                                                                        |
| Using `llms.txt` as an onboarding metric                            | P12. 97% of such files were never requested even once                                                                                                     |
| Requiring special "AI-oriented" markup                              | P12. Officially, no such requirement exists                                                                                                               |
| Using stock imagery as proprietary media                            | it devalues the one verifiable visual asset; the prohibition is already in force in the live system [internal observation, unpublished]         |
| Measuring text length without Unicode segmentation                  | ONB-02, P5                                                                                                                                                |
| Publishing with an AI as the named author                           | Q4.1. Google: "probably not the best approach"; on news surfaces a byline is mandatory                                                                    |

---

## 10. Sources

**Internal**

- `doctrine/00-principles.md` — P2, P5, P11, P12, P13
- `EVIDENCE.md#e01-geo-answer-engines` — AI crawlers not rendering JavaScript; `robots.txt` granularity; the role of `Google-Extended`
- `EVIDENCE.md#e04-search-console` — Search Console API limits, the 16-month window, URL Inspection quota, the need for a first-party store
- `EVIDENCE.md#e05-semantics-and-clustering` — SERP overlap thresholds, over-merging as the dominant defect
- `EVIDENCE.md#e07-competitive-intelligence` — the five competitor classes, candidate thresholds, sweep cost, skeleton retention, the need for human-confirmed classification
- `EVIDENCE.md#e12-data-apis-and-pricing` — Jina Reader and Firecrawl limits and pricing, the crawl ladder
- `EVIDENCE.md#e13-policy-and-risk` — spam policies, the absence of a manual action for scaled content abuse, site reputation abuse and its cases, expired domain abuse, EU AI Act Article 50, the February 2026 Discover update
- `[internal observation, unpublished]` — the publishing-as-code pattern, the three action tiers, zero-fabrication, the genuine-case-study specification, acknowledgement of limits, negative results
- `grill/2026-08-07-brief-final.md` — decisions D1–D11

**External (via the reconnaissance reports)**

- [Spam policies for Google web search](https://developers.google.com/search/docs/essentials/spam-policies) — updated 2026-05-15
- [Creating helpful, reliable, people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content) — updated 2025-12-10
- [AI features and your website](https://developers.google.com/search/docs/appearance/ai-features)
- [Manual Actions report](https://support.google.com/webmasters/answer/9044175)
- [Google News content policies](https://support.google.com/news/publisher-center/answer/6204050)
- [EU AI Act Article 50](https://artificialintelligenceact.eu/article/50/) · [European Commission guidance, 2026-07-20](https://digital-strategy.ec.europa.eu/en/policies/guidelines-transparency-ai-generated-content)

---

## 11. Conflicts with the principles

Checked against `00-principles.md`. No direct contradictions found. Four points need attention at
the next revision:

1. **ONB-13 against P2.** The publishing channel gate permits `manual` mode as a `WARN` rather than
   a `BLOCK`. Formally this leaves room to operate without programmatic publishing, in which case
   several subsystems switch off. The choice is deliberate — otherwise Kiln cannot be deployed on
   projects with a closed admin panel — but it means that "full Kiln" and "Kiln in manual mode" are
   two different products making two different promises. That has to be stated plainly in the
   onboarding report, not in small print.

2. **ONB-10's 30% threshold is unsubstantiated.** It is marked as expert judgement. The fact that
   AI crawlers do not render JavaScript is proven; the specific boundary for "how much text must be
   in the raw HTML" is not. The first three onboardings must gather actual distributions, after
   which the threshold is calibrated and promoted into `thresholds.yml` under the P10 procedure.

3. **ONB-09 and §4.2 take thresholds from reconnaissance, where they are marked as an engineering
   proposal rather than an industry standard.** That is acceptable at the start, but in
   `thresholds.yml` they must sit as local and calibratable values; otherwise P10 is violated —
   numbers would end up in the shared doctrine without proof.

4. **Resolved 2026-08-07.** The language pack gate previously had no rule ID. It is now `ONB-24`
   (§3), carrying `BLOCK` per locale. Two related identifiers were minted at the same time in
   neighbouring files for the same reason: `CMP-27` in `03-competitors.md` and `MSR-22` in
   `08-measurement.md`.

Recorded separately, an observation outside this section's remit: **P13 requires a non-empty
`unique_value_source` on every page, and the source of those values is Block 3 of the grill.** If
Block 3 comes back empty, the whole project will be unable to pass the pre-publication gate — which
makes an empty Block 3 a blocking condition in effect, although it is nowhere named as one. I
suggest considering its promotion to `BLOCK` in `10-safety-gates.md`, where the gate itself lives.
