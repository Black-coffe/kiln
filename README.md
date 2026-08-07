# Kiln

**A portable content doctrine for search and AI answer engines.**

Kiln is not a program and not a SaaS. It is a body of rules, thresholds, procedures and
prohibitions that you clone and wire into an existing project, at the level of that project's own
code, in a day or two.

The name is literal. A kiln fires raw material: a draft passes through the gates and either comes
out hard or is rejected. **The value of the system is in the rejection, not the generation.**

- License: MIT
- Status: 0.1.0, pre-release. Read [Status and maturity](#status-and-maturity) before adopting.

---

## Status and maturity

Kiln is new. This section exists because overselling maturity is precisely the failure mode
`doctrine/00-principles.md` spends a section on, and a README that did it would discredit the rest.

| Area             | State                                                                                                                      |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Doctrine         | 12 sections, ~250 rules with IDs and severities. Written and internally consistent.                                        |
| Evidence base    | `EVIDENCE.md`, ~200 external sources with dates and evidence classes.                                                      |
| Thresholds       | **Every one is uncalibrated.** Marked `[expert judgement, needs calibration]` throughout.                                  |
| Layer-2 scripts  | **6 of 26 written.** The rest exist as specifications inside the doctrine.                                                 |
| Language packs   | English and Ukrainian. The Ukrainian pack is entirely hypotheses: no research on machine-text markers in Ukrainian exists. |
| Live validation  | **None.** Nothing here has been run against a production site. All tests run on fixtures.                                  |
| Plugin packaging | Complete: 9 skills, 5 agents, 5 hooks.                                                                                     |

**What this means in practice.** Run Kiln in `--observe` mode until you have your own
distributions. A gate that blocks on a guessed number teaches people to bypass gates, which is
worse than having no gate. The doctrine says this itself; the software defaults to it.

**The reference pilot.** Thresholds and worked examples throughout the doctrine refer to "the
reference pilot", a single project the framework was designed against: a Ukrainian-language
financial marketplace of roughly 4,000 URLs, YMYL by classification, with an editorial hiatus of
about two years and five bylined authors of whom three are external subject-matter experts. Those
properties are stated because they explain why particular thresholds were chosen. Where your
project differs, the threshold is probably wrong for you: that is what calibration is for.

---

## Why, when there are already hundreds of content generators

Existing tools solve the problem of writing text. That problem is now cheap. The expensive problem
is not killing the project with the text you wrote.

Three facts Kiln is built around:

1. **54% of domains served by AI content platforms lost more than a third of their traffic**
   (Lily Ray, 220+ client domains, 2026; `EVIDENCE.md#e14-content-operations` §2). The trajectory is always the same:
   6–12 months of growth, a peak, then a collapse below the starting point. Most collapses
   happened after the vendor published a case study celebrating that same site.
2. **Tools that measure "content quality" are measuring similarity to the top of the SERP.**
   The correlation between their score and ranking position is 0.28 on Surfer's own data, and
   17.5% for Clearscope (`EVIDENCE.md#e11-content-quality-signals`). Information gain is divergence from the top, not agreement
   with it.
3. **Every existing Claude Code extension in this class is an analyzer without memory.**
   They hold no site state, learn nothing from Search Console, and do not adapt between runs.

Kiln inverts all three: gates outrank the writer, project memory outranks any single run, and the
rules themselves get measured the same way pages do.

---

## Three layers

| Layer           | What it is                                                                    | Portability | Where it lives                              |
| --------------- | ----------------------------------------------------------------------------- | ----------- | ------------------------------------------- |
| **1. Doctrine** | rules, thresholds, prohibitions, procedures, prompts, skills, agents, hooks   | 100%        | `doctrine/`, `skills/`, `agents/`, `hooks/` |
| **2. Scripts**  | autonomous utilities: CSV/JSON in, JSON out. They know nothing about any site | 100%        | `scripts/`                                  |
| **3. Adapter**  | corpus reads, publishing, credentials: the only part written per project      | 0%          | in your project, per `adapter/SPEC.md`      |

Layers 1 and 2 are copied verbatim. Layer 3 is written in a day or two against the spec. This is
exactly why Kiln does not ship as an API: a universal API is pointless, because the consuming
project has to be modified either way, so it is cheaper to write the integration straight against
that project.

### Doctrine language vs content language

The doctrine, all instructions, skills, agents and documentation are written in English. The
_content_ Kiln produces is always written in the language of the target site: one language or
several, as declared in `.kiln/project.yml`. The language pack under `doctrine/lang/<code>.md` is
selected by the project's locale, never by the doctrine's own language. A project running on a
Ukrainian site loads `uk.md`; nothing in the English doctrine implies English output.

---

## Repository layout

```
kiln/
├── README.md                      this file
├── INTEGRATION.md                 how to wire Kiln into your project in 1–2 days
├── LICENSE                        MIT
├── .claude-plugin/
│   └── plugin.json                Claude Code plugin manifest
│
├── doctrine/                      LAYER 1, the body of rules
│   ├── 00-principles.md           hard principles, the root of everything
│   ├── 01-onboarding-grill.md     what to ask the owner, what to gather ourselves
│   ├── 02-semantics.md            keyword core, clustering, intents
│   ├── 03-competitors.md          competitor discovery, content gap, monitoring
│   ├── 04-trends-and-plan.md      trends, seasonality, content plan
│   ├── 05-writing-core.md         language-independent writing and structure rules
│   ├── 06-review-lenses.md        four review lenses, checklists, review log
│   ├── 07-linking.md              internal linking, anti-cannibalization
│   ├── 08-measurement.md          Search Console, leading indicators, reports
│   ├── 09-geo.md                  AI answer engine loop, citation measurement
│   ├── 10-safety-gates.md         policies, publishing pace, legal requirements
│   ├── 11-self-learning.md        three learning loops, rule counters, RULE-CHANGE
│   ├── OPEN-QUESTIONS.md          every unresolved question, ranked by cost
│   ├── CHANGELOG.md               including negative results
│   └── lang/
│       ├── _template.md           language pack template
│       ├── en.md                  English content pack
│       └── uk.md                  Ukrainian content pack
│
├── skills/                        Claude Code skills
├── agents/                        subagents
├── hooks/                         enforcing gates
├── scripts/                       LAYER 2, autonomous utilities
├── adapter/
│   ├── SPEC.md                    adapter contract
│   └── examples/                  examples for different stacks
└── state/                         .kiln/ template, project memory
```

---

## Project memory

Kiln keeps state in a `.kiln/` directory inside your repository, in git rather than in a database.
That makes the history of both doctrine changes and content changes shared, versioned and
revertible.

```
.kiln/
├── project.yml          project profile: language, niche, taboos, pace, conversion
├── thresholds.yml       locally calibrated thresholds
├── corpus.json          corpus map: URL, intent, cluster, dates, metrics
├── semantics/           keyword core, clusters, query edge graph
├── competitors/         competitor profiles and snapshots
├── reviews/             human review logs, per lens
├── measurements/        Search Console exports and derived numbers
└── rules-stats.json     per-rule applied and overridden counters
```

---

## Quick start

```bash
# 1. Install as a Claude Code plugin
claude plugin marketplace add Black-coffe/kiln
claude plugin install kiln@kiln --scope project

# 2. Onboard the project: Kiln gathers everything derivable on its own
#    and asks only what cannot be inferred from data
/kiln:onboard

# 3. Check whether the project is viable at all
/kiln:doctor
```

Details in [INTEGRATION.md](INTEGRATION.md).

---

## What Kiln does not do

- Does not evade AI text detectors and does not use "humanizers".
- Does not optimize for third-party content scores.
- Does not publish without human review.
- Does not edit its own rules automatically.
- Does not write to a target word count.

The full list of prohibitions is in [doctrine/00-principles.md](doctrine/00-principles.md).

---

## How to propose changes

Doctrine changes are accepted only through a PR following the `RULE-CHANGE.md` template: the
observation, data with dates and sources, affected projects, the metric that will verify the
change, and the rollback condition. A rule without evidence is an opinion, and the doctrine holds
no opinions.
