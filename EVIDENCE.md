# Evidence base

Every rule in `doctrine/` cites this file. If a rule has no citation here and no
`[internal observation, unpublished]` marker, it is unsupported and should be challenged.

**Evidence classes**, used consistently throughout the doctrine:

| Class             | Meaning                                                                  |
| ----------------- | ------------------------------------------------------------------------ |
| `[official]`      | first-party documentation from the platform whose behaviour is described |
| `[peer-reviewed]` | published through academic peer review                                   |
| `[preprint]`      | arXiv or similar; not peer reviewed                                      |
| `[controlled]`    | measurement with a control group or a split test                         |
| `[correlation]`   | observed association, causation not established                          |
| `[vendor]`        | published by a party selling a product in the same market                |
| `[practitioner]`  | practitioner report, blog, or forum, no disclosed methodology            |
| `[leak]`          | the May 2024 Google Content Warehouse API documentation leak             |
| `[patent]`        | granted patent or published application                                  |
| `[unverified]`    | claim we could not trace to a primary source                             |

Two warnings that apply to the whole file.

**A patent is not an implementation.** A granted patent proves an idea was filed, nothing more.
Several widely repeated claims in this field cite patents as though they described shipped systems.

**A vendor measuring its own product is not neutral, even when the data is real.** Several of the
strongest datasets here are `[vendor]`. They are included because the methodology was disclosed and
the finding cuts against the vendor's commercial interest, which is stated per entry where it
applies. Where a vendor's data supports its own product, it is marked and discounted.

All URLs verified 2026-08-07 unless stated otherwise.

---

## e01. Answer engines and citation {#e01-geo-answer-engines}

**No special markup exists for AI surfaces.** Google states there are no additional requirements
and no schema.org type needed to appear in AI Overviews or AI Mode. `[official]`

- https://developers.google.com/search/docs/appearance/ai-features — updated 2025-12-10
- https://developers.google.com/search/docs/fundamentals/ai-optimization-guide — updated 2026-07-10

**AI crawlers do not execute JavaScript.** Analysis of roughly 500 million crawler fetches found no
JS rendering by the major AI crawlers, meaning a client-rendered site is invisible to them while
remaining visible to Google. `[controlled]`

- Vercel + MERJ, 2024-12-17 — https://vercel.com/blog/the-rise-of-the-ai-crawler

**Ranking position is no longer a gate for citation.** The share of AI Overview citations drawn
from the top ten results fell from roughly 76% to 38% between mid-2025 and March 2026.
`[vendor]` `[correlation]`

- https://news.designrush.com/ai-overview-citations-drop-ahrefs

**Click-through falls when an AI summary is present.** A panel of ~900 users over 68,879 searches
found clicks dropping from 15% to 8% when an AI summary appeared, with links inside the summary
clicked about 1% of the time. `[controlled]`

- Pew Research Center, 2025-07-22 — https://www.pewresearch.org/short-reads/2025/07/22/google-users-are-less-likely-to-click-on-links-when-an-ai-summary-appears-in-the-results/

**The only peer-reviewed intervention study.** Adding statistics, expert quotations and source
citations raised visibility in a prototype generative engine; keyword stuffing lowered it. Weaker
sites gained most. **Measured on a prototype, not on live engines** — treat magnitudes as
directional only. `[peer-reviewed]`

- Aggarwal et al., "GEO: Generative Engine Optimization", arXiv:2311.09735, KDD 2024 —
  https://arxiv.org/abs/2311.09735 · https://dl.acm.org/doi/abs/10.1145/3637528.3671900

**Off-site brand signals correlate more strongly than backlinks.** Across ~75,000 brands, YouTube
mentions correlated 0.737 and brand mentions 0.664 with AI citation, against roughly 0.19–0.24 for
backlinks. The authors state plainly that correlation is not causation. `[vendor]` `[correlation]`

- https://ahrefs.com/blog/ai-overview-brand-correlation/ — 2025-05-26
- https://ahrefs.com/blog/ai-brand-visibility-correlations/ — 2025-12-12

**Contradicting the above.** A separate study found citation and brand mention only weakly related,
with a negative correlation and 62% of citations producing no brand mention. Both datasets are
vendor-published and they disagree; the doctrine therefore tracks citation and mention as two
separate metrics rather than assuming one drives the other. `[vendor]` `[correlation]`

- https://www.semrush.com/blog/the-ghost-citations-study/
- https://www.semrush.com/news/463141-semrush-releases-expanded-2026-ai-visibility-index-analyzing-126-million-ai-search-prompts/

**Per-bot robots.txt granularity matters more than blocking policy.** Search bots and training
bots are separate agents; blocking a training crawler does not affect visibility, while blocking a
search crawler removes it entirely. `[official]` `[practitioner]`

- https://developers.openai.com/api/docs/bots
- https://www.searchenginejournal.com/anthropics-claude-bots-make-robots-txt-decisions-more-granular/568253/

**Infrastructure became a ranking-adjacent variable.** A major CDN moved to blocking mixed-purpose
AI crawlers by default and to a pay-per-use model. `[practitioner]`

- https://techcrunch.com/2026/07/01/cloudflares-new-policy-pushes-ai-companies-to-pay-for-publishers-content/
- https://www.transparencycoalition.ai/news/cloudflare-becomes-first-infrastructure-provider-to-block-ai-crawlers-by-default

**Search Console reports AI-surface impressions only** — no queries, clicks, CTR or position, with
AI Overviews and AI Mode merged. `[official]`

- https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports — 2026-06-03

### Circulating claims we could not source `[unverified]`

