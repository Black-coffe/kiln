# Kiln Adapter Specification

**Layer 3 contract.** Version 0.1.0 · 2026-08-07 · Normative.

The adapter is the only part of Kiln written per project. Layers 1 and 2 (the doctrine and the
scripts) are copied verbatim and know nothing about your stack. This document defines exactly what
they expect from you, so that a stranger can implement it in a day or two without reading the rest
of the doctrine first.

Everything here defers to [`doctrine/00-principles.md`](../doctrine/00-principles.md). Where this
spec and the principles disagree, the principles win and this file is the bug.

---

## 1. Shape of the contract

The adapter is **one executable** in the consuming project:

```
.kiln/adapter/run        # executable, any language
```

Kiln invokes it as:

```bash
.kiln/adapter/run <operation> < request.json > response.json
```

One process per call. Request JSON on stdin, response JSON on stdout, diagnostics on stderr.

Why a process and not a library, an HTTP API or an MCP server:

- It is language-agnostic. A Python project writes Python, a Node project writes TypeScript, a
  static site writes a shell script over its own files. Kiln does not care.
- It is testable without Kiln. `echo '{}' | .kiln/adapter/run corpus.list | jq` is the whole test
  harness.
- It survives Claude Code's constraints. A plugin has no runtime of its own and cannot reach a
  database directly; everything that touches your data must be a process you own and Kiln shells
  out to. [source: EVIDENCE.md#e09-platform-capabilities]
- It keeps credentials in your process, not in Kiln's. See §5.

An MCP server is a legitimate alternative transport for the same operations, and is worth building
once the adapter is stable. Start with the process. The operation names, payloads and semantics in
this document are identical either way.

### 1.0 Declared configuration

Two values are read from `.kiln/project.yml` rather than discovered, and both are required before
any write path runs:

| Key                       | Meaning                                        |
| ------------------------- | ---------------------------------------------- |
| `publishing.content_root` | repo-relative path holding publishable content |
| `publishing.mode`         | `repo` \| `api` \| `db` \| `manual`            |

**`content_root` is declared, never inferred.** The publish gate
(`hooks/scripts/gate-publish.sh`) uses it to decide whether a given write is a publishing action,
and it **fails closed** when the value is absent. An earlier revision inferred the content root from
common directory names, which meant a project that renamed `content/` to `docs/` silently lost its
publication gate while every run still reported success. A guard that can be disabled by a rename is
not a guard.

For `mode: repo` this is a real directory. For `mode: api` or `mode: db` it is the logical path
prefix the adapter reports in `corpus.list` results, so that the same gate logic applies to
adapter-mediated writes without special-casing.

### 1.1 Request envelope

```json
{
  "operation": "corpus.list",
  "kiln_version": "0.1.0",
  "locale": "uk",
  "params": {},
  "dry_run": false
}
```

`locale` is always present when the project declares more than one. The adapter must treat locales
as separate namespaces: the same path in two locales is two distinct pages (P5).

### 1.2 Response envelope

Success:

```json
{
  "ok": true,
  "operation": "corpus.list",
  "data": {},
  "warnings": ["sitemap lastmod is unreliable, see field notes"]
}
```

Failure:

```json
{
  "ok": false,
  "operation": "content.publish",
  "error": {
    "code": "not_implemented",
    "message": "publishing is manual on this project",
    "retriable": false
  }
}
```

### 1.3 Exit codes

| Code | Meaning                                 | Kiln's behaviour                                                |
| ---- | --------------------------------------- | --------------------------------------------------------------- |
| `0`  | success, `ok: true` on stdout           | continue                                                        |
| `1`  | transient failure                       | retry with backoff, up to 3 attempts, then fail the step        |
| `2`  | permanent failure, bad input            | fail the step, surface `error.message` to the operator          |
| `3`  | operation not implemented               | disable the dependent modules, record it in the project profile |
| `4`  | authentication or authorisation failure | halt everything, never retry, never fall back to another path   |

Exit code `3` is not an error. It is how a project declares its conformance level (§6). Kiln reads
it once at `doctor` time and remembers.

### 1.4 Error codes

`not_implemented` · `not_found` · `invalid_input` · `conflict` · `auth_failed` · `rate_limited` ·
`upstream_unavailable` · `would_publish` (see `content.upsert`).

---

## 2. Operations

Each operation below states: what the doctrine calls it, why it exists, what breaks without it,
its input, its output, its errors, and its idempotency guarantee.

### 2.1 `corpus.list`

**Doctrine name:** corpus enumeration. **Conformance:** L0, mandatory.

**Why it exists.** Every module that reasons about the site as a whole reads this: the internal
link graph, cannibalisation control, the refresh queue, cohort measurement, the topical radius.
Without it Kiln is a text generator, not Kiln.

**What breaks without it.** ONB-12 is a `BLOCK`, so onboarding does not complete at all.

**Input:**

```json
{
  "locale": "uk",
  "since": "2026-05-01T00:00:00Z",
  "include_unpublished": false,
  "cursor": null,
  "limit": 500
}
```

`since` filters on the adapter's own notion of last change and is an optimisation only. An adapter
may ignore it; Kiln always tolerates a full listing.

**Output:**

```json
{
  "ok": true,
  "data": {
    "pages": [
      {
        "id": "1487",
        "url": "https://example.com/uk/kredyt-onlain",
        "path": "/uk/kredyt-onlain",
        "locale": "uk",
        "status": "published",
        "title": "Кредит онлайн: умови банків",
        "meta_description": "…",
        "headings": [
          { "level": 1, "text": "Кредит онлайн", "position_ratio": 0.02 },
          { "level": 2, "text": "Умови банків", "position_ratio": 0.18 }
        ],
        "word_count": 1840,
        "word_count_method": "unicode",
        "published_at": "2024-02-11T09:00:00Z",
        "updated_at": "2024-03-07T12:41:00Z",
        "updated_at_trusted": false,
        "canonical": "https://example.com/uk/kredyt-onlain",
        "robots": "index,follow",
        "schema_types": ["Article", "BreadcrumbList"],
        "author": { "name": "…", "url": "…", "same_as": [] },
        "internal_links": [
          {
            "href": "/uk/mikropozyka",
            "anchor": "мікропозика на картку",
            "zone": "body",
            "position_ratio": 0.31,
            "rel": null
          }
        ],
        "outbound_links": [
          { "href": "https://bank.gov.ua/…", "anchor": "НБУ", "rel": null }
        ],
        "content_hash": "sha256:9f2c…",
        "cluster_id": null,
        "kiln_managed": true
      }
    ],
    "cursor": "eyJvZmZzZXQiOjUwMH0",
    "total": 4075
  }
}
```

**Field notes, all of them load-bearing:**

- `word_count` must be computed with **Unicode-aware tokenisation**. This is P5 and it is not
  pedantry: `wc -w` does not split Cyrillic into words, and on a live measurement it reported an
  English locale as six times larger than a Ukrainian one when the two were at parity. The
  conclusion was exactly inverted. Set `word_count_method` to `"unicode"` when you have done this
  correctly and `"naive"` when you have not, so Kiln can refuse to compare locales.
- `position_ratio` is the character offset of the element divided by the length of the main text
  body, from 0.0 to 1.0. It exists because link placement and citation extraction both depend on
  position: links at the top of the body outperformed footer links roughly fivefold in controlled
  split tests, and 44.2% of LLM citations come from the first 30% of a document. Without this field
  the linking module cannot enforce its position rules and silently degrades to placing links
  anywhere.
- `zone` is one of `body`, `nav`, `footer`, `sidebar`, `related`, `breadcrumb`. Contextual links in
  `body` and navigational chrome must never be counted together, and a single adapter that lumps
  them is worse than one that returns `null`.
- `internal_links` and `outbound_links` are separate arrays because internal and external anchor
  profiles are evaluated separately (`SimplifiedAnchor` in the Content Warehouse leak) and the
  internal profile degrades independently of the external one.
- `kiln_managed` marks pages Kiln created or has permission to edit. Pages with `false` are read
  for the graph and never written to. Default `false` when in doubt.

**Errors:** `auth_failed`, `upstream_unavailable`. **Idempotency:** read-only, safe to call
repeatedly. Kiln calls it on every run.

### 2.2 `corpus.get`

**Doctrine name:** page fetch. **Conformance:** L0, mandatory.

**Why it exists.** `corpus.list` returns structure; the writing, review and linking modules need
the body. Separating the two keeps the full listing cheap on a 4,000-page site.

**What breaks without it.** N-gram overlap against existing pages, the cannibalisation similarity
check that runs _before_ a draft is written, and every internal-link placement.

**Input:** `{"id": "1487"}` or `{"path": "/uk/kredyt-onlain", "locale": "uk"}`.

**Output:**

```json
{
  "ok": true,
  "data": {
    "id": "1487",
    "format": "markdown",
    "body": "…",
    "body_html": "…",
    "frontmatter": {},
    "content_hash": "sha256:9f2c…"
  }
}
```

`format` is `markdown` or `html`. Return the format your project actually stores; do not convert
lossily to please the spec. If you store HTML, `body` may be a plain-text extraction and
`body_html` the source. Kiln uses `body` for text metrics and `body_html` for structural ones.

**Errors:** `not_found`, `auth_failed`. **Idempotency:** read-only.

### 2.3 `content.upsert`

**Doctrine name:** draft write. **Conformance:** L1.

**Why it exists.** It is the only way content enters the project, and it exists separately from
publishing so that `nothing auto-publishes` is enforced by the contract rather than by operator
discipline.

**What breaks without it.** Kiln runs in `audit_only`: it finds, plans and proposes, and produces
files you paste by hand. The review lenses still work; the linking waves and corpus refresh do not.

**Input:**

```json
{
  "locale": "uk",
  "slug": "kredyt-onlain-umovy",
  "title": "…",
  "meta_title": "…",
  "meta_description": "…",
  "excerpt": "…",
  "body": "…",
  "format": "markdown",
  "author_ref": "olena-k",
  "category_ref": "credits",
  "featured_image": { "url": "…", "alt": "…" },
  "structured": { "faq": [] },
  "kiln": {
    "brief_id": "b-2026-08-07-014",
    "review_log": ".kiln/reviews/kredyt-onlain-umovy.yml",
    "doctrine_commit": "a1b2c3d"
  }
}
```

**Output:** `{"ok": true, "data": {"id": "1602", "status": "draft", "url": "…", "created": true}}`

**Mandatory semantics:**

1. **Idempotent on `(locale, slug)`.** Existing page: update. No such page: create. Never create a
   second page with the same slug in the same locale, and never silently mint `slug-2`. Return
   `conflict` instead; a colliding slug usually means the cannibalisation check was skipped, and
   silently creating a near-duplicate is exactly the failure P6 exists to prevent.
2. **Defaults to unpublished, always.** Status after this call is `draft` regardless of what the
   page's status was before. If your CMS cannot create an unpublished page, return
   `not_implemented` rather than publishing; Kiln will drop you to L0 and say so in writing at
   onboarding, not a month later.
3. **Never flips a published page to live content.** Updating a published page through `upsert`
   must write to a draft revision if your stack supports revisions, and must return `would_publish`
   if it does not. Overwriting live content is `content.publish`'s job, not this one's.
4. **Partial updates are field-scoped.** Send only the fields present in the request. The reference
   implementation learned this the expensive way: its admin update uses
   `model_dump(exclude_unset=True)`, so a full-object PUT wiped an interactive checklist that lived
   in a field the writer never touched.
5. **Run the body through the project's own sanitiser**, the same one production uses, and verify
   that any structured extraction still succeeds before returning success. In the reference
   implementation the visual editor restructured `<pre>` and `<h3>` elements and broke the H2+H3
   contract that FAQ extraction depends on, silently. Check it in the adapter, not after publishing.

**Errors:** `conflict`, `invalid_input`, `would_publish`, `auth_failed`, `not_implemented`.

### 2.4 `content.publish`

**Doctrine name:** the publication act. **Conformance:** L2.

**Why it exists.** As a separate, explicit, auditable operation. Publishing is the one irreversible
step in the pipeline and P11 puts a human on it.

**What breaks without it.** Nothing in the analysis layer. The pipeline stops one step short and a
person clicks the final button; that is a legitimate configuration, recorded as
`publish.mode: manual`.

**Input:**

```json
{
  "locale": "uk",
  "slug": "kredyt-onlain-umovy",
  "expected_content_hash": "sha256:4d1a…",
  "approved_by": "vadym",
  "approved_at": "2026-08-07T14:20:00Z",
  "review_log": ".kiln/reviews/kredyt-onlain-umovy.yml"
}
```

**Mandatory semantics:**

1. **Never implied by `upsert`.** There is no `publish: true` flag anywhere in this spec. Two calls,
   two intents, two log entries.
2. **`expected_content_hash` is checked.** If the stored draft's hash differs from what the reviewer
   approved, return `conflict` and publish nothing. This closes the window where a draft is edited
   between review and publication, which would invalidate the review log and with it the AI Act
   Art. 50 exemption (P11).
3. **`approved_by` is required and must not be empty.** A gate that only fires when a field is
   filled rewards leaving it empty; this one fails closed.
4. **Idempotent.** Publishing an already-published page with a matching hash is a success with
   `{"changed": false}`, not an error.

**Errors:** `conflict`, `not_found`, `auth_failed`, `not_implemented`.

### 2.5 `content.link_update`

**Doctrine name:** link placement. **Conformance:** L3.

**Why it exists.** Internal linking waves modify existing published pages. They must change the
link and nothing else: not the publication date, not the modification date shown to users, not any
neighbouring field.

**What breaks without it.** The entire internal linking module, which is one of the three
subsystems the framework was built for. Kiln will still _propose_ link placements; a human applies
them by hand, and the throughput limits in the linking doctrine become irrelevant because human
throughput binds first.

**Input:**

```json
{
  "locale": "uk",
  "id": "1487",
  "expected_content_hash": "sha256:9f2c…",
  "operations": [
    {
      "action": "insert",
      "anchor": "мікропозика на картку",
      "href": "/uk/mikropozyka",
      "occurrence": 1,
      "zone": "body",
      "context_before": "…якщо потрібна невелика сума, ",
      "context_after": " оформлюється за 15 хвилин…"
    },
    { "action": "remove", "href": "/uk/stara-storinka" },
    { "action": "retarget", "href_from": "/uk/a", "href_to": "/uk/b" }
  ]
}
```

**Mandatory semantics:**

1. **Optimistic locking on `expected_content_hash`.** Mismatch returns `conflict` and changes
   nothing. Link waves run over hundreds of pages; a stale write here corrupts a page nobody is
   looking at.
2. **Anchoring by surrounding context, not by offset.** `context_before` and `context_after` are
   required for `insert` and are the primary match. If the context is not found verbatim, return
   `not_found` for that operation rather than inserting at a guessed position.
3. **Atomic per page.** Either all operations for the page apply, or none do.
4. **Touch nothing else.** In particular, do not bump a user-visible "updated" date for a link
   insertion. Manipulating dates without substantive change is named directly by Google as a red
   flag, and the semantic date estimate makes the discrepancy detectable.
5. **Idempotent.** Inserting a link that is already present at that anchor is a success with
   `{"changed": false}`. The reference implementation got this right by skipping the page when the
   target href already appeared in the body.

**Errors:** `conflict`, `not_found`, `invalid_input`, `not_implemented`.

### 2.6 `media.register` (optional)

**Conformance:** optional. **Why it exists.** Original screenshots, charts and photographs are the
cheapest source of the effort artefacts the writing gate demands. If Kiln cannot place an image,
the writer must reference an already-hosted URL.

**Input:** `{"path": "local/file.webp", "alt": "…", "locale": "uk"}`
**Output:** `{"ok": true, "data": {"url": "https://…", "id": "…"}}`
**Idempotency:** keyed on content hash of the file; re-registering the same bytes returns the same
URL.

**Not implemented is fine.** Kiln then requires `featured_image.url` to be supplied by a human, and
the effort-artefact manifest records the image as externally hosted.

### 2.7 `redirect.create` (optional, but see note)

**Conformance:** optional, **required for consolidation**. **Why it exists.** The cannibalisation
decision tree has three outcomes, and one of them is a 301. Without this operation that branch is
unavailable, and Kiln will only ever recommend differentiating pages, never merging them, which
biases the whole module toward keeping duplicates alive.

**Input:** `{"from": "/uk/old", "to": "/uk/new", "type": 301, "locale": "uk"}`
**Idempotency:** creating an identical redirect is a success with `{"changed": false}`. Creating a
conflicting one returns `conflict`; never silently overwrite an existing redirect, and never create
a chain. If `from` is already the target of another redirect, return `conflict` and let a human
resolve it.

**Reminder:** merges, redirects and deletions are irreversible actions on the existing corpus, and
P11 requires a human on every one of them. The adapter implements the capability; the doctrine
decides when it fires.

### 2.8 `sitemap.ping` (optional)

**Conformance:** optional, **strongly recommended**. **Why it exists.** IndexNow costs nothing, has
no meaningful rate limit, and is the cheapest possible reduction in time-to-indexation, which is one
of the eight leading indicators the pilot is measured on.

**Input:** `{"urls": ["https://…"], "locale": "uk"}`
**Idempotency:** re-pinging is harmless. Do not batch beyond your provider's documented limit.

If your project already pings on publish, implement this as a no-op returning
`{"changed": false, "reason": "handled by application"}` rather than returning `not_implemented`,
so the doctor can tell "handled elsewhere" from "not handled at all".

---

## 3. The content hash

**`content_hash` is the change-detection primitive. `updated_at` is not.**

Compute it as:

1. Take the main content body only. Exclude navigation, footer, sidebars and any block whose text
   varies per request.
2. Normalise to Unicode NFC.
3. Collapse all runs of whitespace to a single space; trim.
4. `sha256`, hex, prefixed `sha256:`.

Return the same value from `corpus.list` and `corpus.get` for the same page state. The prefix is
there so a future algorithm change is visible rather than silent.

**Why `updated_at` cannot be trusted.** On a live site examined during this project's research,
`dateModified` was generated at request time: two fetches 27 seconds apart returned 09:27:09 and
09:27:36, and 54 of 58 blog entries carried the current day's `lastmod` in the sitemap. Any change
detector built on that field reports the entire corpus as changed on every run, forever. A second
site in the same research had `lastmod` on only 18% of its 4,075 URLs, which fails the same
detector from the opposite direction.

The rule Kiln applies: if more than 50% of pages report `updated_at` equal to the date of the run,
the field is generated, `updated_at_trusted` is forced to `false`, and everything downstream
switches to `content_hash`. Set `updated_at_trusted` honestly in your adapter and Kiln will not have
to guess.

---

## 4. State contract

**`.kiln/` lives in the consuming project's git repository, as human-readable JSON and YAML,
reviewable in a pull request.**

```
.kiln/
├── project.yml          profile: locales, niche, prohibited claims, pace, conversion
├── thresholds.yml       locally calibrated thresholds, never promoted to the shared doctrine
├── corpus.json          corpus map
├── links.json           link graph edges
├── anchors.json         anchor registry, keyed per locale
├── semantics/           keyword core, clusters, query edge graph
├── competitors/         competitor profiles and snapshots
├── plan.yml             content plan and its capacity ceiling
├── reviews/             human review logs, one file per slug
├── measurements/        Search Console exports and derived findings
├── rules-stats.json     per-rule applied and overridden counters
└── adapter/run          your adapter (the only executable here)
```

**Why files in git and not a database.** Three separate obligations collapse into this one decision:

1. **The review log must be diffable.** The EU AI Act Art. 50 exemption rests on demonstrating
   substantive human examination. A row in a database that someone can update in place is not
   evidence; a signed commit showing who changed what, when, and what they actually altered, is. A
   log that cannot be audited independently is a log that looks like an exemption without being one.
2. **The doctrine's history must be diffable.** P10 requires that rule changes arrive as pull
   requests carrying evidence, and P8 requires counting how often each rule fires and is overridden.
   Both are trivial when the state is text in git and awkward everywhere else.
3. **Rollback must be free.** A bad linking wave, a miscalibrated threshold, a cluster merge that
   turned out wrong: `git revert` is the recovery procedure, and it only exists if the state is in
   the repository.

**SQLite is permitted, as derived data only.** A local cache at `.kiln/cache/kiln.db` is fine and
often necessary for a large corpus. It must be:

- listed in `.gitignore`;
- fully rebuildable from the files with a single command, with no information that exists only
  inside it;
- never the source of truth for anything a human reviews.

If you find yourself wanting to store a review verdict or a doctrine amendment in SQLite, that is
the signal that the design has drifted. Put it in a file.

**Size note.** On a 4,000-page corpus, `corpus.json` runs to a few megabytes and diffs poorly. Split
it per locale and sort keys deterministically so that a run with no changes produces an empty diff.
A noisy diff trains reviewers to skip the file, and a skipped file is an unenforced gate.

---

## 5. Credentials

**Environment variables only. Never in `.kiln/`. Never in the repository.**

The adapter reads what it needs from its own environment and Kiln never sees a secret. This is not
just hygiene: `.kiln/` is committed to git by design, so anything placed there is published to
everyone with repository access, and on a public repository, to everyone.

Adopt the reference implementation's posture, which was built by someone who had already been
burned:

- **Default target is localhost.** Hitting production requires an explicit flag or an explicit
  environment.
- **Default status is draft.** Publishing requires the separate operation and the separate
  credential check.
- **Production credentials require both variables to be present.** Absence is a hard failure with
  exit code `4`, never a fallback to a staging path and never a silent no-op.
- **Read-only scopes wherever a read-only scope exists.** The reference implementation's Search
  Console integration carries the comment "No write scopes ever". Copy that.

Claude Code's plugin config can hold secrets via `userConfig` with `sensitive: true`, but note two
constraints before relying on it: values are refused in shell-form hook commands and monitor
commands, so they must be read from `CLAUDE_PLUGIN_OPTION_<KEY>` in the process environment; and the
credential store is shared with OAuth tokens and capped at roughly 2 KB, so a Google service-account
JSON does not fit and must be referenced by file path instead. [source: EVIDENCE.md#e09-platform-capabilities, §14.11–12]

---

## 6. Conformance

### 6.1 Levels

| Level  | Operations                                 | Unlocks                                                                                                                                         |
| ------ | ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **L0** | `corpus.list`, `corpus.get`                | Corpus map, cannibalisation detection, gap analysis, competitor intelligence, Search Console analysis, all leading indicators, the audit report |
| **L1** | + `content.upsert`                         | Briefs, drafting, the writing gate, all four review lenses, the review log                                                                      |
| **L2** | + `content.publish`                        | The full publication loop, cohort measurement of Kiln-produced pages, the fast learning loop                                                    |
| **L3** | + `content.link_update`, `redirect.create` | Internal linking waves, anchor registry enforcement, cannibalisation consolidation, corpus refresh at scale                                     |

**L0 is the minimum. Kiln refuses to run below it**, because `corpus.list` and `corpus.get` are what
ONB-12 checks and ONB-12 is a `BLOCK`.

Optional throughout: `media.register`, `sitemap.ping`.

### 6.2 What you lose at each stop

**Stopping at L0.** You get a genuinely useful product: a full audit, a prioritised task list, a
cannibalisation report, competitor gaps, and weekly leading indicators. You get no content
production at all. For a site like the pilot, with 4,075 existing URLs and 29 months of neglect,
L0 alone is worth more in the first quarter than L2 would be, because the first valuable run is
repair, not publication.

**Stopping at L1.** You get the whole editorial pipeline and a human publishes the result by hand.
Cost: the publication act leaves no machine-readable record beyond what the human remembers to
write down, so the medium learning loop (indexation and first positions attributed to a specific
draft) degrades to manual bookkeeping and usually stops within a month.

**Stopping at L2.** Everything works except maintenance of the existing corpus. Cost: the internal
link graph can be measured but not repaired, orphan pages stay orphaned, the one-anchor-one-URL
invariant can be reported but never enforced, and the cannibalisation decision tree loses its 301
branch, biasing every recommendation toward keeping duplicate pages alive. On a large existing site
this is the difference between a framework that improves what you have and one that only adds to it.

### 6.3 Conformance test

Ship this with your adapter and run it in CI:

```bash
# L0
echo '{"locale":"uk","limit":1}' | .kiln/adapter/run corpus.list  | jq -e '.ok and (.data.pages|length>0)'
echo '{"locale":"uk","limit":1}' | .kiln/adapter/run corpus.list  | jq -e '.data.pages[0].content_hash|startswith("sha256:")'
echo '{"locale":"uk","limit":1}' | .kiln/adapter/run corpus.list  | jq -e '.data.pages[0].word_count_method=="unicode"'

# Idempotency: two identical listings agree on hashes
diff <(echo '{"locale":"uk"}' | .kiln/adapter/run corpus.list | jq -S '.data.pages|map({path,content_hash})') \
     <(echo '{"locale":"uk"}' | .kiln/adapter/run corpus.list | jq -S '.data.pages|map({path,content_hash})')

# L1: upsert must not publish
echo '{"locale":"uk","slug":"kiln-conformance-probe","title":"probe","body":"probe","format":"markdown"}' \
  | .kiln/adapter/run content.upsert | jq -e '.data.status=="draft"'

# L2: publishing with a stale hash must fail
echo '{"locale":"uk","slug":"kiln-conformance-probe","expected_content_hash":"sha256:0000","approved_by":"ci"}' \
  | .kiln/adapter/run content.publish | jq -e '.ok==false and .error.code=="conflict"'
```

The third assertion is not optional politeness. An adapter that reports `naive` word counts makes
every cross-locale comparison in the framework wrong, and wrong in a direction that looks plausible.

---

## 7. Honest limitations

Things this contract cannot fix, stated plainly so nobody discovers them in week three:

- **Kiln cannot verify that an effort artefact is genuine.** It can verify that a file is attached,
  that its hash matches, and that a human is named as its creator. Whether the screenshot is real is
  outside any machine's reach.
- **Kiln cannot detect that your adapter lies.** If `corpus.list` omits pages, every graph metric is
  computed on a partial corpus and will look fine. The conformance test checks shape, not
  completeness. Compare `data.total` against your own sitemap count at least once.
- **There is no inbound webhook into a running session.** Nothing in this contract is event-driven.
  Everything is pull, on a schedule you control. See INTEGRATION.md §5.
- **The adapter runs with your credentials.** Kiln invokes it through the shell, and a plugin is a
  highly trusted component that executes arbitrary code with your privileges. Review the adapter the
  way you would review a deployment script, because that is what it is.
