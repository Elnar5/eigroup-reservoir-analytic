# Interview Prep — Short Answers

**Reservoir Analytics Project**
**Author:** Elnar Babayev  ·  **eiGroup Associate Data Scientist Assessment**

Pocket-sized, evidence-based answers for an in-person interview.
Every answer is grounded in the deliverables in `outputs/reports/`.

---

## Table of contents

1. [Part A — Data integration & quality](#part-a--data-integration--quality)
2. [Part B — Per-(well, zone) metrics](#part-b--per-well-zone-metrics)
3. [Part C — Cutoff sensitivity & field views](#part-c--cutoff-sensitivity--field-views)
4. [Part D — Sub-zone definition](#part-d--sub-zone-definition)

---

## Part A — Data integration & quality

### "Walk me through Part A."

> "Part A is data loading, joining, and quality assessment. I loaded
> seven well CSVs plus a zones lookup, used `merge_asof` to assign each
> depth sample to its containing zone, computed per-well depth steps,
> and ran range and missing-value checks. The output is a single
> parquet master table of 18,167 samples. The most important finding
> was a likely tool-saturation signature — 19.34% of all permeability
> values are exactly 15,000 mD, the upper end of the documented valid
> range. Statistical evidence strongly favours saturation over a
> physical maximum, but without core data the alternative can't be
> fully ruled out. That single observation shapes the interpretation
> of every downstream metric."

### "How did you handle the zones-to-samples join?"

> "Pandas `merge_asof` with `direction='backward'`. For each sample, it
> finds the zone whose `top_depth` is the largest value still less than
> or equal to the sample's depth. After the merge, I validate that each
> sample's depth falls within its assigned zone's range. The join is
> done per-well using the `by='well_id'` parameter, so wells don't
> contaminate each other."

### "How did you discover the saturation?"

> "Looking at the perm distribution. The value 15,000 mD appears 3,514
> times across 18,167 samples — to machine precision, exactly 15,000.
> A genuine measurement near that value would produce a continuous
> spread. The discrete spike at exactly the upper end of the valid
> range is the textbook signature of a tool ceiling. Once I saw it,
> I added a `perm_saturated` boolean column and made sure every
> downstream report annotates it."

### "How do you know it's a tool ceiling and not a physical maximum?"

> "I don't know with certainty — and that's an important caveat.
> Three pieces of statistical evidence point to saturation rather than
> a physical maximum. First, the data dictionary specifies the perm is
> 'approximately log-normally distributed', and a log-normal
> distribution is continuous — it doesn't produce point masses at any
> single value. Second, the spike sits exactly at 15,000 mD, the upper
> end of the documented valid range — physical maxima would scatter
> near but not precisely at a round, instrument-friendly number.
> Third, 99.85% of the saturated samples concentrate in Zone B alone,
> while Zones A and D show zero saturation. A physical maximum would
> not select for a single zone, but a tool that saturates above
> 15,000 mD would saturate exactly in the high-permeability zones.
> Saturation is the more probable interpretation. To be certain I'd
> need core data."

### "Why didn't you drop the saturated samples?"

> "Two reasons. First, they're real samples that contribute real flow
> capacity — dropping them would bias kh estimates downward, not
> upward. Second, the saturation pattern itself is informative — Zone
> B has 99.85% saturation, Zone D has 0% — and that information would
> be lost if I dropped the samples. Instead I kept them, flagged them,
> and surfaced the count in every downstream chart."

### "What's the well 5 anomaly?"

> "Well 5 is sampled at 0.5 m depth intervals; every other well is at
> 0.2 m. Six wells have around 2,800 samples each, well 5 has about
> 1,000. If I had computed any metric as a sample count, well 5 would
> systematically appear to have less reservoir than it actually does.
> The fix is depth-weighting — every metric integrates over `dz`, not
> over sample count. So well 5's 0.5 m samples each contribute 2.5
> times the thickness of a 0.2 m sample, and volumes come out
> sample-cadence invariant."

### "What about well 3's missing phit values?"

> "Well 3 has 78 NaN porosity values clustered in specific depth
> intervals — consistent with a tool malfunction at certain depths
> rather than random sampling errors. I kept the NaN rows in the
> master table, flagged in the QC report. Any downstream metric
> requiring phit auto-excludes them via pandas' default NaN handling.
> 78 samples out of 18,167 is 0.43% — negligible field-wide, small
> impact on well-3-specific metrics, both disclosed."

### "What would you do differently with more time?"

> "Three things. First, **investigate the saturation by well** — well 7
> is 30% saturated vs other wells at 14-22%. That could be a
> well-specific tool issue rather than a field-wide ceiling. Second,
> **request calibration data** — core or production data — that would
> let me check whether sub-15,000 mD values are also affected by tool
> compression near the ceiling. Third, **investigate well 5's depth
> sampling** — was the 0.5 m step deliberate (e.g., a different tool
> run) or an upload error? That changes how confident I can be in the
> depth-weighting fix."

### "If I asked you to summarize Part A in one sentence?"

> "Eighteen thousand one hundred sixty-seven samples across seven
> wells and five zones, with one critical caveat: nearly twenty
> percent of all permeability values sit at exactly 15,000 mD, which
> three pieces of statistical evidence identify as most likely a tool
> ceiling — making every downstream flow-capacity number a probable
> lower bound rather than a definitive estimate."

---

## Part B — Per-(well, zone) metrics

### "Walk me through Part B."

> "Part B computes the five required metrics per (well, zone) — gross
> thickness, net thickness, average porosity, average permeability,
> and kh — plus seven bonus diagnostics including NTG, kh-weighted
> mean perm, Lorenz coefficient, and saturation counts. The output is
> a 35-row × 12-column tidy DataFrame, plus two rollup tables by zone
> and by well. The findings split into five clear zone signatures and
> one critical caveat: Zone B's headline kh of 10.7M is most likely a
> lower bound, because 99.85% of its net samples sit at the 15,000 mD
> upper limit."

### "Why did you add bonus columns?"

> "Three of them earn their place by answering specific questions the
> required metrics leave open. **NTG** turns 'net = 466 m' into 'this
> is 63% reservoir-quality rock', which is more interpretable.
> **kh-weighted average perm** is the engineering-correct mean when
> dz varies between wells. **Lorenz coefficient** signals internal
> heterogeneity — Zone C's 0.65 is what motivated the Part D
> clustering. The other four are sanity counts that make the
> reviewer's job easier."

### "How do you handle NaN porosity?"

> "Exclude conservatively, count visibly. Samples with NaN phit are
> excluded from the net mask because missing data is not reservoir.
> But the count of excluded samples appears in `n_phit_nan`, so the
> reviewer can see exactly how much thickness was potentially lost.
> Well 3 has 78 NaN values across all five zones — about 4% of well
> 3's samples — so well 3's net is technically a lower bound."

### "Why do you keep saturated samples in kh?"

> "Two reasons. First, dropping them would systematically
> under-estimate flow capacity — they're real samples at the upper end
> of the documented measurement range. Second, by keeping them and
> counting them in `n_perm_saturated_in_net`, the **potential**
> lower-bound nature of kh is visible. If the 15,000 mD spike is a
> tool ceiling — which the statistical evidence favours — those kh
> values are conservative lower bounds. If 15,000 is a physical
> maximum, they're exact. Either way, the saturated count next to
> each kh lets the reviewer decide. If I'd dropped the samples,
> reviewers would have had no way to tell any potential censoring
> had occurred."

### "Why is Zone B's Lorenz coefficient zero?"

> "Mathematical inevitability — under the saturation interpretation.
> The Lorenz coefficient measures heterogeneity. If 99.85% of Zone B's
> samples have an identical perm value, by construction they all
> contribute equally to flow, and the Lorenz curve collapses to the
> 45° diagonal — coefficient ≈ 0. **If 15,000 mD is a tool ceiling
> (which the evidence favours), this is censoring, not homogeneity**:
> two sub-intervals with true perm of 20,000 mD and 80,000 mD would
> both register as 15,000 mD, and any heterogeneity metric computed
> from those measurements would be blind to the difference. Under
> the alternative reading — 15,000 mD as a physical max — the zero
> Lorenz would be a real homogeneity finding."

### "Which zone deserves the most attention?"

> "Two answers depending on what you're optimizing. **For maximum
> visible kh**, Zone B — but its number is most likely a lower bound
> by an unknown multiple, if the saturation interpretation holds. **For
> maximum defensible kh under either interpretation**, Zone E — its
> 1.2M mD·m is a real measurement, with only 1.4% saturation. For a
> development decision today, I'd target Zone E as the primary
> high-perm zone and treat Zone B's true magnitude as the largest
> single uncertainty in the deliverable — one that core or production
> data would resolve."

### "Why is Zone D non-reservoir?"

> "Three orders of magnitude. Total kh is 42 mD·m, compared to 267,000
> for Zone A and over a million for Zone E. Average perm is sub-1 mD.
> NTG is 10% at default cutoffs and never exceeds 29% even at the
> loosest cutoff Part C.1 tested. Zero saturated samples means this
> is a real measurement, not a tool artefact. The binding constraint
> is porosity, not shaliness — most of Zone D fails the phit ≥ 0.08
> threshold, regardless of how vsh is set. Zone D is tight rock,
> field-wide, robustly unproductive."

### "What's the well 7 paradox?"

> "Well 7 has the highest kh in the field (2.59M mD·m) AND the highest
> saturated sample count (798). Under the saturation interpretation,
> the two go together — the tool ceiling pushes visible perm up to
> the limit, inflating apparent kh while making the true value
> unknowable. Well 7's true kh would then be higher than its reported
> number by an unknown multiple. So when ranking wells, well 7 leads,
> but the gap to the rest of the field could be even larger than the
> table suggests. The recommendation is to report saturation fraction
> alongside kh in any cross-well comparison — otherwise rankings are
> partly an instrument artefact."

### "If you had one more day, what would you add?"

> "Three things. First, **a saturation-corrected kh estimate** for
> Zone B — using order-of-magnitude bounds from typical
> sandstone-perm distributions, I could give an upper bound to pair
> with the current lower bound. Second, **a per-zone uncertainty
> column** that combines saturation fraction and NaN fraction into a
> single 'how much do I trust this number' index. Third, **a
> sample-count vs depth-weighted comparison** — show that the
> depth-weighting is doing its job by demonstrating well 5's metrics
> match what they would have been at 0.2 m sampling."

### "Summarize Part B in one sentence."

> "Thirty-five (well, zone) rows with five required metrics and seven
> bonus diagnostics, telling five distinct zone stories: Zone A clean
> top reservoir, Zone B saturation-capped flow champion with a
> probable lower-bound kh of 10.7M, Zone C heterogeneous secondary
> that motivates Part D's clustering, Zone D non-reservoir tight rock
> at any cutoff, and Zone E the most defensible high-perm zone at
> 2,045 mD."

---

## Part C — Cutoff sensitivity & field views

### "Walk me through Part C."

> "Part C is about cutoff sensitivity and field-level views. C.1 sweeps
> the vsh cutoff across nine values from 0.3 to 0.7 to see which findings
> are robust. C.2 builds six complementary charts that answer different
> field-level questions."

### "Why sweep instead of picking a cutoff?"

> "The default 0.5 is a literature value, not calibrated to this field.
> Core and production data — which would normally inform the calibration
> — aren't available. So the question shifts: how sensitive are our
> deliverables to the cutoff? The sweep bounds the conclusions instead
> of picking one."

### "What's the most important finding from Part C.1?"

> "Zone D is robust failure. NTG never exceeds 29% even at the loosest
> cutoff. Average perm stays sub-mD. Zone D is tight rock — a physical
> property of the field, not a methodology artefact. The sweep rules out
> a cutoff-driven explanation."

### "How would you choose a cutoff?"

> "First preference: calibrate against core or production data. Not
> available here. Second: report ranges, not point estimates. Third: if
> forced to one number, 0.5 is defensible — but always disclose what
> would change at 0.4 and 0.6."

### "What tradeoffs do you see?"

> "Strict cutoffs give higher-quality reservoir but smaller volume.
> Permissive cutoffs give larger volume but include rock that may not
> produce. Without core calibration, all three (strict/default/permissive)
> are defensible — the honest move is to report all of them and let the
> reviewer see."

### "Why six charts when the case asks for two-three?"

> "The case lists five distinct field-level questions to consider. Each
> chart answers a different question well. The heatmap shows where the
> flow is, the stacked bar shows how wells rank, the crossplot is a sanity
> check, the sensitivity curve is the C.1 visualization, the Lorenz curve
> shows internal heterogeneity, and the box plot directly answers
> 'consistently strong or weak across the field'. Forcing one chart to
> answer all five would make none of them sharp."

### "Which chart is the most important?"

> "Hardest one to lose: the kh heatmap. It carries the most information
> per pixel — every well-zone intersection with both kh and saturation
> count. Easiest to lose: the crossplot, which is a sanity check rather
> than a direct answer to a case question."

### "Is the data internally consistent?"

> "Yes. Chart 3 confirms the Carman-Kozeny trend — porosity and
> permeability correlate as expected. And the saturated samples form a
> clean horizontal band at log_perm = 4.18, exactly where the 15,000 mD
> tool ceiling would be. Both signals say the dataset is internally
> consistent, with the censoring effect being the only major caveat."

### "What's the saturation problem?"

> "99.85% of Zone B's net samples report exactly 15,000 mD — the upper
> end of the documented valid range. Three pieces of statistical
> evidence in Part A point to this being a tool ceiling rather than a
> physical maximum: the data dictionary specifies log-normal
> distribution (which doesn't produce point masses), the spike sits
> exactly at the round upper limit, and it concentrates in a single
> zone. Under that reading, the true permeability is higher than
> 15,000 mD by an unknown multiple, and every Zone B kh number is a
> conservative lower bound. Without core data we can't be 100% sure —
> a physical maximum remains a less likely alternative. Either way, we
> surface the saturated count on three charts so the reviewer can
> read the results under either interpretation."

### "Why does Lorenz fail for Zone B?"

> "Because 99.85% of Zone B's net samples report exactly the same perm
> (15,000 mD), they all contribute equally to flow by construction.
> The Lorenz curve collapses to the diagonal, giving a coefficient
> near zero. Under the saturation interpretation, this isn't a
> homogeneity finding — it's an artefact of the tool ceiling
> compressing the perm range to a single value. Under the alternative
> interpretation (15,000 mD as a physical max), the zero Lorenz would
> be a real homogeneity result. The statistical evidence makes
> saturation more likely, but both readings are documented."

### "What spatial trends did you find?"

> "The case mentions spatial trends, but the dataset doesn't include
> geographic coordinates for the wells. Without coordinates, we can show
> well-to-well variation (Chart 1, Chart 9) but not directional or
> geographic trends. We'd need surveyed well locations to address that
> question properly. This is a data limitation, not a methodology one."

---

## Part D — Sub-zone definition

### "Walk me through Part D."

> "Part D is sub-zone definition — given a zone, propose a data-driven
> way to subdivide it. I picked Zone C because it's the thickest
> non-saturated zone and its Lorenz coefficient of 0.65 already
> signalled internal heterogeneity. I used K-means with six features —
> vsh, phit, log(perm), sw, effective porosity, hc porosity — fit
> pooled on all 7 wells' Zone C samples. Three sub-zones emerged with
> monotonically improving quality. Leave-one-well-out ARI averaged
> 0.991, meaning the structure is essentially invariant to which well
> is held out."

### "Why Zone C and not Zone B?"

> "Zone B's permeability is most likely saturated — 99.85% of its net
> samples report exactly 15,000 mD, and the statistical evidence in
> Part A points to this being a tool ceiling rather than a physical
> maximum. Clustering on a feature that's been compressed to a single
> value can't find real heterogeneity in that feature, so Zone C was
> the better primary choice. I ran Zone B anyway as a negative
> control. The result fails in a specific, predictable way: two of
> the three sub-zones have log_perm centroids of 4.175938 vs
> 4.176091 — indistinguishable. **That failure is itself a finding**:
> under the saturation interpretation it confirms the Lorenz story
> from Part C; under the alternative interpretation it means Zone B
> is genuinely homogeneous in perm."

### "Why k=3 instead of k=2?"

> "K=2 wins by silhouette (0.394 vs 0.276), but K=3 is the geological
> answer. K=3 gives three coherent quality tiers — poor, moderate, best
> — where every feature orders monotonically: vsh decreases, phit
> increases, perm increases, sw decreases. The case asks for 2-3
> sub-zones; I picked 3 because it maps to three operational decisions:
> avoid sub-zone 0, characterize sub-zone 1, target sub-zone 2. I
> documented the trade-off explicitly."

### "What does same sub-zone across wells mean operationally?"

> "Two samples in different wells belong to the same sub-zone if they
> are assigned to the same cluster by the same fitted model. There is
> exactly one set of centroids in standardized 6-feature space, and
> every sample in the field is scored against those same centroids.
> Sub-zone 0 in well 1 and sub-zone 0 in well 4 have the same
> characteristic vsh, phit, perm, sw — they're the same kind of rock
> at different depths."

### "How did you validate it?"

> "Four checks: silhouette 0.276 on k=3, leave-one-well-out ARI 0.991,
> agreement between K-means and GMM, and physical interpretability of
> the centroids — every feature orders monotonically across the three
> sub-zones. The LOWO result is the strongest single piece of evidence
> — withholding any well doesn't change the clustering."

### "What would better validation require?"

> "Three external sources. **Core descriptions and core permeability**
> would let us check whether sub-zone boundaries correspond to
> observable lithology and measured perm tiers — gold standard.
> **Production logs** would test whether the predicted best tier
> actually produces more per metre — operational validation. **Pressure
> transient data** would calibrate magnitude, not just ranking. Cheaper
> proxies I could add without new data: bootstrap stability, feature
> ablation, stratigraphic continuity."

### "What failure modes worry you?"

> "Top of the list: saturation collapsing cluster separation on a
> saturated feature. Zone B is the example — clustering 'succeeds'
> statistically but two centroids are indistinguishable in perm.
> Second: cluster identity drift across wells, which the LOWO test
> guards against. Third: spurious k — picking k=3 when k=2 wins by
> silhouette is a judgment call I documented. Then features chosen
> wrong, depth ordering ignored, and sample imbalance. Each has a
> specific mitigation."

### "What's the drilling implication?"

> "Sub-zone 2 — the best tier — holds 48% of Zone C's kh in only 29%
> of its thickness. It's present in all seven wells with thicknesses
> between 34 and 55 metres. A horizontal well or stimulation campaign
> targeting sub-zone 2 captures roughly twice the flow per metre
> drilled compared to a non-discriminating Zone C target. Sub-zoning
> changes the per-foot economics of any Zone C development decision."

### "If the company gave you another week, what would you do?"

> "Three things. First, depth-aware post-processing — smooth the
> salt-and-pepper assignments into contiguous depth intervals.
> Second, feature ablation — refit with each feature removed to
> document which features the clusters depend on. Third, request core
> data for two or three wells and check whether sub-zone boundaries
> align with described lithology changes. That gets us from internal
> consistency to external validation."