Do not build rules on these. Each is widely repeated with no traceable primary publication:
"ChatGPT uses the Bing index"; "semantic completeness r=0.87"; "structured data +73% selection
rate"; specific source-share percentages such as "Wikipedia 47.9%"; "embedding optimization,
cosine >0.88 → 7.3× citation" (unfalsifiable — each platform's embedding model is not externally
measurable).

---

## e02. Practitioner consensus and update history {#e02-practitioner-pulse}

**Zero-click is the majority case.** Clickstream analysis puts 68.01% of Google searches in early
2026 ending without a click; on 1,000 searches roughly 276 clicks reach the open web, down from 374
in 2024. `[correlation]`

- https://sparktoro.com/blog/in-2026-less-than-one-third-of-google-searches-still-send-a-click/
- https://searchengineland.com/google-zero-click-searches-2026-study-479717

**The CTR impact is still worsening, not stabilising.** Two measurement waves by the same team
found −34.5% then −58%. `[vendor]`

- https://ahrefs.com/blog/ai-overviews-reduce-clicks/ — wave 1
- https://www.businesswire.com/news/home/20260518322756/en/New-Research-Googles-AI-Overviews-Now-Cost-Websites-58-of-Their-Clicks — 2026-05-18

**Self-promotional listicles damage the whole domain.** Across 100 queries, pages ranking
themselves first were cited in 69% of cases but the answer recommended a competitor; the effect was
domain-wide, not page-level. `[practitioner]`

- https://almcorp.com/news/self-promotional-listicles-ai-overviews-help-competitors-lily-ray-study/

**Google does not penalise AI content as such.** One million pages and 100,000 SERPs: correlation
between AI-detected share and ranking position was 0.011, statistical noise. 5.3% of top-3 results
were fully AI-generated. Vendor-published, but the finding cuts against the detection market's
commercial interest. `[vendor]` `[correlation]`

- https://ahrefs.com/blog/google-doesnt-punish-ai-content/ — 2026-07-27

**Core and spam update history**, used for dating cohort effects: `[official]`

- https://status.search.google.com/products/rGHU1u87FJnkP6W2GwMi/history
- https://www.seroundtable.com/google-march-2026-core-update-complete-41145.html — 2026-04-08
- https://www.seroundtable.com/google-may-2026-core-update-done-41435.html — 2026-06-02
- https://www.seroundtable.com/google-june-2026-spam-update-done-41580.html — 2026-06-26
- https://www.seroundtable.com/february-2026-google-discover-core-update-done-41006.html — 2026-02-27

**Pages that let the user finish the task outperform.** Winners let users complete an action on the
page in 84% of cases against 50% for losers. `[practitioner]`

- https://www.digitalapplied.com/blog/ai-search-citation-ranking-factors-2026-data-study

**Note on a paywalled source.** A widely cited practitioner conclusion that "most AI SEO advice
does not survive testing at scale" sits behind a subscription and **was not verified**.
`[unverified]`

---

## e03. Detection, style, and human-sounding writing {#e03-ai-detection-and-humanization}

**Detectors are not a ranking signal.** See the 0.011 correlation under e02. No evidence exists
that any search engine uses an AI detector as a ranking input, and Google has declined to confirm
one when asked directly. `[correlation]` `[practitioner]`

- https://ppc.land/googles-john-mueller-warns-ai-seo-acronyms-signal-spam-tactics/ — 2026-06

**Vendors overstate detector accuracy by 15–30 points.** Independent runs give 66–92% depending on
detector and dataset against claimed 99%+. Two vendors interpret the same benchmark in opposite
directions, which is itself reason to distrust both summaries. `[practitioner]` `[vendor]`

- https://fast.io/resources/ai-detector-accuracy-comparison-2026/
- https://gptzero.me/news/chicago-booth-2026/ · https://www.pangram.com/blog/third-party-pangram-evals

**Modern detectors no longer rely on perplexity**, which kills the entire "raise perplexity /
break burstiness" family of evasion advice. No systematic bias against non-native speakers was
found. `[preprint]`

- Al Ali, Helcl, Libovický, arXiv:2602.05769 — 2026-02-06

**What actually separates human from machine text.** Across nine languages and 19 annotators,
humans identified machine text with 87.6% accuracy, and the gap ran along three axes:
**concreteness, cultural nuance, diversity** — not vocabulary or sentence length. This is the
empirical basis for principle P4. `[preprint]`

- arXiv:2502.11614 — https://arxiv.org/abs/2502.11614

**Lexical overrepresentation has a documented mechanism.** Words whose frequency recently spiked in
academic abstracts match the words models overuse. `[peer-reviewed]`

- Juzek & Ward, "Why Does ChatGPT 'Delve' So Much?", COLING 2025 —
  https://aclanthology.org/2025.coling-main.426/

**The most complete practical marker list** is maintained collectively by editors reviewing
thousands of suspect edits. `[practitioner]`

- https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing
- Russian-language equivalent — https://ru.wikipedia.org/wiki/Википедия:Признаки_сгенерированности_текста

**No Ukrainian research exists.** No academic study and no collectively maintained marker list for
Ukrainian was found. The Ukrainian language pack is therefore built by analogy from Russian plus
language-independent metrics, and every lexical entry in it carries `status: hypothesis`.
Practitioner observations only: `[practitioner]`

- https://www.rbc.ua/rus/styler/dayte-sebe-obduriti-5-oznak-shcho-tekst-napisav-1747236652.html
- https://theinweb.media/yak-vidrizniti-tekst-ai/

**Humanizer services are unsupported.** Every located "test" was published by a party selling a
humanizer or by an affiliate. No independent measurement exists. `[vendor]`

