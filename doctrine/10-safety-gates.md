# 10. Safety Gates: policy, pace and legal exposure

**Version:** 0.1.0 · **Date:** 2026-08-07 · **Review:** mandatory every 90 days
**Subordinate to:** [`00-principles.md`](00-principles.md). Where a rule here conflicts with a principle, the principle wins.
**Rests on:** P0 (rejection is the primary metric), P2 (pace equals verification capacity), P11 (human mandatory at three points), P13 (unique value must be named), P14 (programmatic only on real data).
**Adjacent sections:** [`08-measurement.md`](08-measurement.md) (the cohort monitor that detects silent penalties), [`06-review-lenses.md`](06-review-lenses.md) (the review log that carries the legal exemption), [`07-linking.md`](07-linking.md) (cluster similarity, the mechanism behind the anti-doorway gate), [`05-writing-core.md`](05-writing-core.md) (claim provenance), [`01-onboarding-grill.md`](01-onboarding-grill.md) (eligibility gates at intake).

---

## 0. Position of this section

Every other section of the doctrine describes how to produce something. This one describes what must never leave the building, and under what conditions the building closes.

It exists because the failure mode Kiln is designed against is not "the article was mediocre". It is "the domain lost 99.95% of its traffic in one enforcement action and had recovered a tenth of it fourteen months later". That outcome is documented, it happened to organisations with budgets and lawyers, and nothing about it was announced in Search Console.

|              |                                                                                                                                                                                                                                                                                                                    |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Purpose**  | Enforce the constraints that keep Kiln from destroying the site it is installed on, and define the conditions under which Kiln stops publishing entirely.                                                                                                                                                          |
| **Inputs**   | Draft plus its metadata (`unique_value_source`, `ai_involvement`, `public_interest`, byline, YMYL flag); the existing corpus and cluster map; `.kiln/project.yml` (ownership model, domain history, target surfaces, verification capacity); cohort findings from `08-measurement.md`; the Google update calendar. |
| **Outputs**  | A publish/hold decision with a named reason; the `safety` block appended to every publication record; kill-switch state in `.kiln/safety-state.yml`; the honest pace log.                                                                                                                                          |
| **Executor** | Code for everything countable and every schema requirement. An agent for topical judgement and for classifying public-interest status as a _proposal_. A human for every release of a hold, for the YMYL editorial contour, and for legal classification.                                                          |

One framing note before the rules. This section quotes policy verbatim and refuses to paraphrase. Paraphrase is how the SEO folklore that fills this topic gets manufactured: a policy says three conditions must coincide, a blog reports one of them, and eighteen months later an entire industry is optimising against a rule that was never written. Every quotation below carries its URL and the date the page was last updated.

---

## 1. Procedure

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │ ONBOARDING (once)                                                    │
  │  project-level gates: SAF-07 expired domain, SAF-08 reputation host, │
  │  ownership model, target surfaces, verification capacity             │
  │  → fail = project not eligible, see 01-onboarding-grill.md           │
  └────────────────────────────────┬─────────────────────────────────────┘
                                   │
  ┌────────────────────────────────▼─────────────────────────────────────┐
  │ PLANNING (per item)                                                  │
  │  SAF-09 topic focus · SAF-11 pace ceiling · public_interest proposal │
  └────────────────────────────────┬─────────────────────────────────────┘
                                   │
  ┌────────────────────────────────▼─────────────────────────────────────┐
  │ PRE-PUBLICATION (per draft, §12 checklist, single gate)              │
  │  SAF-02 unique value · SAF-03 anti-doorway · SAF-04 programmatic     │
  │  SAF-05 affiliate bar · SAF-06 no generative manipulation            │
  │  SAF-10 byline · SAF-13 flags · SAF-14 disclosure · SAF-15 YMYL      │
  │  SAF-16 news surfaces                                                │
  │  → any BLOCK = hold, with a named rule and a named remedy            │
  └────────────────────────────────┬─────────────────────────────────────┘
                                   │
  ┌────────────────────────────────▼─────────────────────────────────────┐
  │ POST-PUBLICATION (continuous)                                        │
  │  SAF-12 pace logged · SAF-17 update-window freeze                    │
  │  cohort_watch.py (08-measurement §8) → SAF-18 kill switch            │
  │  → release only by SAF-19                                            │
  └──────────────────────────────────────────────────────────────────────┘
