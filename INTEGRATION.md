# Integrating Kiln

**How to wire Kiln into an existing project in one to two days.**

This guide assumes you have never read the doctrine. You do not need to. Work through it in order,
and read [`doctrine/00-principles.md`](doctrine/00-principles.md) once the framework is running and
you want to know why it refuses things.

Prerequisites: a git repository, Claude Code, and either Python 3.11+ or Node 20+ for the layer 2
scripts. Search Console access for the property. That is all.

---

## Hour 0: eligibility

**Do this before installing anything.** Five checks, roughly fifteen minutes. If any of the first
three fails, Kiln will not run and you would spend a day discovering that.

Set your target once:

```bash
export URL="https://example.com/some-real-content-page"
export ORIGIN="https://example.com"
```

### 1. Server-side rendering (ONB-10, blocking)

AI crawlers do not execute JavaScript. A client-rendered site stays perfectly visible to Google
and is completely invisible to ChatGPT, Claude and Perplexity, which is the failure mode nobody
notices because the Google numbers look normal.

```bash
curl -sL -A "OAI-SearchBot/1.0" "$URL" \
| python3 -c "import sys,re;h=sys.stdin.read();h=re.sub(r'(?is)<(script|style|noscript).*?</\1>',' ',h);print(len(re.sub(r'(?s)<[^>]+>',' ',h).split()))"
```

Compare that number to the word count you see in the browser. Below roughly 30% of the rendered
text, this is a `BLOCK`: fix rendering first. Next.js, Nuxt, Astro and Remix all ship server
rendering; the usual cause is a content area deliberately hydrated on the client.

### 2. AI crawler reachability (ONB-11, blocking)

The granularity here is the single most commonly confused point in the whole field. `GPTBot` is the
training crawler and blocking it is a legitimate business decision with no effect on ChatGPT
visibility. `OAI-SearchBot` is the search crawler and blocking it makes you invisible. `ClaudeBot`
is not `Claude-SearchBot`. People block the wrong one constantly.

```bash
curl -s "$ORIGIN/robots.txt" | grep -iE "OAI-SearchBot|Claude-SearchBot|PerplexityBot|GPTBot|ClaudeBot|Google-Extended|CCBot|Googlebot"

for UA in "Googlebot/2.1" "OAI-SearchBot/1.0" "PerplexityBot/1.0" "Claude-SearchBot/1.0" "Mozilla/5.0"; do
  printf '%-24s ' "$UA"
  curl -s -o /dev/null -w '%{http_code} %{size_download}\n' -A "$UA" "$URL"
done
```

All five must return `200`. Body sizes must match: a bot receiving a materially different page from
a browser is a cloaking indicator and a separate blocker. A CDN bot-management rule is the usual
culprit, not robots.txt.

### 3. Programmatic corpus access (ONB-12, blocking)

Any one of these is sufficient: content files in the repository, a readable API, database read
access, or a complete and correct sitemap.

```bash
curl -s "$ORIGIN/robots.txt" | grep -i sitemap
curl -s "$ORIGIN/sitemap.xml" | grep -c "<loc>"
```

**Recurse into sitemap index files.** A first pass on the pilot site read 308 URLs from what turned
out to be an index; the real number was 4,075. Everything downstream, coverage, cohorts, linking
throughput, was wrong by a factor of thirteen until that was caught.

### 4. Publishing channel (ONB-13)

You need a programmatic way to create a page **in draft** and a **separate** way to publish it. If
publishing is only possible by hand through an admin panel, that is a warning rather than a blocker,
recorded as `publish.mode: manual`. Know now what it costs: automated internal linking and bulk
corpus refresh are switched off in that mode. That is written here rather than discovered in week
four.

### 5. Active penalty (ONB-14)

Open Search Console, Security and Manual Actions. An active manual action means fix that first.