**Google's position, quoted.** Spam policy applies regardless of how content was produced: "AI,
automation, or human beings. It's going to be an issue." Policy last updated 2026-05-15 and
extended to cover generative responses. `[official]`

- https://developers.google.com/search/docs/essentials/spam-policies
- https://developers.google.com/search/blog/2023/02/google-search-and-ai-content
- https://ppc.land/google-spam-policies-now-officially-cover-ai-overviews-and-ai-mode-in-search/

**Google advises against chunking content for machines.** `[practitioner]` reporting on an official
statement, 2026-01-08

- https://searchengineland.com/google-doesnt-want-you-to-create-bite-sized-chunks-of-your-content-467269

**Invisible characters leak from model output** (zero-width, U+202F) and are trivially detectable;
they must be stripped automatically. `[practitioner]`

- https://lifehacker.ru/nevidimye-simvoly-chatgpt/

**Could not verify.** A Nature article on detector performance sat behind authentication; a Vrije
Universiteit Brussel study is known only through secondary retellings on sites affiliated with the
detection market. Both excluded. `[unverified]`

---

## e04. Search Console as a data source {#e04-search-console}

**API limits and behaviour.** 25,000 rows per request; 50,000 rows per search type per site per
day; 16-month horizon; hourly data retained 8 days only. `[official]`

- https://developers.google.com/webmaster-tools/v1/searchanalytics/query
- https://developers.google.com/webmaster-tools/limits

**Rare queries are anonymised by design**, so the sum over the query dimension does not reconcile
with the property total. This is documented behaviour, not a bug. `[official]`

- https://developers.google.com/search/blog/2022/10/performance-data-deep-dive

**Reporting lag is 2–4 days**, stretching to 5–7 during system updates, with multi-week incidents
on record. The practical rule of cutting the trailing 3–4 days is practitioner convention, not a
guarantee. `[official]` for the incident, `[practitioner]` for the rule

- https://searchengineland.com/google-search-console-performance-reports-delays-fixed-466290

**BigQuery bulk export** removes row limits but rows are **not deduplicated**, anonymised queries
arrive as an empty string rather than NULL, and `epoch_version` is the only signal that history was
rewritten. `[official]`

- https://support.google.com/webmasters/answer/12918484
- https://support.google.com/webmasters/answer/12917991 · https://support.google.com/webmasters/answer/12917174
- https://developers.google.com/search/blog/2023/06/bigquery-efficiency-tips

**CTR curves.** Two are required: clean SERP and AI-Overview-present. Published curves vary widely
between studies (position one ranges 19–39.8% across sources), so they are priors to be calibrated
locally, never absolute forecasts. `[practitioner]` `[correlation]`

- First Page Sage meta-analysis via https://indexsy.com/ctr-statistics/
- Seer Interactive, 3,119 informational queries via https://wordsatscale.com/ai-overviews-ctr-statistics-2026/

**Cannibalization detection method**, including keeping a query only when the second URL has
non-zero clicks, and using embedding similarity around 0.9 to separate "merge" from "differentiate".
`[practitioner]`

- https://www.jcchouinard.com/keyword-cannibalization-tool-with-python/
- https://www.searchenginejournal.com/find-keyword-cannibalization-using-openai-text-embeddings-examples/520274/
- https://www.thatdevpro.com/insights/framework-gscanalysis/ — thresholds are heuristics, stated as such

**Bing offers the same query×page slice free**, plus IndexNow for immediate change notification.
`[official]`

- https://learn.microsoft.com/en-us/bingwebmaster/ · https://www.indexnow.org/documentation

**Open-source prior art**, MIT unless noted: `[practitioner]`

- https://github.com/AminForou/mcp-gsc · https://github.com/saurabhsharma2u/search-console-mcp
- https://github.com/allanreda/SEO-Keyword-Cannibalization-Detector

---

## e05. Keyword core and clustering {#e05-semantics-and-clustering}

**SERP-overlap clustering is no longer expensive.** The historical objection was priced against
$9–25 per 1,000 queries; current standard-queue pricing is $0.60 per 1,000, making a 5,000-query
core cost roughly $3. Every heuristic designed to conserve SERP calls is therefore obsolete.
`[vendor]` pricing pages

- https://dataforseo.com/apis/serp-api/pricing — July 2026

**Search volume no longer predicts traffic** but still filters out zero-demand noise. See the
zero-click figures under e02. `[correlation]`

**Query fan-out is documented by Google**, which describes breaking a question into subtopics and
issuing many queries simultaneously. The subquery count is not published; practitioner estimates
run 8–16. The operational consequence is coverage of facets **within one document**, explicitly not
one thin page per facet. `[official]` via `[practitioner]` analysis

- https://www.aleydasolis.com/en/ai-search/google-query-fan-out/

**Intent taxonomy with an academic basis.** A user-centered framework proposing knowledge /
guidance / output-seeking, applicable to both search and chat interfaces, explicitly challenging
the 1992 Broder taxonomy. Full text paywalled. `[peer-reviewed]`

- Lichtenegger, Urman, Hannak, CHI 2026 — https://dl.acm.org/doi/10.1145/3772318.3791050

**Keyword Planner volumes are bucketed and semantically merged**, which is the source of most
volume distortion. `[official]`

- https://developers.google.com/google-ads/api/docs/keyword-planning/generate-keyword-ideas

**Open-source prior art.** SERP-overlap clustering with built-in SERP caching, graph clustering via
overlap coefficient, and an MCP server for the same task: `[practitioner]`

- https://github.com/FassihFayyaz/SEO-Clustering-Tool · https://github.com/MarcoGiordano96/SERP-Clustering
- https://github.com/dredozubov/mcp-serp-clustering · https://github.com/HasData/python-for-seo