```

The shape matters. Project-level gates run once and are cheap to satisfy or impossible to satisfy; there is no middle ground and no point re-running them per article. Content gates run per draft. The kill switch runs on a cohort clock, because that is the only clock on which silent algorithmic enforcement is visible at all.

---

## 2. The policies, quoted

All quotations in this section come from [Spam policies for Google web search](https://developers.google.com/search/docs/essentials/spam-policies), last updated **2026-05-15 UTC**, unless stated otherwise.

### 2.1 The introductory paragraph, as amended in July 2026

> "...such as attempting to manipulate Search systems into ranking content highly or attempting to manipulate **generative AI responses in Google Search**."

> "Sites that violate our policies may rank lower in results or not appear in results at all."

Enforcement is described as operating "through automated systems and, as needed, human review that can result in a manual action".

The clause about generative responses was added on **2026-07-24** ([Search documentation updates](https://developers.google.com/search/updates)). It is the single most consequential change of the year for this framework, because it collapses two supposedly separate disciplines into one enforcement regime. There is no "GEO layer" that operates under gentler rules. A tactic aimed at influencing an AI Overview is a spam tactic on exactly the same terms as a tactic aimed at influencing a blue link.

### 2.2 Scaled content abuse

> "Scaled content abuse is when many pages are generated for the primary purpose of manipulating search rankings and not helping users."

Violating examples, verbatim:

- "Using generative AI tools or other similar tools to generate many pages without adding value"
- "Scraping feeds, search results, or other content to generate many pages ... where little value is provided"
- "Stitching or combining content from different web pages without adding value"
- "Creating multiple sites with the intent of hiding the scaled nature of the content"
- "Creating many pages where the content makes little or no sense to a reader but contains search keywords"

Introduced March 2024, alongside the March 2024 core update (2024-03-05), replacing the earlier "automatically generated content" formulation.

**Read the definition as a legal test.** Three conditions must hold simultaneously: (a) many pages, (b) primary purpose is manipulating rankings, (c) not helping users. A pipeline that produces verifiable unique value on every page breaks condition (c) and, in doing so, undermines any claim about (b). This is precisely where the gates apply pressure, and it is why `unique_value_source` (SAF-02) is the load-bearing gate of the entire framework rather than a documentation nicety.

Note what the definition does _not_ say. It does not mention AI authorship as a violation. The method of production is not the offence; the absence of value at scale is. Every rule in this section is built on that distinction.

### 2.3 Site reputation abuse

> "Site reputation abuse is a tactic where third-party content is published on a host site mainly because of that host's already-established ranking signals."

Violating examples, verbatim: "An educational site hosting a page about sponsored reviews of payday loans written by a third-party"; "A medical site hosting a third-party advertising page about 'best casinos'"; "A news site hosting coupons ... to capitalize on the news site's reputation".

Explicitly not violating: wire services, press releases, user-generated-content sites, editorial content, correctly attributed affiliate links.

Timeline: announced 2024-03-05, enforcement began 2024-05-05, policy expanded 2024-11-19.

The expansion is the part that matters to anyone designing a system. Google considered "various business arrangements, including white-label services, licensing agreements, and partial ownership structures" and concluded that **no degree of first-party involvement excuses the abuse** ([Search Engine Journal, 2024-12-05](https://www.searchenginejournal.com/google-strengthens-policy-against-site-reputation-abuse/533018/)). Editorial oversight stopped being a safe harbour on that date. A contract is not a defence, an ownership stake is not a defence, and "we reviewed it" is not a defence when the content exists on that host because of that host's ranking signals.

### 2.4 Expired domain abuse

> "Expired domain abuse is where an expired domain name is purchased and repurposed primarily to manipulate search rankings by hosting content that provides little to no value."

Examples given: affiliate content on a former government agency site; commercial medical products on a former medical charity site; a casino on a former primary school site.

### 2.5 Doorway abuse

> "Creating substantially similar pages that are closer to search results than a clearly defined, browseable hierarchy"

Doorways are defined as "sites or pages ... created to rank for specific, similar search queries".

This one is aimed straight at naive semantic clustering, and it is the reason SAF-03 exists. A framework that takes a keyword cluster and emits N nearly identical pages, one per query variant, has built a doorway system. It will feel like thorough topic coverage from the inside. From the outside it is the textbook example in the policy.

### 2.6 Thin affiliation

> "publishing content with product affiliate links where the product descriptions and reviews are copied directly from the original merchant without any original content or added value"

The policy also states what a compliant affiliate page adds: "additional information about price, original product reviews, rigorous testing and ratings, navigation of products or categories, and product comparisons". That sentence is a specification, and SAF-05 implements it as one.

### 2.7 What Google says about AI directly

From [Creating helpful, reliable, people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content), last updated **2025-12-10 UTC**:

> "Is it self-evident to your visitors who authored your content?"

> "Sharing details about the processes involved can help readers and visitors better understand any unique and useful role automation may have served."

On disclosure: "Consider adding these when it would be reasonably expected." That is a recommendation, not a requirement. Google does not mandate an "AI-written" label. It mandates transparent authorship, which is a different obligation and is satisfied by a real byline and a stated methodology rather than by a disclaimer.

From [AI features and your website](https://developers.google.com/search/docs/appearance/ai-features), last updated **2025-12-10 UTC**:

> "There are no additional requirements to appear in AI Overviews or AI Mode, nor other special optimizations necessary."

> "You don't need to create new machine readable files, AI text files, or markup to appear in these features."

---

## 3. Why Search Console cannot be the detector

The official [Manual Actions report](https://support.google.com/webmasters/answer/9044175) lists the following actions: Back button hijacking; Site abused with third-party spam; User-generated spam; Spammy free host; Structured data issue; Unnatural links to your site; Unnatural links from your site; Thin content with little or no added value; Cloaking and/or sneaky redirects; Major spam problems; Cloaked images; Hidden text and/or keyword stuffing; AMP content mismatch; Sneaky mobile redirects; News and Discover policy violations; Site reputation abuse.

**"Scaled content abuse" is not on that list. Neither is "expired domain abuse."**

This is not a documentation oversight, and it is not a minor detail. It determines the entire monitoring architecture. Mass low-value publication is punished algorithmically, through core and spam updates. Traffic falls; Search Console stays clean. If a manual action does arrive at all it arrives under a different label, most plausibly "Thin content with little or no added value" or "Major spam problems", which tells you nothing about which of your decisions caused it.

A great many practitioner blogs assert the opposite and describe a "scaled content abuse manual action" as though it were a thing one receives. It is not. Anyone who builds their monitoring on that assumption has built a smoke detector that only rings after the fire is out.

Site reputation abuse is the inverse case: it does appear in the manual actions list, and Google has stated that algorithmic detection is also planned. It is the one policy in this section where Search Console is a real signal.

### SAF-01 · Penalty detection must not depend on the Manual Actions API · **BLOCK**

Kiln's risk monitor is the cohort dynamics detector specified in [`08-measurement.md` §8](08-measurement.md) (`cohort_watch.py`, rules MSR-17 and MSR-18), which compares the impression and click trajectory of Kiln-published cohorts against the `pre-kiln` cohort over a rolling window, aligned to the update calendar. The Manual Actions API is polled as a supplementary signal and never as the primary one.

An implementation that treats an empty Manual Actions response as evidence of health fails this rule.

**Rationale.** The absence of a manual action is not the absence of a penalty, because the relevant policy has no corresponding manual action.

---

## 4. The structural evidence: who fell and who did not

Traffic figures below are third-party estimates (Semrush-class), not analytics data, reported in a Level B secondary source ([Growtika](https://growtika.com/blog/publisher-affiliate-collapse)). They are directionally reliable and precise to roughly an order of magnitude, which is more than enough for the point being made.

| Property                                | Before           | After                      | Change  | Date                                           |
| --------------------------------------- | ---------------- | -------------------------- | ------- | ---------------------------------------------- |
| Forbes Advisor (`/advisor/`)            | 23.6M/mo at peak | 11K                        | −99.95% | penalty 2024-09, deindexed 2024-11             |
| CNN Underscored                         | 3.2M/mo          | 945 (10 URLs left indexed) | −99.97% | manual action 2024-11-20                       |
| Time Stamped (Taboola Turnkey Commerce) | 3M/mo            | 0                          | −100%   | shut down 2025                                 |
| AP Buyline (Taboola Turnkey Commerce)   | launched 2024-03 | 0                          | −100%   | shut down; team left for a new venture 2025-06 |

Also affected: USA Today Reviewed, US News 360 Reviews, The Sun Shopping, WSJ Buy Side. The enforcement landed days before Black Friday 2024, at the point of maximum commercial damage.

Now the half of the evidence that actually tells you what to build:

| Property          | Peak            | February 2026 | Status                                                |
| ----------------- | --------------- | ------------- | ----------------------------------------------------- |
| NYT Wirecutter    | 15.9M (2025-04) | 8M            | no penalty                                            |
| NY Mag Strategist | 3.82M (2024-12) | 662K          | no penalty; the decline is attributed to AI Overviews |

Wirecutter and Strategist publish commercial review content in the same categories, at comparable scale, competing for the same queries as the properties that were destroyed. They were not touched.

**The difference is structural, not stylistic.** An in-house editorial operation versus an outsourced revenue-share partner. Not "better prose". Not a higher content score. Not a lower AI-detection reading. The ownership model of the content production itself.

This is the single most important fact in this document, and it is why P2 sets pace from verification capacity rather than from a number someone published in a blog post. You cannot review your way out of an outsourced content farm by reviewing faster. You avoid the outcome by having a real editorial operation, and a real editorial operation has a throughput, and that throughput is your publishing ceiling.

---

## 5. Recovery reality

- **Forbes Advisor:** 2.28M/mo by 2026-02, roughly 10% of peak, following restructuring. The shortfall was covered with paid traffic (3.2M by 2025-12), which is to say it was not recovered so much as repurchased.
- **CNN Underscored:** 1.26M/mo by 2026-02, roughly 39% of peak.

**Fourteen months and more to partial recovery. No documented case of full recovery.**

The official expectation for a reconsideration request is that "Most reconsideration reviews can take several days or weeks, although in some cases, such as link-related reconsideration requests, it may take longer than usual to review your request." That timeline describes the review of the request, not the restoration of traffic, and the gap between the two is where the fourteen months live.

This is the arithmetic that justifies every blocking gate below. A gate that holds a good article for two days costs two days. A gate that was not there costs somewhere between a year and the business.

---

## 6. Content gates

### SAF-02 · `unique_value_source` must be non-empty, typed, and backed by an artefact · **BLOCK**

No page publishes unless `unique_value_source` is populated with a typed value drawn from a closed set, accompanied by a reference to the artefact that substantiates it:

| Type                      | Required artefact                                                         |
| ------------------------- | ------------------------------------------------------------------------- |
| `own_data`                | the dataset or export, hashed into the effort manifest                    |
| `own_measurement`         | the measurement log or test record                                        |
| `primary_experience`      | a first-person account with verifiable specifics (dates, versions, costs) |
| `expert_interview`        | a transcript or approved quotation with an attributable person            |
| `original_calculation`    | the method, stated by name, and the inputs                                |
| `primary_source_analysis` | the primary document, fetched by us, with URL and date                    |
| `dataset_record`          | the non-LLM record instantiating the page, plus its source                |

Free-text values are rejected. "More detailed", "better structured" and "more up to date" are not types and never become types.

The artefact mechanics, including the manifest format and the `created_by` requirement, are specified in [`05-writing-core.md`](05-writing-core.md) and are not duplicated here.

**Rationale.** Verbatim policy: "Using generative AI tools or other similar tools to generate many pages **without adding value**". Value that cannot be named cannot be demonstrated, and a gate triggered by a filled field rewards silence unless the field is typed and backed. Also P13.

**Threshold:** none. This is binary. `[source: spam policies, 2026-05-15]`

---

### SAF-03 · Cluster-wide anti-doorway check before publication · **BLOCK**

Before a draft is published, it is compared against every existing page in its cluster and against every other draft queued from the same cluster. If pairwise similarity exceeds the project threshold, the draft does not publish; it is merged, differentiated on substance, or dropped.

The similarity mechanism, the anchor invariant it depends on, and the merge-versus-differentiate decision tree are specified in [`07-linking.md`](07-linking.md). This rule adds only the enforcement point: the check runs _before_ publication, on the queue as well as on the corpus, not as a periodic audit afterwards.

Checking only against the published corpus is the failure mode worth naming. Six drafts generated from one cluster in one planning run will each pass a corpus check individually and constitute a doorway set collectively.

**Rationale.** Verbatim policy: "Creating substantially similar pages that are closer to search results than a clearly defined, browseable hierarchy". Also P6.

**Threshold:** inherited from `07-linking.md`. `[expert judgement, needs calibration]` in both places, and it must be calibrated once, in one file, not twice.

---

### SAF-04 · Programmatic pages must carry a real database record · **BLOCK**

A page produced by a template publishes only if both tests pass:

1. **Strip test.** Remove every element common to the template across the set. What remains must be substantive text, not a name and a number.
2. **Non-LLM source test.** The page has a data source that is not a language model: a live database record, a feed, a measurement, a public register.

The page exists because the object exists. It does not exist because the query exists.

**Rationale.** The survivors in this genre (Zapier, Wise, Airbnb, Canva, TripAdvisor) carry genuine records on every page: prices, rates, reviews, integration parameters. The casualties substituted a variable into prose. Also P14.

**Thresholds:** a practitioner threshold of ≥500 unique words per page and ≤40% template share circulates and is operationally usable, but it comes from a Level C source with no primary evidence. `[expert judgement, needs calibration]` Kiln records the actual template share per programmatic set and treats the number as a parameter, not a law.

---

### SAF-05 · Affiliate pages carry a raised bar · **BLOCK**

A page carrying affiliate links publishes only if it contains at least one of: original price data gathered by us, original testing or measurement, a structured comparison built from our own collection, or category navigation that constitutes a genuine service to the reader.

Merchant descriptions reproduced with links attached do not publish, regardless of how much surrounding prose exists.

**Rationale.** Verbatim policy, thin affiliation: content where "the product descriptions and reviews are copied directly from the original merchant without any original content or added value". The policy names the remedy in the same breath: "additional information about price, original product reviews, rigorous testing and ratings, navigation of products or categories, and product comparisons". This rule is that sentence, enforced.

Note the compounding exposure: affiliate content was the content type in every one of the destroyed properties in §4.

---

### SAF-06 · No manipulation of generative responses · **BLOCK**

Forbidden without exception, and detected by static inspection of the rendered page before publication:

- Instructions addressed to a language model embedded anywhere in the page, in visible text, in comments, in attributes, in structured data, or in hidden elements.
- Prompt injection of any form, including text intended to alter how an assistant summarises or characterises the page.
- Serving different content to AI crawlers than to Googlebot or to human visitors.
- Facts placed in structured data that do not appear in the visible text.

The last item deserves its own note, because it is the one that gets rationalised. It has been demonstrated that language models extract information from JSON-LD even when the markup is syntactically invalid and semantically meaningless, because the model tokenises the script block as ordinary text. That this works is not a reason to do it. Markup that asserts what the page does not say is a cloaking risk under Google's own structured data policy, and the risk/benefit ratio is negative. The correct inference runs the other way: **if a fact matters, put it in the visible text**, because visible text is what gets tokenised reliably. Markup is a duplicate, not a channel.

**Rationale.** Since 2026-07-24 the spam policies cover "attempting to manipulate generative AI responses in Google Search" verbatim. Google states separately that no special optimisation is necessary at all. Also P12.

---

## 7. Project and site gates

### SAF-07 · Kiln does not deploy on a repurposed expired domain · **BLOCK**

At onboarding, the domain's WHOIS creation date and its historical topic (via archive snapshots) are checked. If the domain was acquired after expiry and the intended topic differs materially from its historical topic, the project is not eligible. There is no override at the article level; this is a project-level determination made once.

**Rationale.** Verbatim policy: an expired domain "purchased and repurposed primarily to manipulate search rankings by hosting content that provides little to no value".

---

### SAF-08 · No third-party content on a host we do not own · **BLOCK**

Kiln does not publish to a domain where the operator is not the first party, and does not publish content whose topic sits outside the host's own subject matter, irrespective of the commercial arrangement.

White-label agreements, licensing, revenue share and partial ownership are explicitly not exemptions. This is stated in the policy expansion, not inferred.

**Rationale.** Site reputation abuse is the one policy in this section with a fully documented enforcement outcome, and that outcome was total: −99.95% and −99.97%, with partial recovery taking over a year. On 2024-11-19 Google considered the exact business structures a defender would reach for and rejected all of them.

---

### SAF-09 · Topic focus discipline · **WARN**

A planned item whose topical distance exceeds the radius **of the site section it belongs to** requires explicit owner sign-off before it enters the plan. The sign-off is recorded with a reason.

The distance metric is the topical radius defined in [`07-linking.md`](07-linking.md).

**The radius is per section, not per site.** The section map comes from the project profile
(`01-onboarding-grill.md`, `project.yml`), and each section carries its own calibrated radius. An
item is measured against the centroid of its own section, not against the centroid of the whole
corpus.

**Why this is not a loosening.** A site-wide radius on a legitimately multi-vertical property fires
on nearly everything. The pilot is a financial marketplace covering banks, microfinance, insurance,
reviews and a wiki: those verticals are far apart in embedding space by their nature, so a single
site centroid sits in empty space between them and every draft looks like dispersion. A gate that
fires constantly is worse than no gate, because it trains the team to dismiss the warning, and it
will be dismissed on the one occasion it was right. Per-section radii keep the gate sensitive to
what it is actually for: an insurance article appearing in the microfinance section, or a section
quietly drifting away from its own subject over time.

Section drift is itself measured. A section centroid moving materially between calibrations is
reported, because that is genuine topical dispersion arriving slowly rather than in one visible jump.

**Threshold:** per-section topical radius, `[expert judgement, needs calibration]`. Sections must be
calibrated on the existing corpus **before the first wave**; until a section has a calibrated radius,
SAF-09 records `INFO` for that section rather than `WARN`, because an uncalibrated threshold produces
noise, not signal.

**Rationale.** The February 2026 Discover core update (2026-02-05 to 2026-02-27) introduced, among three changes, the identification of "topic-specific expertise within publications covering multiple subjects". Topical dispersion is now penalised at the algorithmic level, not merely disfavoured in theory. This is a direct argument against the strategy of writing about whatever has traffic — and note that the update's own wording is about expertise _within_ subject areas, which is what a per-section radius measures and a site-wide one does not.

**Why WARN and not BLOCK.** Legitimate expansion into an adjacent topic is a normal business event. The gate exists to make it a decision rather than a drift.

---

### SAF-10 · Human byline, real date, no AI author · **BLOCK**

Every publication carries a byline naming an identifiable human, a publication date, and a route from the byline to an author page. A byline naming a model, a brand, or a generic editorial persona with no corresponding page does not publish.

**Rationale.** Google's own framing question: "Is it self-evident to your visitors who authored your content?" Google News requires "Clear dates and bylines" and "Information about the authors, publication, and publisher". Google has separately indicated that giving an AI system an author byline is not a good approach; the correct pattern names the real people who wrote, edited or reviewed. In the Quality Rater Guidelines, absence of information about the responsible person or organisation is independent grounds for the lowest rating.

---

## 8. Publishing pace: the honest answer

### What is in circulation

Every one of the following is a Level C claim, meaning an SEO agency reporting on itself:

- "100+ posts per quarter is now the norm", with velocity tiers of 30–60 / 60–150 / 150–250 / 250+ per quarter.
- "16+ posts per month produces 3.5× traffic."
- "71% of AI-generated pages indexed within 36 days across a 16-month experiment."
- A flagship case study describing a move from 12 to 104 posts per month, with a 96% fact-check pass rate and 91% schema compliance.

On checking the primary sources: there are none. The flagship 104-posts-per-month case is **explicitly labelled by its own author as an "anonymised composite"**, which is to say a fabricated aggregate rather than a client. The velocity statistics are attributed to unspecified "client audits" with no external verification, and the author describes the benchmarks as "directional".

### What is actually true

Google has never published a pace threshold. No controlled public experiment on publishing velocity exists. The proposition that a publishing burst is itself a spam signal is plausible and undemonstrated.

Hard-coding any of those numbers as a safety limit would be cargo cult: adopting the form of a rule with none of the evidence, and then defending it because it is in the doctrine.

### SAF-11 · Publishing pace is bounded by verification capacity · **BLOCK**

The publishing ceiling is computed from the review capacity formula in [`06-review-lenses.md`](06-review-lenses.md), which derives throughput from the narrowest review lens and from measured per-item time, not from an assumed number. Items publish only from the queue of drafts that have cleared review. There is no separate posts-per-day constant anywhere in Kiln, and adding one is a doctrine violation, not a configuration choice.

**Rationale.** The bottleneck that determines survival is verification, per §4. Constraining the actual bottleneck is a real control; constraining an invented proxy is theatre. Also P2.

---

### SAF-12 · Actual pace is logged per publication and never back-filled · **BLOCK**

Every publication records its true timestamp, its cohort, and the review capacity in force at the time. Bursts are flagged. Records are never rewritten retroactively, and a publication whose timestamp is edited after the fact is excluded from all learning.

**Rationale.** Two reasons, and the second is the interesting one. First, the pace log is the input to the cohort monitor, and a falsified log disables the kill switch. Second, nobody in the industry has honest pace data, because everyone reporting it is selling something. A framework that logs its own pace truthfully across multiple projects, and joins it to subsequent cohort outcomes, becomes the first real source of this data. That is a genuine contribution, and it costs one timestamp.

---

## 9. The legal layer: EU AI Act Article 50

Regulation (EU) 2024/1689. Transparency obligations have applied since **2026-08-02**, which is five days before this document was written.

### The obligation

> "Deployers of generative AI systems must clearly label AI-generated or manipulated text **published with the purpose of informing the public on matters of public interest**."

Three criteria must coincide: the text is published, it informs the public, and the subject is a matter of public interest. The Commission enumerates the public-interest domains: politics and democratic processes, public administration and services, justice and law enforcement, fundamental rights, public safety, health, environmental protection, consumer safety.

### The exemption, which is the part that matters

> "Published text that has undergone **human review or editorial control** does not need to be labelled."

Human review is defined as "deliberate examination of the substance of the content by one or more natural persons possessing relevant knowledge and professional judgement". Editorial control requires "a responsible editorial entity" with "authority to approve, alter or reject the substance".

A spell check does not qualify. An approval click does not qualify. What qualifies is a qualified person examining the substance, and the only evidence that this happened is a record of what they changed.

### Form and penalties

Information must be "clear, distinguishable" and provided no later than the first interaction. Per the Commission's Guidelines of **2026-07-20** (non-binding but clarifying), general disclaimers in terms and conditions, in a site footer, or as a vague label are **not sufficient**.

Penalties reach **EUR 15,000,000 or 3% of worldwide annual turnover, whichever is higher**, enforced by national market surveillance authorities. `[source: EU AI Act, via EVIDENCE.md#e10-eeat-entities-schema]`

Content created before 2026-08-02 does not require retroactive labelling. The machine-readable marking obligation under Art. 50(2) primarily concerns synthetic audio, image and video; no specific marking standard for text is set in the guidance, and a grace period runs to 2026-12-02 for systems placed on the market before 2026-08-02.

### SAF-13 · `ai_involvement` and `public_interest` exist from the first record · **BLOCK**

Every content record carries, from creation:

- `ai_involvement`: `none` | `assisted` | `generated`
- `public_interest`: boolean, with `public_interest_basis` naming the domain when true

Both are mandatory at insert. Neither can be null. Neither is derived later.

**Rationale, and this is an architectural point rather than a compliance footnote.** These fields cannot be reconstructed retroactively. Six months from now, facing a question about a thousand published pages, there is no procedure that recovers whether a given article was model-generated or human-written, and no amount of engineering effort substitutes for a field that was never populated. The cost of adding them on day one is two columns. The cost of adding them on day four hundred is that the entire back catalogue is permanently unclassifiable.

---

### SAF-14 · Visible disclosure when all three conditions coincide · **BLOCK**

Where `public_interest = true` **and** `ai_involvement != none` **and** `published_at >= 2026-08-02` **and** no qualifying human review is logged, the page does not publish without a visible, distinguishable disclosure placed where the reader encounters it before the content.

A footer notice does not satisfy this rule. A line in the terms of service does not satisfy this rule. The Guidelines exclude both by name.

The preferred path is the exemption: log a qualifying substantive human review under [`06-review-lenses.md`](06-review-lenses.md) and the labelling obligation does not arise. The disclosure is the fallback, not the default.

**Note on classification.** An agent may propose the value of `public_interest`; it does not decide it. The determination is legal in character and belongs to the project owner, recorded once per topic area at onboarding and revisited when the topic set changes.

---

### SAF-15 · YMYL triggers the mandatory editorial contour · **BLOCK**

When the topic classifier flags an item as YMYL, the following become mandatory and blocking: a substantive human review logged per lens with a non-empty record of what changed; a reviewer whose subject-matter qualification is recorded; a named human author resolving to an author page; published editorial policy on the site.

**Rationale.** The two category systems overlap heavily. Google's YMYL expanded in the 2025-09-11 Quality Rater Guidelines to "Government, Civics & Society", explicitly covering elections, public institutions and trust in civic processes. The AI Act's "matters of public interest" covers politics, public administration, justice, health, safety and consumer protection. A single rule discharges both obligations, and it also raises the machine estimate of effort invested, since `contentEffort` in the Content Warehouse leak is described as an "LLM-based effort estimation". One subsystem, three purposes. Also P11.

**The reference pilot is inside this rule.** It is a financial marketplace: YMYL by Google's classification, consumer-finance by the AI Act's. The strictest configuration in the doctrine is the default configuration for the first project, which is the correct order to discover problems in.

---

### Open legal question, stated plainly

**Extraterritorial application of Art. 50 to a Ukrainian project was not resolved by any source consulted.** The obligation attaches to deployers placing output on the EU market or addressing an EU audience, and no source examined established how that applies to a Ukrainian-language site serving a Ukrainian audience with incidental EU readership. The intel report flags this as out of scope, and it remains out of scope here.

Kiln's position: the flags in SAF-13 are cheap and are collected regardless of jurisdiction, so the framework stays capable of complying whatever the answer turns out to be. But the answer is required before this framework is used on a project with genuine EU exposure, and it requires a lawyer rather than another research agent. Recorded as an open item, not as a resolved one.

---

## 10. Platforms beyond Google Search

### SAF-16 · News and Discover surfaces impose their own gate · **BLOCK when targeted**

If `.kiln/project.yml` declares Google News or Discover as target surfaces, the following are blocking:

- Clear publication dates and bylines on every item.
- Published information about the authors, the publication, and the publisher.
- Explicit disclosure of sponsored content.
- No misleading preview content. The policy prohibits "preview content that misleads users to engage with it by promising details which aren't reflected in the underlying content", which in practice forbids the headline-versus-body gap that clickbait depends on.

**Rationale and severity.** Violations lead to removal from news surfaces, and "repeated or egregious violations" lead to **permanent ineligibility**. Permanent is the operative word: this is the only sanction in this document with no documented path back at all, which is why it blocks rather than warns.

There is no separate AI policy for Google News in the published documentation. The byline requirement makes anonymous machine publication incompatible with the surface as a practical matter, without any AI-specific rule being needed.

**Discover, additionally.** The February 2026 Discover core update prioritises locally relevant content from sites in the user's own country, demotes sensationalism, and rewards topic-specific expertise. It has rolled out for English-language US users with expansion stated as forthcoming. Practitioner observations of 30–60% losses on sensational thin-content sites are Level C and are recorded as context, not as a threshold. `[expert judgement, needs calibration]`

### Surfaces not covered by this doctrine

- **Bing.** The official guidelines page could not be retrieved during research. Bing is historically more permissive toward AI content, but that is practitioner consensus and has not been raised to a primary source. **Gap.**
- **Yandex.** Not researched. Relevant only for projects targeting the ru segment. **Gap.**
- **AI answer engines.** No documented mechanism exists analogous to a Google domain penalty. The real lever runs the other way: crawler access. The risk is exclusion through a robots.txt or CDN misconfiguration, not demotion for quality. Covered in [`09-geo.md`](09-geo.md) and at onboarding.

Both gaps must be closed before Kiln is used on a project whose primary market is served by those engines. They are recorded here rather than quietly omitted.

---

## 11. The update calendar as context

Google ships core updates and spam updates two to three times a year each. Core updates roll out over 12 to 45 days; spam updates over hours to days.

| Update                                          | Start      | End        | Duration  |
| ----------------------------------------------- | ---------- | ---------- | --------- |
| March 2024 core                                 | 2024-03-05 | 2024-04-19 | 45 d      |
| March 2024 spam (three new policies introduced) | 2024-03-05 | 2024-03-20 | 14 d 21 h |
| June 2024 spam                                  | 2024-06-20 | 2024-06-27 | 7 d       |
| August 2024 core                                | 2024-08-15 | 2024-09-03 | 19 d      |
| November 2024 core                              | 2024-11-11 | 2024-12-04 | 23 d      |
| December 2024 core                              | 2024-12-12 | 2024-12-18 | 6 d       |
| December 2024 spam                              | 2024-12-19 | 2024-12-26 | 7 d       |
| March 2025 core                                 | 2025-03-13 | 2025-03-27 | 13 d      |
| June 2025 core                                  | 2025-06-30 | 2025-07-17 | 16 d      |
| August 2025 spam                                | 2025-08-26 | 2025-09-22 | 26 d 15 h |
| December 2025 core                              | 2025-12-11 | 2025-12-29 | 18 d      |
| February 2026 Discover update                   | 2026-02-05 | 2026-02-27 | 21 d      |
| March 2026 spam                                 | 2026-03-24 | 2026-03-24 | 19 h 30 m |
| March 2026 core                                 | 2026-03-27 | 2026-04-08 | 12 d      |
| May 2026 core                                   | 2026-05-21 | 2026-06-02 | 11 d      |
| June 2026 spam                                  | 2026-06-24 | 2026-06-26 | 2 d       |

Source: [Google Search Status Dashboard, ranking updates history](https://status.search.google.com/products/rGHU1u87FJnkP6W2GwMi/history).

Of the June 2026 spam update Google confirmed to Search Engine Roundtable that it targeted neither link spam nor site reputation abuse. By elimination it targeted content tactics: scaled content abuse, cloaking, sneaky redirects, keyword stuffing.

### SAF-17 · Rollout windows freeze learning · **WARN**

While a core or spam update is rolling out, and for 14 days after it completes `[expert judgement, needs calibration]`, measurements taken in that window are marked unstable. They do not feed threshold recalibration, they do not feed the rule counters of P8, and they do not trigger doctrine amendment proposals under P10.

Cohort alerts continue to fire during the window. Learning pauses; the kill switch does not.

**Rationale.** Over a 45-day core rollout, page-level metrics do not describe page quality. A framework that learns during that window learns the update, permanently mistakes it for a quality signal, and propagates that mistake to every project sharing the doctrine.

---

## 12. The kill switch

A gate nobody can trip is not a gate. This one can, and the conditions are written down in advance so that the decision is not made under pressure by someone with an incentive to keep publishing.

### SAF-18 · Kill switch triggers · **BLOCK**

Publication stops for the entire project, immediately and automatically, on any of:

| #   | Trigger                                                                                                     | Source                                                 |
| --- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| K1  | Two consecutive cohort windows in alarm                                                                     | [`08-measurement.md`](08-measurement.md) MSR-17/MSR-18 |
| K2  | Any manual action received, of any type                                                                     | Manual Actions API                                     |
| K3  | Share of Kiln-published pages with zero impressions over 28 days exceeding the project threshold            | `08-measurement.md` §8                                 |
| K4  | Removal from a declared target surface (News, Discover)                                                     | Publisher Center notification                          |
| K5  | Discovery that a shipped page violates a BLOCK rule in this section                                         | audit, or a report from any source                     |
| K6  | The verification capacity that authorised the current pace ceases to exist, for instance a reviewer leaving | `06-review-lenses.md`                                  |

State is written to `.kiln/safety-state.yml` with the trigger, the timestamp, and the evidence. While the state is set, the publish path returns a non-zero exit and refuses, including for items already approved by review.

K6 is the trigger that gets forgotten, and it is the one that connects this section to §4. Losing a reviewer does not merely slow production. It converts an in-house editorial operation into something structurally closer to the arrangement that got four properties destroyed. Pace must fall with capacity, immediately, and if capacity falls far enough then publication stops until it is restored.

---

### SAF-19 · Release requires a named human and stated evidence · **BLOCK**

Only the project owner releases a kill-switch hold. The release record must contain:

1. The trigger being released and its evidence.
2. The identified cause, or an explicit statement that the cause is unknown.
3. The remediation performed, with the affected URLs listed.
4. The metric that will confirm the remediation worked, and the date it will be checked.
5. The condition that will re-trigger the hold.

Automatic release is forbidden. Release on the grounds that the metric recovered on its own is forbidden without items 2 and 3.

**Rationale.** The asymmetry is total. A false hold costs weeks of publishing. A missed penalty costs, on the documented evidence, fourteen months and a domain. Any release procedure calibrated against the first cost is calibrated against the wrong number.

The release record is also the raw material for P15, since a hold that turns out to be a false alarm is a negative result and belongs in `doctrine/CHANGELOG.md` with its data.

---

## 13. Pre-publication checklist

One gate, run as one operation, returning one decision. Rules owned by other sections are referenced rather than restated, so that a threshold changes in exactly one place.

| #   | Check                                                                     | Rule   | Owner section                | Severity |
| --- | ------------------------------------------------------------------------- | ------ | ---------------------------- | -------- |
| 1   | Kill switch is not engaged                                                | SAF-18 | this                         | BLOCK    |
| 2   | `unique_value_source` typed, non-empty, artefact attached                 | SAF-02 | this                         | BLOCK    |
| 3   | Every claim about the world has a primary source we fetched               | —      | `05-writing-core.md`         | BLOCK    |
| 4   | Cluster-wide similarity below threshold, corpus and queue                 | SAF-03 | this + `07-linking.md`       | BLOCK    |
| 5   | Programmatic set passes the strip and non-LLM-source tests                | SAF-04 | this                         | BLOCK    |
| 6   | Affiliate bar met, if affiliate links present                             | SAF-05 | this                         | BLOCK    |
| 7   | No generative-response manipulation; markup facts present in visible text | SAF-06 | this                         | BLOCK    |
| 8   | Human byline, real date, author page resolves                             | SAF-10 | this                         | BLOCK    |
| 9   | `ai_involvement` and `public_interest` populated                          | SAF-13 | this                         | BLOCK    |
| 10  | Disclosure present, or a qualifying review logged                         | SAF-14 | this + `06-review-lenses.md` | BLOCK    |
| 11  | YMYL editorial contour complete, if flagged                               | SAF-15 | this                         | BLOCK    |
| 12  | Target-surface requirements met, if surfaces declared                     | SAF-16 | this                         | BLOCK    |
| 13  | Item is within the pace ceiling                                           | SAF-11 | this + `06-review-lenses.md` | BLOCK    |
| 14  | Anchor invariant not violated by the new page                             | —      | `07-linking.md`              | BLOCK    |
| 15  | Indexable: no stray `noindex`, no accidental `nosnippet`                  | —      | `01-onboarding-grill.md`     | BLOCK    |
| 16  | Topic within radius, or sign-off recorded                                 | SAF-09 | this                         | WARN     |
| 17  | Not inside an update freeze window, for learning purposes only            | SAF-17 | this                         | WARN     |

### SAF-20 · The checklist is a gate, not advice · **BLOCK**

The checklist is enforced by a hook on the publish path, and a `WARN` is recorded rather than swallowed. A checklist that produces a report which a human may act on is not a gate, and Kiln does not ship one.

**Rationale.** This is the exact defect diagnosed in the owner's existing system, where the quality gate was advisory, the hook was recorded as "not built yet", and the entire arrangement rested on individual discipline. It held until it did not, and two mutually exclusive rules coexisted in the documentation for months because nothing was counting. Also P8.

---

## 14. Roles: code, agent, human

| Operation                                                | Executor                           | Rule           |
| -------------------------------------------------------- | ---------------------------------- | -------------- |
| Field presence, typing, schema validation                | **code**                           | SAF-02, SAF-13 |
| Similarity computation                                   | **code**                           | SAF-03         |
| Template share and strip test                            | **code**                           | SAF-04         |
| Static inspection for injected instructions and cloaking | **code**                           | SAF-06         |
| WHOIS and archive history lookup                         | **code**                           | SAF-07         |
| Byline and author-page resolution                        | **code**                           | SAF-08, SAF-10 |
| Pace accounting and burst detection                      | **code**                           | SAF-11, SAF-12 |
| Cohort alerting and kill-switch engagement               | **code**                           | SAF-18         |
| Update-calendar polling and freeze windows               | **code**                           | SAF-17         |
| Whether an affiliate page adds genuine value             | **agent proposes, human decides**  | SAF-05         |
| Topical distance interpretation                          | **agent proposes, human decides**  | SAF-09         |
| YMYL classification                                      | **agent proposes, human confirms** | SAF-15         |
| `public_interest` classification                         | **agent proposes, owner decides**  | SAF-13, SAF-14 |
| Whether the review was substantive                       | **human**                          | SAF-14, SAF-15 |
| Project eligibility at onboarding                        | **human**                          | SAF-07, SAF-08 |
| Kill-switch release                                      | **human, owner only**              | SAF-19         |
| Legal determination of AI Act applicability              | **human, and not this framework**  | §9             |

The pattern is consistent with the rest of the doctrine: code computes what is countable, an agent proposes what requires judgement, a human decides anything irreversible or legally consequential. No agent releases a hold and no agent decides a legal question.

---

## 15. Prohibited

| Prohibition                                                        | Rule   | Reason                                                                   |
| ------------------------------------------------------------------ | ------ | ------------------------------------------------------------------------ |
| Treating an empty Manual Actions response as evidence of health    | SAF-01 | there is no manual action for scaled content abuse                       |
| A posts-per-day constant used as a safety limit                    | SAF-11 | no evidence exists for any such number; it displaces the real constraint |
| Back-dating or editing a publication timestamp                     | SAF-12 | disables the cohort monitor and therefore the kill switch                |
| Deriving `ai_involvement` or `public_interest` after the fact      | SAF-13 | retroactive classification is impossible, not merely inconvenient        |
| A footer or terms-of-service notice used as AI Act disclosure      | SAF-14 | excluded by name in the Commission Guidelines of 2026-07-20              |
| An approval click recorded as human review                         | SAF-15 | the exemption requires examination of the substance                      |
| Publishing to a host we do not own on the strength of its rankings | SAF-08 | no ownership structure was accepted as a defence on 2024-11-19           |
| Facts in structured data that are absent from visible text         | SAF-06 | cloaking risk; that LLMs read it is not a justification                  |
| Automatic release of a kill-switch hold                            | SAF-19 | asymmetry: weeks against a domain                                        |
| Learning from metrics gathered during an update rollout            | SAF-17 | the framework learns the update and mistakes it for quality              |
| Checking similarity only against the published corpus              | SAF-03 | a doorway set generated in one run passes every individual check         |
| An advisory checklist in place of an enforced gate                 | SAF-20 | the documented failure mode of the system this doctrine replaces         |
| Budget spent on `llms.txt` as a safety or visibility lever         | P12    | 97% of such files were never requested once                              |

---

## 16. Sources

**Level A, primary**

- [Spam policies for Google web search](https://developers.google.com/search/docs/essentials/spam-policies), last updated 2026-05-15
- [Creating helpful, reliable, people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content), last updated 2025-12-10
- [AI features and your website](https://developers.google.com/search/docs/appearance/ai-features), last updated 2025-12-10
- [Guidance on generative AI content](https://developers.google.com/search/docs/fundamentals/using-gen-ai-content)
- [Search documentation updates](https://developers.google.com/search/updates) (2026-07-24 generative-response amendment; 2026-06-15 llms.txt clarification; 2026-05-15 AI-features guidance)
- [Google Search Status Dashboard, ranking updates history](https://status.search.google.com/products/rGHU1u87FJnkP6W2GwMi/history)
- [Manual Actions report](https://support.google.com/webmasters/answer/9044175)
- [Google News content policies](https://support.google.com/news/publisher-center/answer/6204050)
- [Search Quality Rater Guidelines, 2025-09-11, 182 pp.](https://guidelines.raterhub.com/searchqualityevaluatorguidelines.pdf)
- [EU AI Act, Article 50](https://artificialintelligenceact.eu/article/50/)
- [European Commission, Guidelines on transparency obligations for AI-generated content](https://digital-strategy.ec.europa.eu/en/policies/guidelines-transparency-ai-generated-content), 2026-07-20
- [European Commission, Transparency obligations under Article 50 (FAQ)](https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act)

**Level B, quality secondary**

- [Growtika, publisher affiliate collapse autopsy](https://growtika.com/blog/publisher-affiliate-collapse) (traffic figures for §4 and §5)
- [Search Engine Journal, Google Strengthens Policy Against Site Reputation Abuse](https://www.searchenginejournal.com/google-strengthens-policy-against-site-reputation-abuse/533018/), 2024-12-05
- [Search Engine Land, June 2026 spam update complete](https://searchengineland.com/google-june-2026-spam-update-469000)
- [Search Engine Land, February 2026 Discover core update complete](https://searchengineland.com/google-february-2026-discover-core-update-is-now-complete-469450)
- [Search Engine Land, Google confirms spam policies apply to AI Overviews and AI Mode](https://searchengineland.com/google-updates-search-spam-policies-to-clarify-it-applies-to-generative-ai-responses-477657)
- [Press Gazette, publisher shopping revenue blow](https://pressgazette.co.uk/platforms/google-dealt-blow-to-publisher-shopping-revenue-on-eve-of-black-friday-site-reputation-abuse-update/)
- [Sidley, EU AI Act Transparency Obligations](https://datamatters.sidley.com/2026/06/24/eu-ai-act-transparency-obligations-preparing-for-compliance-by-2-august-2026/), 2026-06-24

**Level C, hypotheses only, never compiled into thresholds**

- Publishing velocity retrospectives and the "100 posts per month" composite case study. Cited in §8 solely to be refuted.
- Programmatic thresholds of ≥500 words and ≤40% template share (SAF-04).
- Discover loss estimates of 30–60% for sensational thin content (§10).

**Internal**

- `EVIDENCE.md#e13-policy-and-risk` (primary basis for this section)
- `EVIDENCE.md#e10-eeat-entities-schema` (legal layer, authorship, YMYL overlap)

---

## 17. Conflicts with the principles

**17.1 SAF-09 against P0, at the margin.** P0 says the rejection rate is the primary measure of Kiln working. SAF-09 is a WARN rather than a BLOCK, which means topical drift is recorded but not stopped. On a site with weak topical focus to begin with, and `example.com` spans banks, microfinance, reviews and a wiki, the WARN will fire constantly and be dismissed constantly, which trains the team to dismiss warnings. Either the topical radius is calibrated per section rather than per site, or this rule becomes noise within a month. **Resolved 2026-08-07:** SAF-09 now measures against the radius of an item's own section, with the section map declared in `project.yml`. **The calibration itself remains outstanding** — until a section has a calibrated radius, SAF-09 records `INFO` for that section, and sections must be calibrated on the existing corpus before the first wave.

**17.2 SAF-11 and SAF-18/K6 against the pilot's actual staffing.** Pace is bounded by verification capacity, and capacity collapses to zero if reviewers become unavailable. The pilot has four reviewers with distinct lenses and no redundancy: on the capacity formula in `06-review-lenses.md`, throughput is set by the narrowest lens, so one person's absence does not reduce capacity proportionally, it reduces it to zero for every draft needing that lens. K6 then stops the project. This is arguably correct behaviour, and it is also a single point of failure that the doctrine has not acknowledged anywhere else. **Resolved 2026-08-07 by owner decision:** every lens now carries a named backup forming a ring (`06-review-lenses.md` §9.1, `REV-B1`), and a lens without one is a `BLOCK` above the ONB-13 corpus threshold. Capacity during substitution is roughly halved rather than unchanged, and the arithmetic is stated explicitly. **Residual: the ring covers one absence, not two adjacent ones, and it has never met a holiday season.**

**17.3 SAF-14 against P11's framing.** P11 presents the human review log as closing three obligations at once, including the AI Act exemption. That is true only where the reviewer holds relevant qualification and the recorded change is substantive. A log entry from an unqualified reviewer with an empty change record satisfies P11 as written and fails Art. 50 as written. `06-review-lenses.md` already treats an empty `substantive_changes` field as a blocker, which closes the gap, but P11's own text is looser than the requirement it claims to satisfy. **Recommend tightening P11's wording in the next revision; not fixed here, since P11 is not this section's to amend.**

**17.4 SAF-04's thresholds are Level C and are stated as if operational.** The ≥500-word and ≤40%-template numbers come from practitioner blogs with no primary evidence, and this section labels them accordingly. But labelling does not prevent use, and a number in a doctrine acquires authority regardless of its footnote. The strip test and the non-LLM-source test are the real gates; the numbers are diagnostics. **If the pilot never runs programmatic pages, these thresholds should be removed rather than left to accumulate credibility unearned.**

**17.5 The kill switch has never been tested.** Every trigger in SAF-18 is derived from reasoning about documented cases, not from having watched the switch fire correctly. K1 depends on the cohort monitor, which `08-measurement.md` §14.6 already flags as having insufficient cohort sizes at the pilot's publishing volume, resolved there by moving to quarterly cohorts, which lowers sensitivity. The kill switch is therefore least sensitive exactly where it is most needed: early, on a small corpus. **Compensate with K2, K4 and K5, which do not depend on cohort statistics, and treat K1 as a slow backstop rather than the primary trigger during the first two quarters.**

**17.6 Extraterritoriality of Art. 50 is unresolved and gates a real decision.** Stated in §9 and repeated here so it is not lost: this needs a lawyer before the framework is used on a project with genuine EU exposure. No further research agent will settle it.