One caveat worth internalising: **there is no manual action for scaled content abuse.** It does not
appear in that report because it does not exist as a manual action; enforcement is algorithmic and
silent. A clean Manual Actions page is necessary, not sufficient. Kiln's cohort monitor exists
precisely because this class of penalty never announces itself.

---

## Day 1: wiring

### 1.1 Install the plugin

Declaratively, committed to the repository so the whole team gets it:

```json
// .claude/settings.json
{
  "extraKnownMarketplaces": {
    "kiln": { "source": { "source": "github", "repo": "<org>/kiln" } }
  },
  "enabledPlugins": ["kiln@kiln"]
}
```

Each team member is prompted to install on first trusting the folder. Or imperatively:

```bash
claude plugin marketplace add <org>/kiln
claude plugin install kiln@kiln --scope project
```

Committing it to `.claude/settings.json` is not cosmetic. Cloud sessions and scheduled runs do not
read `~/.claude/skills/` and do not inherit user-scope plugins; anything that must work in CI has to
be declared in the repository. [source: EVIDENCE.md#e09-platform-capabilities, §14.7]

### 1.2 Create the state directory

```bash
mkdir -p .kiln/adapter
cp -r "$(claude plugin path kiln)/state/." .kiln/
printf '.kiln/cache/\n' >> .gitignore
```

`.kiln/` is committed. `.kiln/cache/` is not. See [`adapter/SPEC.md` §4](adapter/SPEC.md) for why
this is load-bearing rather than a preference.

### 1.3 Write `project.yml`

The fields Kiln refuses to start without: locales, publishing pace, review capacity, prohibited
claims, conversion definition.

```yaml
site: https://example.com
locales:
  - code: uk
    path_prefix: /uk
    language_pack: uk # doctrine/lang/uk.md must exist, else BLOCK
    primary: true
  - code: en
    path_prefix: /en
    language_pack: en

ymyl: true # finance, health, legal, safety: raises every gate

publish:
  mode: api # api | manual
  pace_source: review_capacity # never a fixed number

review:
  lenses:
    facts: { reviewer: vadym, hours_per_week: 3 }
    domain:
      { reviewer: yura, hours_per_week: 3, qualification: "CFO, 12y banking" }
    voice: { reviewer: reviewer-3, hours_per_week: 2 }
    usefulness: { reviewer: oleksii, hours_per_week: 2 }
  approver: editor-1 # must not be one of the lenses on the same draft

conversion: lead_form_submit
```

**On language.** The doctrine, the skills and this guide are English. The content is not. Declare
your locales here and Kiln loads `doctrine/lang/<code>.md` for each; nothing in an English doctrine
implies English output. A locale with no language pack is a blocker, because the alternative,
falling back to English rules, is actively harmful: the "high dash density indicates AI authorship"
rule is correct for English and grammatically wrong for Cyrillic, where the dash is obligatory in
the «Х — це У» construction. That mistake has already been made once, converting 349 correct
occurrences into commas.

### 1.4 Implement the minimum adapter

Two operations, `corpus.list` and `corpus.get`. Read [`adapter/SPEC.md`](adapter/SPEC.md) §2.1 and
§2.2 for the exact fields. Skeleton:

```python
#!/usr/bin/env python3
# .kiln/adapter/run   (chmod +x)
import json, sys, hashlib, unicodedata, regex

def wc(text):                       # Unicode-aware, see SPEC §2.1
    return len(regex.findall(r'\p{L}[\p{L}\p{M}\p{Pd}\']*', text))

def content_hash(text):
    n = unicodedata.normalize('NFC', text)
    n = ' '.join(n.split())
    return 'sha256:' + hashlib.sha256(n.encode()).hexdigest()

def corpus_list(p):
    pages = []                      # ← your query goes here
    return {"pages": pages, "cursor": None, "total": len(pages)}

OPS = {"corpus.list": corpus_list}

op = sys.argv[1]
req = json.load(sys.stdin)
if op not in OPS:
    print(json.dumps({"ok": False, "operation": op,
                      "error": {"code": "not_implemented", "retriable": False}}))
    sys.exit(3)
print(json.dumps({"ok": True, "operation": op, "data": OPS[op](req.get("params", {}))},
                 ensure_ascii=False))
```

Exit code `3` for unimplemented operations is how the project declares its conformance level. It is
not an error.

Get `word_count_method: "unicode"` right on the first pass. `wc -w` does not split Cyrillic into
words; during this project's research it reported an English locale as six times larger than a
Ukrainian one when the two were at parity, and the conclusion drawn from it was exactly backwards.

### 1.5 Run the doctor

```bash
claude
> /kiln:doctor
```

It re-runs the Hour 0 gates, probes every adapter operation, records the conformance level, and
prints what each missing operation costs you. Expect L0 on day one. That is the correct place to be.

---

## Day 2: first useful output, and not one new article

```bash
> /kiln:onboard
```

Two phases. Kiln first gathers everything derivable from data on its own: the corpus map, technical
defects, the Search Console history, a SERP sweep of your seed terms, the competitor set. Then it
asks you the things that cannot be derived, in about forty minutes: what you are forbidden to claim,
where your product is genuinely worse than a competitor's, what proprietary data you hold, who signs
the articles, and what counts as a conversion.

It asks only the second set. Everything in the first set it brings you already answered, for
confirmation. Forty minutes rather than three hours, and the answers are better because they came
from measurement instead of recollection.

Then:

```bash
> /kiln:audit
```

**Write nothing new this week.** This is a deliberate instruction, not a cautious one.

On the pilot site, the audit surfaced this without a single new page being written: 2022 in the
title tags of pages competing against rivals showing 2026; `lastmod` present on 18% of 4,075 URLs;
no `author` and no `dateModified` in the schema of a YMYL finance site that already employs three
credentialed external experts; hreflang pairs broken between locales, 169 Ukrainian pages against 70
Russian in one section; 207 template link occurrences per article against 6 genuine editorial links
between related articles. A parallel site had two case-study pages sharing one title and one meta
description, and slugs truncated mid-word with collision suffixes.

None of that requires new content. All of it is repair, all of it is measurable in Search Console
within weeks rather than months, and none of it carries publication risk. Meanwhile the corpus map,
the cluster assignments and the link graph get built and validated on real data before anything
depends on them.

There is a second reason. Leading indicators need a baseline, and a baseline taken after you start
publishing is not a baseline. Your existing pages are also the cleanest control cohort you will ever
have: cohort measurement compares Kiln-produced pages against `pre-kiln` ones, and a site with
thousands of pre-existing URLs hands you that control group for free. A new site never gets one.

---

## Week 1 onward

**Wire the review lenses.** Four checklists, four people, one zone each, binary answers. They work
blind to each other until reconciliation, because seeing another verdict first anchors yours and
destroys the disagreement signal, which is the fastest learning input the framework has. Do not
compress this into "everyone reads everything": that is one class of defect found four times instead
of four classes found once, and it burns out inside a month. The precedent is on record in the
reference implementation's own documentation: "the weekly calendar ran for one week and stopped."

**Wire the gates.** Advisory gates do not hold. The reference implementation says so in its own
roadmap, where the enforcing hook is listed as not built and the whole system consequently rests on
one person's discipline. Kiln ships `hooks/hooks.json` with a `PreToolUse` hook that denies writes to
content paths when the brief, the cluster binding, the cannibalisation check or the effort artefact
is missing. Enable it on day one, before anyone has a habit to protect.

**Set the publishing pace.** Not a number you like. `capacity` is computed from actual review logs,
using the slowest lens rather than the sum of hours, at the 80th percentile rather than the median,
because the ceiling has to survive a bad week. Until 30 logs exist the pace stays at whatever you
agreed verbally, and Kiln says so rather than pretending to have measured it.

**Schedule the recurring jobs.** See below.

---

## Scheduling reality

Be clear-eyed about this, because the obvious design does not work.

**Inbound webhooks into a running Claude Code session are effectively unavailable.** The Channels
mechanism exists, but during its research preview it accepts only plugins on Anthropic's allowlist,
requires claude.ai or Console authentication, is unavailable on Bedrock, Google Cloud and Microsoft
Foundry, and delivers events only while a session is open. A third-party channel will not run in
production today. [source: EVIDENCE.md#e09-platform-capabilities]

Four scheduling mechanisms exist and none is universal:

| Mechanism               | Runs where    | Needs your machine on | Local files | Minimum interval |
| ----------------------- | ------------- | --------------------- | ----------- | ---------------- |
| GitHub Actions          | GitHub runner | no                    | fresh clone | cron             |
| Desktop scheduled tasks | your machine  | yes, app open         | yes         | 1 minute         |
| Cloud routines          | Anthropic     | no                    | fresh clone | 1 hour           |
| `/loop`                 | your machine  | yes, session open     | yes         | 1 minute         |

**Use GitHub Actions.** It is the only option that runs unattended, needs nobody's laptop, and
operates on the repository, which is where Kiln's state lives anyway.

```yaml
# .github/workflows/kiln.yml
name: Kiln
on:
  schedule:
    - cron: "0 6 * * *" # daily: sitemap diff, competitor watch, hourly GSC archive
    - cron: "0 7 * * 1" # weekly: full analysis and leading indicators
  workflow_dispatch:

jobs:
  run:
    runs-on: ubuntu-latest
    permissions: { contents: write, pull-requests: write }
    steps:
      - uses: actions/checkout@v6
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          plugin_marketplaces: "https://github.com/<org>/kiln.git"
          plugins: "kiln@kiln"
          prompt: "/kiln:audit --scheduled"
          claude_args: |
            --allowedTools "Read,Write,Edit,Bash,WebSearch,WebFetch"
        env:
          KILN_ADAPTER_MODE: readonly
          GSC_CREDENTIALS: ${{ secrets.GSC_CREDENTIALS }}
      - name: Open PR with findings
        run: |
          git diff --quiet .kiln/ || {
            git checkout -b "kiln/$(date +%Y-%m-%d)"
            git add .kiln/ && git commit -m "kiln: scheduled sweep"
            gh pr create --fill
          }
```

Notes that will save you an afternoon:

- **Findings arrive as a pull request, not as a commit to the default branch.** The diff is the
  report. This is the same mechanism that makes review logs auditable.
- `KILN_ADAPTER_MODE: readonly` keeps scheduled runs at L0. Scheduled publication is not a feature
  worth having, and Claude Code agrees: since v2.1.196 skills marked `disable-model-invocation` do
  not run on a schedule, which covers `/kiln:write` and `/kiln:onboard` by design. There is no
  publish skill at all: publication runs through the adapter behind the pre-publication gate
  (`10-safety-gates.md` SAF-20), never through a prompt.
- GitHub runs scheduled workflows only from the default branch, and disables the schedule on public
  repositories after 60 days without activity.
- The daily job archives Search Console hourly data because that data lives for eight days and then
  disappears permanently. Miss a week and the newsjacking window detector has no history to compare
  against, forever.

**Desktop scheduled tasks** are the alternative when a job genuinely needs local files that are not
in the repository. They need the desktop app open and the machine awake, and after a sleep they
replay exactly one missed run.

**Cloud routines** have an API trigger, which is the closest thing to a webhook available. It opens
a fresh cloud session with a clean clone and no local files, the minimum interval is one hour, and
the payload arrives wrapped as untrusted data that the routine's prompt must reference explicitly or
it is inert. Useful for "a competitor published something, go look". Not useful for anything that
needs your working tree.

---

## Stack notes

**Python (FastAPI, Flask, Django).** The reference implementation is FastAPI plus Postgres and the
adapter is a thin wrapper over the existing admin API rather than raw SQL. Do the same: go through
your application's own layer so the content passes the same sanitiser production uses. That
implementation's hard-won lesson is worth copying verbatim: it converts drafts through the real
sanitiser and asserts that structured extraction still succeeds _before_ uploading, because the
visual editor silently restructured `<pre>` and `<h3>` elements and broke the heading contract that
FAQ extraction depended on. Send partial updates only; a full-object PUT there once wiped a field the
writer had never touched.

**Node and TypeScript.** Same shape. If you use a headless CMS client, wrap it rather than exposing
it: the adapter contract is smaller than any CMS SDK and the narrowness is the point.

**Headless CMS (Contentful, Sanity, Strapi, Payload).** `corpus.list` maps to a content query,
`content.upsert` to a draft entry, `content.publish` to the publish action, which every one of these
exposes separately. `content.link_update` is the hard one, because bodies are usually rich-text ASTs
rather than markdown: implement it as an AST walk matching on `context_before` and `context_after`,
never on character offsets. Do not round-trip through markdown; you will lose embedded blocks.

**Static site generators (Hugo, Astro, Eleventy, Jekyll).** The easiest case and the one with the
best properties. `corpus.list` walks `content/**/*.md` and parses frontmatter; `content.upsert`
writes a file with `draft: true`; `content.publish` flips the flag; `content.link_update` edits the
markdown in place. The whole adapter is around 150 lines, publication is a commit, and the review log
sits in the same pull request as the article. `redirect.create` appends to your host's redirects
file.

**WordPress.** The REST API covers `upsert` (`status: draft`) and `publish` (`status: publish`)
directly. Content arrives as HTML, so return it in `body_html` and supply a text extraction in
`body`. A commercial SEO plugin already handles schema, sitemaps and Search Console; do not rebuild
that layer, point the adapter at it.

---

## Troubleshooting

**`corpus.list` returns far fewer pages than the site has.** You are reading a sitemap index as if
it were a sitemap. Recurse. This exact error understated a corpus by a factor of thirteen during
research.

**Every page shows as changed on every run.** Your `updated_at` is generated at request time. On one
live site, two fetches 27 seconds apart returned different `dateModified` values and 54 of 58 blog
entries carried the current day's `lastmod`. Set `updated_at_trusted: false` and let `content_hash`
do the work.

**Cross-locale metrics look absurd.** Almost always `word_count_method: "naive"`. Cyrillic, Greek,
Hebrew, Arabic, CJK: `wc -w` gets all of them wrong, and the failure looks like a real finding.

**The publish gate blocks everything.** Usually correct behaviour, usually `unique_value_source`.
The field is populated from the proprietary-assets block of the onboarding interview, and if that
block came back thin, every draft will fail this gate until you have something real to put in it.
That is the system working. The fix is upstream, in what you can actually claim to know that nobody
else does.

**Freshness rules flag most of the corpus at once.** Expected on a neglected site, and the threshold
is uncalibrated on day one. Run in observe mode first, look at the distribution, then set the
threshold. Do not lower a rule to fit the corpus before you have seen the numbers.

**The linking module wants years to cover the corpus.** Real arithmetic, not a bug: a 10% cap per
wave against a four-to-twelve week measurement window puts a 4,000-URL site at a year or more.
Parallel waves across unrelated clusters are the usual answer, but verify the clusters really are
unrelated first, because a shared pillar page breaks the independence the measurement depends on.

**Claude Code does not see the plugin.** Check that the marketplace was trusted, then
`/reload-plugins`. In CI, parse the `system/init` event from `--output-format stream-json` and fail
the job when `plugin_errors` is non-empty. A silently unloaded plugin produces a run that looks
successful and does nothing.

**A project-level agent silently overrides a Kiln agent.** Plugin agents have the lowest priority of
all five scopes, so an identically named file in `.claude/agents/` wins without warning. Rename
yours.

**A scheduled run behaves differently from an interactive one.** Background subagents lose most
built-in tools, and background has been the default since v2.1.198. If an agent needs a tool outside
that reduced set, it must declare `background: false`.