---

## e06. Internal linking and topical authority {#e06-internal-linking}

**The only controlled evidence in this area comes from SEO split testing.** Category buttons at the
top of the body produced +25% organic sessions; geographic links +7%; footer links from the home
page +5%. A test that **reduced** the number of links in a module produced a positive result, and
the testing team states directly that "more internal linking is better" is probably not optimal.
`[controlled]`

- https://www.searchpilot.com/resources/case-studies/seo-split-test-lessons-increasing-internal-linking
- https://www.searchpilot.com/resources/case-studies/impact-of-internal-linking-seo
- https://www.searchpilot.com/resources/blog/internal-linking-tests · https://www.searchpilot.com/data-analysts

**Irrelevant internal links are harmful, not neutral.** The leaked documentation contains
`anchorMismatchDemotion`, and counts internal and external anchors separately via
`SimplifiedAnchor`, meaning an internal anchor profile degrades independently. `[leak]`

- https://ipullrank.com/google-algo-leak
- https://searchengineland.com/unpacking-googles-massive-search-documentation-leak-442716

**Link weight is proportional to click probability**, driven by position on the page, font size and
topical relatedness of the anchor. This is the mechanism behind the split-test results above.
`[patent]`

- US8117209B1, filed 2004, granted 2010-05-11 — https://patents.google.com/patent/US8117209B1/en
- https://searchengineland.com/seo-implications-of-googles-reasonable-surfer-patent-44222

**Google on link volume**, quoted: if every page links to every other page "there is no structure
there… we can't tell which one is the most important". `[official]`

- https://www.searchenginejournal.com/google-cautions-against-using-too-many-internal-links/412553/

**Topical focus is computable.** `siteFocusScore` and `siteRadius` appear in the leak as measures of
how tightly a site holds one topic and how far a page's embedding sits from the site centroid.
`[leak]` with `[practitioner]` interpretation

- https://www.hobo-web.co.uk/topical-authority/ · https://www.szymonslowik.com/sitefocus-siteradius-and-topical-authority-in-seo/

**Extraction operates at passage level**, so "related reading" blocks, sidebars and footers do not
enter the cited fragment. Roughly 44% of LLM citations come from the first third of a document.
`[practitioner]`

- https://www.lumar.io/blog/best-practice/content-chunking-ai-extractability-geo-aeo-explainer/
- https://www.getpassionfruit.com/blog/how-llms-search-for-citations-what-they-look-for-and-what-they-actually-find

**Embedding thresholds in practice**: 0.78–0.85 workable, below 0.50 noise. Practitioner figure, not
validated. `[practitioner]`

- https://nikoalho.fi/writing/automating-internal-linking/

**The glossary-as-foundation model.** A finance reference site's A–Z definition glossary reportedly
drives ~44 million visits per month, with most definition pages over 2,000 words. `[practitioner]`

- https://www.spicymargarita.co/archive/investopedia-seo-case-study

**Editorial linking convention** worth copying: link on first occurrence, and only where reading the
target would help the reader understand the current passage. `[practitioner]`

- https://en.wikipedia.org/wiki/Wikipedia:Manual_of_Style/Linking

### Not established `[unverified]`

"+30% traffic from 3+ contextual links", "+43% organic", "10 internal links is optimal", "94% of top
pages are within 3 clicks of the home page" — all before/after without a control group, or secondary
citations whose primary publication could not be confirmed. Usable as hypotheses only.

---

## e07. Competitive intelligence {#e07-competitive-intelligence}

**Real competitors are identified through the SERP, not by assumption** — domains ranking top-5 for
the core, regardless of industry or business model. `[practitioner]`

- https://www.eliteasia.co/how-to-do-an-seo-competitor-analysis-in-2026/ · https://focalfrog.com/blogs/seo-competitor-analysis-guide

**AI competitors require a separate method**: 20–30 high-intent prompts run across engines, logging
which brands are mentioned and which URLs cited. `[practitioner]`

- https://www.optimizegeo.ai/blog/ai-competitor-research · https://clairon.ai/blog/competitor-citation-analysis

**No canonical thresholds are published.** The one commercial competitor-similarity metric is
proprietary, computed over 500 fresh SERPs and returning up to 25 competitors, with the formula
undisclosed. All thresholds in the doctrine are therefore our own and marked for calibration.
`[vendor]`

- https://aithority.com/technology/native-and-programmatic-advertising/moz-launching-new-competitor-analysis-tool-and-metric/

**Weighted share of voice beats flat counting**, since position one is worth far more than position
ten. `[practitioner]`

- https://cloro.dev/blog/competitor-seo-tracking/

**Sitemap diffing is the cheapest signal in the discipline** — a competitor's new URL appears in
their sitemap within hours of publication. `[practitioner]`

- https://monity.ai/guides/monitor-competitor-sitemap-xml-new-urls
- https://apify.com/tri_angle/sitemap-change-detector

**Daily granularity is required for money keywords**, because AI Overviews and SERP features flip
within a week; weekly sampling cannot separate "an AI Overview appeared" from "we lost rankings".
Estimated volatility ~12 changes per key per month, AI Overviews present in 15–25% of searches.
`[practitioner]`

- https://agencydashboard.io/blog/rank-tracking-ai-search-visibility
- https://www.therankmasters.com/insights/ai-visibility/best-ai-rank-tracking-serp-monitoring-tools

