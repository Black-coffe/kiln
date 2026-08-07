# Contributing to Kiln

Kiln is a body of rules about content. Its only real asset is that every rule can be traced to
something. A contribution that adds a rule without evidence does not add value, it dilutes the one
property that distinguishes this repository from a vendor blog.

So the bar is unusual, and it is deliberate.

## The bar

Principle **P10** in `doctrine/00-principles.md` governs every change to `doctrine/`. A pull request
that changes a rule, a threshold or a prohibition is accepted only with:

1. **Sufficient evidence**, one of four classes, stated explicitly:

   | Class                 | Minimum bar                                                                          |
   | --------------------- | ------------------------------------------------------------------------------------ |
   | Controlled comparison | one measurement with a control group, reported in full including the arm that lost   |
   | Repeated observation  | at least 10 recorded instances across at least 2 projects, or 20 within one project  |
   | Primary source        | a dated first-party document: official documentation, policy, patent, filing, ruling |
   | Recorded harm         | a single documented incident where the current rule caused damage, with the trace    |

2. **Data with dates and sources.** A URL and a date, or a reproducible measurement.
3. **The list of affected projects**, including the expected effect on projects other than yours.
4. **The metric** that will show whether the change worked.
5. **The rollback condition.**

Use the template in [`RULE-CHANGE.md`](RULE-CHANGE.md). It has a filled worked example.

**A single project's data may propose a change but never justify one on its own**, except under
"recorded harm". The doctrine is shared, so a change derived from noise on one site moves every
site that uses it.

## What gets rejected

- A rule with no evidence, however sensible it sounds. Sensible-sounding is how this field
  accumulated the folklore the doctrine spends its length dismantling.
- A tactic sourced to a blog post that cites another blog post. Trace it to the primary
  publication or mark it `[unverified]` and put it in the "not established" section, not in a rule.
- A threshold presented as a constant when it is somebody's guess. Mark it
  `[expert judgement, needs calibration]` and it is welcome.
- Anything that gates publication on a third-party AI detector or content score. See **P3**. This
  is not negotiable and the reasoning is in the principles file with the correlation figures.
- Vendor benchmarks for the vendor's own product, unless the finding cuts against their commercial
  interest and the methodology is disclosed.

## Negative results are wanted

**P15**: a hypothesis that failed and a rule that had to be withdrawn are recorded in
`doctrine/CHANGELOG.md` with the date and the data.

This is not politeness. Publishing what did not work is the only thing that stops the same idea
being rediscovered every eighteen months, and it is the main reason to prefer a public repository
over a vendor's marketing. If you tried something from this doctrine and it failed, that report is
more valuable than a new rule.

## Code contributions

Layer-2 scripts live in `scripts/`. The conventions are in `scripts/README.md` and they are
enforced:

- JSON or JSONL in, JSON or JSONL out. Nothing parses prose.
- **Deterministic.** Identical input produces byte-identical output, ordering included. Without
  this it is impossible to tell a change in the SERP from a change in our own code.
- **Unicode-aware text handling.** Use `kiln_common.tokenize_words`. A naive tokenizer splits
  Ukrainian «п'ять» at the apostrophe, and every density metric built on it is then wrong in a way
  that still looks plausible.
- **Non-zero exit on a blocking finding.** A gate that only prints a warning is documentation.
- **`thresholds_used` on every finding**, with provenance. Recalibration otherwise silently
  invalidates stored history.
- No secrets on the command line. No writes under the plugin root.

Before opening a PR:

```bash
cd scripts
python rules_lint.py --project-root ..   # must report 0 errors
python -m pytest -q                      # must pass
```

`rules_lint.py` audits the doctrine itself: unresolvable rule IDs, a document prescribing what
another forbids, thresholds without provenance, language packs whose prescribed and forbidden sets
intersect. If your change makes it fail, the change is incomplete rather than the linter wrong.
If you believe the linter is wrong, say so in the PR and explain why — that is a legitimate
argument, and it has been right before.

## Language packs

Adding a language is one of the most useful contributions available, and the one with the highest
risk of doing harm.

Start from `doctrine/lang/_template.md`. Then read the warnings in `doctrine/lang/uk.md`, because
they are concrete and they generalise:

- **Do not port rules across languages.** Em-dash density is a valid English signal and is
  grammatically wrong for Cyrillic, where the dash is obligatory in the "X is Y" construction.
- Every lexical entry carries a `status`: `hypothesis` until measured on a real corpus.
- Words models overuse are judged by **frequency**, never by presence. Banning an ordinary word by
  presence bans ordinary writing in that language.
- Pack metrics are capped at `WARN`. Only `deterministic` entries — orthographic facts, not
  statistical claims — may block.
- State honestly what research exists for your language. For most languages the answer is none, and
  saying so is more useful than implying otherwise.

## Scope

Kiln is deliberately not a generator. Pull requests that add generation features while leaving the
gates untouched are the opposite of the project's thesis: generation is cheap, and what kills sites
is the absence of a brake.

## License

MIT. By contributing you agree your contribution is licensed under it.