**Legal boundary: the dividing line is login, not scraping.** The Ninth Circuit held that scraping
publicly accessible profiles does not violate the CFAA, but the same plaintiff was found to have
breached terms it accepted by creating accounts. A later summary judgment held that terms did not
prohibit scraping public data while logged out. Coverage is US-only; other jurisdictions were not
researched. `[practitioner]` summaries of case law

- https://use-apify.com/docs/what-is-apify/is-apify-legal · https://www.browserless.io/blog/is-web-scraping-legal

**Disputed pricing.** One endpoint's price differs between the vendor's own pricing page and
third-party guides; verify against documentation before relying on it. `[vendor]`

- https://dataforseo.com/pricing/dataforseo-labs/dataforseo-google-api vs https://nextgrowth.ai/dataforseo-api-guide/

---

## e08. Trend and demand detection {#e08-trend-detection}

**The Google Trends API is not usable.** Announced 2025-07-24, still application-gated alpha a year
later with no self-serve access and no published GA timeline. Even with access, quotas work out to
roughly five terms per day at daily resolution. `[official]` announcement, `[practitioner]` status

- https://developers.google.com/search/blog/2025/07/trends-api — 2025-07-24
- https://scrapebadger.com/blog/does-google-trends-have-an-api-what-to-use-in-2026
- https://willmanntobias.medium.com/some-first-discoveries-testing-google-trends-api-v1alpha-7580a31cef01

**The main library is dead** — archived 2025-04-17, read-only. Direct scraping returns 429 after
10–15 requests per IP and violates terms. `[practitioner]`

- https://apiserpent.com/blog/pytrends-dead-google-trends-data-2026

**Web Trends normalises 0–100 within each query**, so two queries cannot be joined and no more than
five terms compared. This is the single most misunderstood property of the data source.
`[official]`

- https://newsinitiative.withgoogle.com/resources/trainings/basics-of-google-trends/

**Hourly Search Console data is retained 8 days**, which is why archiving must run daily rather than
on demand. `[official]` limits, `[practitioner]` for the newsjacking application

- https://developers.google.com/webmaster-tools/limits
- https://www.playwire.com/blog/seo-publishing-best-practices-what-the-data-in-google-search-console-is-telling-you

**Reddit has no viable commercial tier** between the free 100 QPM allowance and enterprise pricing
reported at $12,000/month. Its value is that it shows how people phrase a problem before it becomes
a query. `[practitioner]`

- https://www.techloy.com/reddit-api-pricing-in-2026-complete-guide-for-developers-and-businesses/
- https://ahrefs.com/blog/reddit-keyword-research

**GDELT is the strongest free news signal**: no hard quotas, 100+ languages, topic-level volume over
time. `[official]`

- https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/ · https://github.com/alex9smith/gdelt-doc-api

**Google News RSS is contractually closed to commercial use.** Terms restrict it to personal
non-commercial use and prohibit robots. Excluded from the framework. `[official]`

- https://www.google.com/intl/en_us/terms_google_news.html

**Free quotas elsewhere**: YouTube 10,000 units/day with search costing 100 units, so ~100 searches
daily; Hacker News via Algolia at 10,000 requests/hour; no commercial TikTok research API exists.
`[practitioner]`

- https://www.getphyllo.com/post/youtube-api-limits-how-to-calculate-api-usage-cost-and-fix-exceeded-api-quota
- https://support.algolia.com/hc/en-us/articles/44485795695889-Rate-Limits
- https://www.xpoz.ai/blog/guides/tiktok-research-api-limits-access-and-alternatives/

**Anomaly detection method.** Rolling z-score is the standard baseline; comparing a short window
against a longer overlapping window handles noise. The doctrine uses median and MAD instead of mean
and standard deviation because outliers inflate the very sigma used to detect them. `[practitioner]`

- https://www.tinybird.co/blog/anomaly-detection
- https://medium.com/booking-com-development/anomaly-detection-in-time-series-using-statistical-analysis-cc587b21d008

### Priors, not constants `[unverified]`

Seasonal lead time of "3–6 months before peak" is practitioner consensus with no measurement behind
it. Content freshness half-lives and the claim that AI-cited content is 25.7% fresher come from
blogs without disclosed methodology. All are configurable parameters in the doctrine, never
hard-coded.

---

## e09. Platform capabilities and limits {#e09-platform-capabilities}

All `[official]`, verified 2026-08-07. These constrain what the framework can enforce and how it can
be scheduled.

- Plugins and directory structure — https://code.claude.com/docs/en/plugins ·
  https://code.claude.com/docs/en/plugins-reference
- Marketplaces and dependencies — https://code.claude.com/docs/en/plugin-marketplaces ·
  https://code.claude.com/docs/en/plugin-dependencies
- Hooks, the only mechanism that can enforce a gate rather than advise —
  https://code.claude.com/docs/en/hooks · https://code.claude.com/docs/en/hooks-guide
- MCP servers — https://code.claude.com/docs/en/mcp
- Memory and project context — https://code.claude.com/docs/en/memory
- Headless execution — https://code.claude.com/docs/en/headless
- CI integration — https://code.claude.com/docs/en/github-actions
- Scheduling options — https://code.claude.com/docs/en/routines ·
  https://code.claude.com/docs/en/desktop-scheduled-tasks
- Inbound channels, allowlisted and session-bound — https://code.claude.com/docs/en/channels

**Consequences the doctrine depends on.** A plugin's own `CLAUDE.md` is not loaded, so context must
arrive through a skill or a session-start hook. Plugin-provided agents cannot declare hooks, MCP
servers or permission modes. Inbound webhooks into a live session are effectively unavailable, so
scheduling is CI-based. The plugin root is replaced on update, so no state may be written there.

---

## e10. E-E-A-T, entities and structured data {#e10-eeat-entities-schema}

**Quality Rater Guidelines**, 182 pages, revision dated 2025-09-11. Raters do not influence ranking
directly. `[official]`

- https://guidelines.raterhub.com/searchqualityevaluatorguidelines.pdf
- https://www.seroundtable.com/google-search-quality-raters-guidelines-update-40092.html

**Lowest quality is defined by three multiplied factors** — little to no effort, originality, or
added value — explicitly "regardless of whether it was written by a human or AI". `[official]`

**No AI-specific schema exists**, and facts present in markup but absent from visible text carry
cloaking risk. `[official]`

- https://developers.google.com/search/docs/appearance/structured-data/sd-policies
- https://developers.google.com/search/docs/appearance/ai-features

**LLMs do not parse JSON-LD semantically.** An experiment placed an address inside deliberately
invalid, fabricated JSON-LD and multiple assistants extracted it, indicating the block is
tokenised as ordinary text. Not independently reproduced. `[practitioner]`

- https://markwilliamscook.substack.com/p/schema-llms-and-the-low-bar-for-evidence
- https://www.searchenginejournal.com/schema-llms-the-low-bar-for-evidence-in-geo/576090/

**FAQ rich results were withdrawn in May 2026.** The schema type is not deprecated; only the rich
result is gone. `[practitioner]` reporting a `[official]` documentation change

- https://www.getpassionfruit.com/blog/what-changed-with-google-drops-faq-rich-results-and-what-to-do-now
- Current gallery of supported types — https://developers.google.com/search/docs/appearance/structured-data/search-gallery

**llms.txt is not used.** Across 137,000 domains, 97% of these files received no requests in a
month. Google's position is that it neither helps nor hurts. `[vendor]` data, `[official]` position

- https://ahrefs.com/blog/llmstxt-study/
- https://www.searchenginejournal.com/google-says-llms-txt-is-purely-speculative-for-now/577576/

**EU AI Act Article 50 applies from 2026-08-02.** AI-generated text informing the public on matters
of public interest must be disclosed. The exemption is human review amounting to deliberate
examination of the substance by a person with relevant competence; a footer or terms page is
explicitly insufficient. Penalties reach €15M or 3% of turnover. `[official]`

- https://artificialintelligenceact.eu/article/50/
- https://digital-strategy.ec.europa.eu/en/policies/guidelines-transparency-ai-generated-content
- https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act
- https://datamatters.sidley.com/2026/06/24/eu-ai-act-transparency-obligations-preparing-for-compliance-by-2-august-2026/

**Extraterritorial application to a non-EU operator serving non-EU users was not researched** and
remains an open question in `doctrine/OPEN-QUESTIONS.md`. `[unverified]`

---

## e11. Content quality signals {#e11-content-quality-signals}

**The Information Gain patent says something narrower than commonly claimed.** The score is computed
**relative to documents already shown to one specific user within a session**, by a model trained on
human-labelled pairs. Since we hold no per-user reading history, a page-level "information gain
score" is not computable; every product selling one is measuring difference from the top results,
which is a legitimate proxy under an inaccurate name. `[patent]`

- US11354342B2, filed 2018-10-18, granted 2022-06-07 — https://patents.google.com/patent/US11354342B2/en
- Continuations US12013887B2, US20200349181A1

**Claims that information gain is a live ranking factor are unsupported.** A patent is not an
implementation. `[unverified]`

**Content Warehouse leak, attributes relevant to quality.** Verbatim strings via the most complete
public analysis: `[leak]`

- `contentEffort` — "LLM-based effort estimation for article pages". Google already judges content
  by machine, and the criterion is how easily it could be reproduced.
- `OriginalContentScore` — "7-bits, 0..127. Only pages with little content have this field", i.e.
  applied only to short pages. A widely repeated "0–512" range is a retelling error that inverts the
  conclusion.
- `siteAuthority` — "converted from quality_nsr.SiteAuthority, applied in Qstar".
- `semanticDate` — date estimated from content, anchors and related documents, which is how
  template-level date manipulation becomes detectable.
- https://ipullrank.com/google-algo-leak · https://sparktoro.com/blog/an-anonymous-source-shared-thousands-of-leaked-google-search-api-documents-with-me-everyone-in-seo-should-see-them/
- Interpretation: https://www.hobo-web.co.uk/what-is-googles-content-effort-signal/ ·
  https://www.hobo-web.co.uk/qualitynsrpqdata/

**Click signals are confirmed under oath**, described in US DOJ testimony as one of the important
signals, with 13 months of aggregated data narrowing tens of thousands of candidates to hundreds.
This does **not** imply click manipulation works; the same system is designed against anomalous
clicks. `[official]` testimony via `[practitioner]` summary

- https://www.hobo-web.co.uk/navboost-how-google-uses-large-scale-user-interaction-data-to-rank-websites/

**Helpful content guidance**, updated 2025-12-10, names red flags the doctrine encodes directly:
mass production, extensive automation, restating without adding, **writing to a word count**, date
manipulation, and leaving the reader needing to search again. It also asks publishers to disclose AI
involvement and explain why it was useful. `[official]`

- https://developers.google.com/search/docs/fundamentals/creating-helpful-content

**Vendor content scores correlate weakly with position** — 0.28 on one vendor's own data, 17.5% for
another, leaving roughly three quarters of variance outside the score. Pages scoring 85+ have been
documented on page three, and pages scoring 60–70 in position one. No independent validation of any
vendor score exists. `[vendor]`

- https://backlinko.com/information-gain (targets 10–40% original content without giving a
  measurement method) `[practitioner]`

---

## e12. Data sources and pricing {#e12-data-apis-and-pricing}

Prices verified 2026-08-05 to 2026-08-07 from vendor pricing pages. All `[vendor]`. Prices move;
treat as an order-of-magnitude guide and re-check before committing.

**SERP APIs.** Standard-queue pricing around $0.60 per 1,000 is roughly fifteen times cheaper than
subscription-only alternatives at $9–25. AI-Overview-inclusive results cost 4–15× more than plain
results, which is why the doctrine tracks AI presence only on priority queries.

- https://dataforseo.com/pricing/google-serp/google-organic-serp-api · https://serpapi.com/pricing
- https://coldiq.com/blog/serper-pricing — note that credits expire after six months

**Full-suite APIs are out of scope for a portable framework** at $500–10,000/month entry points.

- https://thatmarketingbuddy.com/blog/semrush-api-pricing

**Backlinks** differ by two orders of magnitude between providers.

- https://dataforseo.com/blog/backlink-api-value-for-money · https://majestic.com/account/api

**Crawling and rendering.** A free-tier reader API at 500 RPM covers most needs; paid crawlers matter
only where JS rendering is required.

- https://jina.ai/reader/ · https://www.firecrawl.dev/pricing · https://apify.com/pricing

**First-party data is free and generous**: Search Console 1,200 QPM per site, Bing 10,000 URLs/day,
IndexNow unlimited.

- https://developers.google.com/webmaster-tools/limits · https://www.indexerhub.com/blog/bing-indexing-api

**LLM inference dominates per-article cost**, spanning roughly a 24× range between frontier and
lightweight models. Embeddings are effectively free at this scale.

- https://developers.openai.com/api/docs/pricing · https://ai.google.dev/gemini-api/docs/pricing
- https://docs.voyageai.com/docs/pricing

**AI-visibility subscriptions run $29–489+/month** and are replaceable by a self-run prompt set at a
few dollars monthly, which also yields the raw answers needed for calibration.

- https://acromatico.com/ai-visibility-tool-pricing-compared · https://www.surmado.com/blog/best-ai-visibility-tools-2026

---

## e13. Policy, enforcement and risk {#e13-policy-and-risk}

**Scaled content abuse, quoted.** Pages generated "for the primary purpose of manipulating search
rankings and not helping users" — three conditions that must coincide. Last updated 2026-05-15, and
extended on 2026-07-24 to cover attempts to manipulate generative responses in Search. `[official]`

- https://developers.google.com/search/docs/essentials/spam-policies
- https://developers.google.com/search/updates

**There is no manual action for scaled content abuse.** The official manual actions list does not
contain it, so the penalty arrives algorithmically and silently. Detection must therefore be
cohort-based rather than console-based. This contradicts widespread industry assertion. `[official]`

- https://support.google.com/webmasters/answer/9044175

**Site reputation abuse is the one fully documented enforcement event.** Major publisher
subdirectories fell from tens of millions of visits to the low thousands, in one case losing
99.95%. Comparable operations with in-house editorial teams were unaffected. The distinguishing
factor was **structural — in-house versus outsourced partner — not text quality.** Since
2024-11-19, first-party involvement including white-label arrangements, licensing and ownership
stakes is explicitly not a defence. `[practitioner]` reporting on `[official]` policy

- https://www.searchenginejournal.com/google-strengthens-policy-against-site-reputation-abuse/533018/
- https://growtika.com/blog/publisher-affiliate-collapse
- https://pressgazette.co.uk/platforms/google-dealt-blow-to-publisher-shopping-revenue-on-eve-of-black-friday-site-reputation-abuse-update/

**Recovery takes 14+ months to partial, and no full recovery is documented.** `[practitioner]`

**Programmatic pages survive when each carries a unique record from a real database** and fail when
a template substitutes a variable into prose. `[practitioner]`

- https://www.digitalapplied.com/blog/programmatic-seo-after-march-2026-surviving-scaled-content-ban
- https://www.dualmedia.com/programmatic-seo-2026/

**No credible data on safe publishing pace exists.** Every circulating figure is agency
self-reporting, and the most-cited case study is labelled by its own publisher an "anonymised
composite". The doctrine derives pace from verification capacity instead. `[unverified]`

- https://www.digitalapplied.com/blog/ai-content-h1-2026-retrospective-publishing-velocity-data
- https://www.digitalapplied.com/blog/case-study-ai-content-engine-publisher-100-posts-month-2026

**News and Discover carry separate requirements** — bylines, dates and author information, with
permanent ineligibility for repeated violations. The February 2026 Discover update emphasised
topic-specific expertise within publications covering multiple subjects, which argues against
publishing on any topic that happens to have traffic. `[official]` · `[practitioner]`

- https://support.google.com/news/publisher-center/answer/6204050
- https://searchengineland.com/google-february-2026-discover-core-update-is-now-complete-469450

**Bing and Yandex policies were not researched** and remain a gap. `[unverified]`

---

## e14. Content operations {#e14-content-operations}

**The strongest available evidence on AI content programmes failing.** 220+ domains publicly listed
as customers of AI content platforms, traffic measured through two independent third-party tools:
54% lost ≥30% of peak traffic, 39% lost ≥50%, 22% lost ≥75%. The trajectory repeats — 6–12 months of
growth, a peak, then a collapse frequently below the starting baseline — and most collapses occurred
**after** vendors published success case studies about those same sites. `[practitioner]` with
disclosed method and named tooling

- https://lilyraynyc.substack.com/p/it-works-until-it-doesnt-ai-content-risks

**Zero-click confirmed on clickstream data**: 68.01% of searches in 2026, desktop 79.6%, mobile
54.8%. With an AI Overview present, clicks fall to 8% from 15%. `[correlation]`

- https://www.similarweb.com/blog/marketing/geo/zero-click-marketing/ — 2026-06-10

**Newsroom practice under editorial control.** A major publisher declined to ship a public chatbot
on the grounds that without editorial oversight it would not be their journalism; training focuses
on the nature of probabilistic models rather than prompting technique. One fact-checking
organisation reported 16% of checkable claims being AI-generated in 2025, up from 7%.
`[peer-reviewed]`-adjacent institutional research

- https://reutersinstitute.politics.ox.ac.uk/news/ai-and-future-news-2026-what-we-learnt-about-its-impact-newsrooms-fact-checking-and-news

**The binding constraint is editorial review capacity, not generation speed** — reported
independently by solo practitioners and by teams. `[practitioner]`

- https://aeoinsider.com/ai-content-workflows/
- https://www.heinzmarketing.com/blog/the-ai-content-trap-when-scaling-becomes-a-liability/ — "AI helps
  when it accelerates an expert's thinking, not when it replaces it"

**Hallucination benchmarks.** Summarisation-grounded rates run 3.3%–20.2% across models and rise to
26%–63.8% on domain tasks. **Reasoning-optimised models perform worse on grounded fact-checking**,
adding unsupported interpretation — which is why the doctrine specifies a non-reasoning model for
verification. Retrieval grounding reduces hallucination 15–25%, agentic verification 25–40%.
`[practitioner]` aggregation of published benchmarks

- https://news-factory.app/blog/news-fact-checking-2026

**Role-contract process design** ("editorial mesh"): typed handoffs between researcher, writer,
editor and QA, with QA on a different model family. The shape is useful; the accompanying timing
statistics are low-confidence vendor content. `[practitioner]`

- https://www.digitalapplied.com/blog/agentic-content-operations-ai-editorial-team-2026

**Content economics.** Western full cost per article lands in the $1,000–1,800 range across
freelance, agency and DIY-with-AI routes, with founder time dominating the last. Russian-language
market: 300–1,000 ₽ per 1,000 characters, 5,000–6,000 ₽ for a corporate blog article.
Ukrainian market: from 55 ₴ per 1,000 characters, and from $10 per 1,000 characters for specialists.
The order-of-magnitude gap means cost savings are not the sellable value in those markets.
`[vendor]` with disclosed method · `[practitioner]`

- https://www.averi.ai/how-to/the-true-cost-of-content-in-2026-freelancers-vs.-agencies-vs.-ai-platforms
- https://sdelaem.agency/blog/skolko-stoit-napisat-statyu/ · https://plagiart.com/prices/text/

---

## e15. Market landscape and prior art {#e15-market-landscape}

**Existing extensions in this class are analyzers without memory.** Several sizeable MIT-licensed
skill collections exist; none holds site state, learns from Search Console, or adapts between runs.
`[practitioner]`

- https://github.com/AgriciDaniel/claude-seo · https://github.com/AgriciDaniel/claude-blog
- https://github.com/rampstackco/claude-skills · https://github.com/OpenClaudia/openclaudia-skills
- https://github.com/seranking/seo-skills

**Reusable components**, MIT unless noted: `[practitioner]`

- Search Console MCP servers — https://github.com/AminForou/mcp-gsc ·
  https://github.com/saurabhsharma2u/search-console-mcp · https://github.com/houtini-ai/better-search-console
- Clustering — https://github.com/johnoconnor0/keyword-clustering ·
  https://github.com/searchsolved/search-solved-public-seo · https://github.com/evemilano/keyword_clustering_easy_demo

**Content optimizers measure similarity to the top of the SERP**, which is the inverse of
information gain. Reviews document a case where every optimizer continued scoring a page highly
after it dropped out of the top three, and users report the humanization and optimization passes
fighting each other because they are two separate objectives. `[vendor]` review aggregates

- https://www.capterra.com/p/218703/Surfer/reviews/
- https://www.growthmarketingpro.com/clearscope-vs-frase-vs-marketmuse-vs-surfer-seo/

**Autonomous publishing tools acknowledge their own scope limits** — one describes itself as a
content engine rather than a complete SEO system. `[vendor]`

- https://rankpilot.dev/blog/seobot-review

**The GEO tooling market is overwhelmingly monitoring**, priced $29–$399+/month, with one vendor
raising $96M at a $1B valuation for a dashboard. Few produce actions. `[practitioner]`

- https://www.superbcrew.com/profound-raises-96-million-in-series-c-funding-round/
- https://ayzeo.com/comparisons/geo-platforms-compared

**Documented market pain**: practitioners report paying $300+/month across four or five tools that
do not exchange data, and copying figures between dashboards manually. `[practitioner]`

- https://onelittleweb.com/top-tools/best-ai-seo-tools/

**Caveat on this section.** Search results for tool reviews are heavily occupied by affiliate
content. Where a review site earns commission on the tools it ranks, it is `[vendor]` in effect even
when it presents as independent.

---

## Internal observations

Some rules rest on observations made while building and auditing real sites. Those sites are not
identified here and their data is not published. Such rules are marked in the doctrine as
`[internal observation, unpublished]`.

They are stated in the doctrine as anonymous, reproducible findings — for example, that a site was
observed serving `dateModified` equal to the request time on every fetch, which makes that field
useless for change detection. The lesson is portable and testable on any site; the site that taught
it is not named.

**These carry the lowest evidential weight in the framework.** A single observation on a single site
is a hypothesis. Where such an observation drives a `BLOCK` rule, that is flagged in
`doctrine/OPEN-QUESTIONS.md` as needing external corroboration.
