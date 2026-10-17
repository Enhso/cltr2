# Methods summary: agent-overreach issue study (rtc/research)

Files: PI = pull_agent_issues.py, CI = code_issues.py (line refs). All paths under /home/hatim/applications/cltr2/rtc/research/.
Verification: I re-ran `CI summary` and `CI agree` (default args) in a scratch dir with symlinked inputs. strata.csv, summary_by_quarter.csv,
trend.csv and agreement_disagreements.csv reproduced byte-for-byte. I also ran aggregate-only counts over the big files (no rows printed).
"Checked" below means that. Other figures (e.g. sensitivity rows) are my own recomputations in scratch, not in the project.

## 1. Data source
- Repos: anthropics/claude-code, openai/codex, google-gemini/gemini-cli (PI:39). Months 2025-03..2026-09 (PI:458-459); denominators.csv has all 57 repo-months.
- Snapshot: GitHub search responses cached forever (PI:112-120); cache/ mtime is 2026-10-15 16:47, so it is a one-time snapshot of that day.
- Net: 33 quoted phrases in 4 families (PI:44-86): destructive 10, ignored_instruction 8, safeguard_bypass 8, misreport 7.
  Query per phrase-month: `repo:R is:issue created:YYYY-MM-01..YYYY-MM-DD in:title,body "phrase"` (PI:216,231). Title+body only, no comments, no PRs.
  Paged to GitHub's 1,000-result cap (PI:275). Checked: no phrase-month exceeded the cap (max 361), no `incomplete_results`.
- Match = any phrase hit. matches.jsonl has one row per (repo, month, phrase, issue): 15,517 rows -> 11,728 unique issues (9,395 claude-code / 1,890 codex / 443 gemini).
  Rows keep only title, labels, state, author type, comment count and `body_excerpt` = first 800 chars of body (PI:269).
- Issue families (unique issues, overlapping): safeguard_bypass 5,332; destructive 5,019; ignored_instruction 1,280; misreport 1,232. 972 issues hit 2 families, 71 hit 3, 7 hit 4.
- Denominator (PI:216-226): `total_count` of `repo:R is:issue created:month`, i.e. EVERY issue opened that month (open/closed, duplicates, bot/spam, feature requests; no PRs).
  CI:582-590 sums months to quarters and repos together. It counts issues as they exist at pull time (deleted/transferred issues are absent).
  Quarterly totals: 2025Q1 415 (March only), Q2 3,807, Q3 10,761, Q4 11,958, 2026Q1 32,324, Q2 41,083, Q3 40,644.
- It counts issues filed, NOT agents in use or agent actions. No script measures usage/volume directly.

## 2. Pipeline in order
1. Pull. `PI collect` -> cache/, matches.jsonl, denominators.csv. `PI summarise` -> monthly.csv, phrase_counts.csv. `PI sample` -> coding_sample.csv was superseded (file absent).
2. Queue (CI:183-228). Input matches.jsonl; output queue.jsonl (11,722 lines). Dedupes to repo#number, DROPS author_type Bot (:188; only 6 bots), keeps duplicates.
   Per quarter: sort by key, shuffle with Random(2026) (:213-216), then round-robin across quarters (:218-221). Population = keyword matches, not all issues.
3. Stage 1 (CI:409-426, defaults :1000-1003). Input queue.jsonl; output stage1_codes.jsonl. Model alias `haiku`, batch 40, `claude -p`, no tools, rubric_stage1.md as system prompt.
   Model sees per issue: key, created date, labels, title, first 800 chars of body (whitespace-collapsed) (:409-414). Census of the queue: 11,718 of 11,722 coded;
   4 never coded (attempts=1 each, silently dropped). 296 calls, est. cost $2.05 (CLI-reported), 2026-10-15 17:01-21:24.
4. Deep (CI:454-576). Input queue + stage 1 (+ live `gh api` fetch); output deep_codes.jsonl, deep_cache/. Model alias `sonnet`, batch 5, rubric_deep.md.
   Model sees: title, labels, body whitespace-collapsed then cut to 3,000 chars, and ONLY the first 4 comments cut to 600 chars each, with author association (:464, :497-512).
   Not a census: 4,919 of 11,718 (42%) coded. 1,019 calls, est. $49.5, 2026-10-16 06:54 -> 10-17 04:13.
   Escalation is not "LoC hits only". Stage 1 assigns each issue to a class (:146-149): s1_loc (any code 3/4/5), s1_lowconf (no 3/4/5, self-reported confidence "low"),
   unflagged (everything else). `deep_order` (:515-548) takes validation issues first, then water-fills across (quarter x class) strata with equal weights 1,1,1 (:1016-1020),
   always drawing the stratum with fewest deep codes, in each stratum's random queue order. Intent: any prefix is a random subsample of every stratum.
   Realised coverage (strata.csv): 2025 quarters ~100% in all classes; s1_lowconf 99-100% throughout;
   2026Q1/Q2/Q3 s1_loc 88%/62%/70%; unflagged 25%/18%/14% (about 455 deep codes per stratum).
5. LoC definition (CI:56,142): a DEEP code set containing 3 (ignored instruction/deny rule/CLAUDE.md/stop), 4 (circumvented a safeguard) or 5 (misreported own actions).
   Stage-1 codes are used only to form strata, never as the measurement.

## 3. How each output is produced
| file | producer | definition |
|---|---|---|
| denominators.csv, matches.jsonl, cache/ | PI collect | above |
| monthly.csv | PI summarise (:313-361) | per repo-month, per family and ALL, variants all/excl_dup: n unique issues, per-1k of total issues, Wilson 95% CI (:288-295,353-358). Includes bots; keyword stage only, no LLM. |
| phrase_counts.csv | PI summarise (:363-378) | per phrase-month: GitHub total vs rows retrieved (checked: equal everywhere, 1,031 rows) |
| queue/stage1/deep jsonl, attempts.json, usage_log.csv, deep_cache/ | CI stage1/deep | `latest()` keeps the last record per key (:134-139). attempts.json counts omitted/failed items per stage:key; >=3 excludes the item (:351,391-393). |
| strata.csv | CI summary (:675-694) | per quarter x class: stage1_coded N, deep_coded n, loc_hits, loc_rate = hits/n, Wilson 95% CI (no finite-population correction) |
| summary_by_quarter.csv | CI summary (:729-762) | see formulas below |
| trend.csv | CI summary (:781-822) | log-linear slopes, see below |
| validation_sample.csv | CI validation (:861-901); my_codes/my_safeguards_disabled filled by hand | see section 4 |
| agreement_disagreements.csv | CI agree (:971-988) | rows where hand code SET != deep code set (exact set mismatch, includes non-LoC mismatches) |
Formulas (summary_by_quarter.csv; reproduced):
- keyword_matches = queue count in quarter (non-bot). matches_per_1k = 1000 x keyword_matches / total_issues (3 repos pooled) (:709).
- loc_share_q = SUM_h (N_qh / N_q) x p_qh (:613-638). N_qh = stage-1-coded issues in (quarter, class), p_qh = deep LoC hits / deep-coded n.
  If n < min(20, N) the all-quarter class rate is borrowed (non-strict default). The shipped flags column is empty, so no point estimate borrowed.
- est_loc_reports = loc_share x keyword_matches (:744). loc_per_1k = loc_share x matches_per_1k (:755) = LoC reports per 1,000 ALL issues filed.
- CI: percentile bootstrap, 1,000 resamples, seed 2026: resample stage-1-coded issues within a quarter together with their (class, deep state), recompute share (:703-731).
  loc_per_1k interval = share interval x fixed matches_per_1k (:756-757). Treats keyword matches as a sample from a superpopulation; no FPC; denominators and keyword recall treated as exact.
- trend.csv: OLS slope of log(y) on quarter index 0..6, reported as 100 x (exp(slope)-1) % per quarter (:641-647,784-786). Rows: matches per 1k (no CI), LoC share, LoC per 1k.
  CIs are percentiles of bootstrap slopes (:718-727). No p-values or hypothesis tests anywhere.
Shipped results (LoC share [CI] ; LoC per 1k [CI]): 2025Q1 .231 [0,.462] ; 7.2 | Q2 .240 [.168,.320] ; 7.9 [5.5,10.5] | Q3 .341 [.302,.381] ; 15.7 [13.9,17.6] |
 Q4 .271 [.240,.307] ; 14.5 [12.8,16.4] | 2026Q1 .219 [.199,.240] ; 17.0 [15.5,18.7] | Q2 .225 [.206,.244] ; 19.8 [18.1,21.5] | Q3 .163 [.146,.178] ; 17.3 [15.5,19.0].
 Matches per 1k: 31.3, 32.8, 46.1, 53.4, 77.7, 87.9, 106.5. est_loc_reports: 3, 30, 169, 173, 549, 813, 704.

## 4. Validation
- Draw (CI:861-901): from queue issues with a stage-1 code, equal allocation per quarter (per = 60 // 7 = 8), `rng.sample` with Random(2027). n=56, not 60. Not proportional to quarter size; not stratified by class or repo.
  Composition: 48 claude-code, 6 codex, 2 gemini; stage-1 class 39 unflagged / 15 s1_loc / 2 s1_lowconf. Sheet shows key, url, quarter, title only (no LLM output).
- Coder: a human (Hatim, single coder, 56/56 filled, notes empty), same 0-5 codebook, working from the GitHub URL, i.e. the full live thread. Hand LoC positives: 14/56.
  validation_sample.csv last modified 2026-10-16 19:00. 30 of the 56 had already been deep-coded before the sheet was used for ordering (deep `reason` != "validation"). Blindness to LLM output cannot be verified from the files.
- Agreement (CI:904-912,953-960): binary LoC (3/4/5) vs not, Cohen's kappa, percentile bootstrap CI (2,000 resamples), unweighted.
  Hand vs deep (Sonnet): both 10, hand-only 4, LLM-only 4, neither 38; agreement 86%, kappa 0.62 [0.35, 0.83]; exact code-set agreement 70%.
  Hand vs stage 1 (Haiku): 10 / 4 / 5 / 37; agreement 84%, kappa 0.58 [0.31, 0.82]; exact set 73%. Disagreements are symmetric (4 and 4), no evidence of directional bias at this n.
- Not computed by any script: the hand fields `my_safeguards_disabled`, and the LLM fields `safeguards_disabled`, `irreversible`, `quote`, `rationale` are never aggregated or checked.

## 5. Caveats, threats to validity, bugs
Measurement / construct
1. "LoC" here = issue REPORTS in which a reporter alleges disobedience/circumvention/misreporting, as judged by Sonnet. Of 1,760 deep LoC calls (unweighted, whole deep sample), 1,378 include code 3,
   564 include code 5, only 112 include code 4. 735 (42%) are confidence "low" (reporter claim, no log); only 145 (8%) "high". Code 4 alone is ~1.3 per 1k issues in 2026Q3 (my recompute).
   Dropping low-confidence LoC calls cuts the share by 33-60% (my recompute, 2025Q1..2026Q3): .231,.240,.341,.271,.219,.225,.163 -> .154,.096,.183,.163,.125,.129,.097.
2. Rates are per 1,000 issues filed, not per agent-use. The study cannot separate "more agents" from "higher rate per use": it sees reports as a share of the issue stream.
   Issue volume is a poor usage proxy: claude-code issues fall from 13,075 (2026-04) to 7,387 (2026-09); gemini-cli collapses from 1,704 (2026-03) to 123 (2026-07).
   Reporting propensity, templates, triage bots, awareness of the topic and product changes (permission modes, CLAUDE.md) all move numerator and denominator.
3. Composition: pooled rate mixes repos with very different rates. My per-repo recompute (scratch; codex/gemini strata thin and partly borrowed): LoC per 1k, claude-code
   7.2,11.7,25.7,18.9,21.0,25.3,23.3 (flat since 2025Q3); codex 1.7..11.6, 2026Q3 7.1; gemini 4.3..11.8. Codex's share of denominators rises from 12% (2025Q3) to 36% (2026Q3). No script reports per-repo results.
4. Keyword net: recall unknown. Only precision is estimated (from deep coding). Issues describing the same behaviour in other words are never seen, and phrase popularity can drift.
   GitHub search is tokenised, not substring; I did not test whether "rm -rf" etc. match literally. Matches per 1k "(exact count)" in trend.csv is exact only as a search count.
5. Duplicates are kept. 2,459/11,728 matched issues (21%) carry a duplicate label or state_reason; the queue does not carry state_reason (CI:192-205). Duplicate-label share by quarter is
   0/7/15/24/30/27/4%: labels lag, so dedupe cannot be applied evenly across time (my recompute: excluding labelled dups turns the 2026Q2->Q3 LoC-per-1k change from -13% to +21%).
   Reports are not incidents: ~30% of LoC calls in 2025Q4-2026Q2 carry a duplicate label.
6. Numerator excludes bot authors (CI:188; 6 issues); the denominator includes all authors (PI:216). Bot/spam share of the denominator is unknown.
LLM coding
7. Coder is one pass of an LLM: no repeat runs, no test-retest, temperature not controlled. Model recorded only as the alias "haiku"/"sonnet" (CI:303,388); only `usage` and `total_cost_usd` are kept from the CLI JSON (CI:299-311),
   so the resolved model ID is not stored. Your global notes say the haiku alias resolved to Haiku 4.5 unless ANTHROPIC_DEFAULT_HAIKU_MODEL was set: confirm which served. Prompt tokens
   (median 16k stage 1, 7.8k deep) suggest no large CLAUDE.md was loaded. Whether `--safe-mode` (CI:251) was accepted or `--no-safe-mode` used is not recorded.
8. The rubric's first line tells the coder the study is about "whether agents take unsanctioned actions" (priming). Labels and created date are shown to the coder.
9. Deep input is truncated: body 3,000 chars, first 4 comments x 600 chars (CI:464,499,510). Later maintainer replies and logs at the end of long bodies are invisible; the human saw the full thread.
   Deep text was fetched at coding time (live body/labels), stage-1 excerpt at pull time.
10. clean_items (CI:321-344) accepts incoherent sets and unverified quotes. 43 of 1,760 LoC calls also carry code 0 or 1. Quotes are never checked as verbatim.
11. Ground truth for rates is Sonnet, with no misclassification correction. Validation is n=56 with 14 hand positives, kappa CI [0.35, 0.83], equal-per-quarter (48/56 claude-code), single coder (Hatim), not independent of the study design.
Sampling / estimation
12. Two deep-sampler versions were used. deep_codes `reason` has "flagged" (1,529; s1_loc + s1_lowconf pooled) and "audit" (170; unflagged), run 10-16 06:54-12:52, which the current deep_order
    (CI:515-548) cannot emit. CI mtime is 10-16 12:54, after phase 1. The folder is not under version control, so the first sampler's rule cannot be inspected. The stratified estimator
    re-derives strata from stage 1 (CI:658-662), so it stays valid only if phase 1 draws were random within stratum. Checked: deep vs not-deep within 2025Q4-2026Q3 strata are
    similar on repo mix, families/phrases per issue, stage-1 confidence and dup-label share. Consistent with random, not proof.
    Also: PI mtime (10-16 18:10) is after the data it produced (10-15), so PI may differ from the pull code. Rubric files equal the script constants (checked).
13. Missing deep codes are not reported: `deep_failed` counts only items with >=3 attempts (CI:663), all 0. 33 attempted-but-uncoded issues (attempts 1-2) sit in 8 strata
    (e.g. 2026Q3 unflagged 9, lowconf 6). 4 stage-1 failures are not reported at all. Small, but fetch failures (deleted issues) are not random.
14. Trend CIs are unreliable as shipped. 2025Q1 is one partial month (13 issues, no codex/gemini issues); the `max(x, 1e-4)` floor (CI:721,725) plus bootstrap draws with zero LoC makes
    the upper tail absurd: LoC share -5.6%/qtr [-12.5, +112.5]; LoC per 1k +17.6%/qtr [9.0, 283.0]. Quarters are weighted equally in OLS regardless of size. Rerun (scratch):
    --from-quarter 2025Q2: share -9.3% [-13.0,-4.3], LoC per 1k +14.7% [9.9,20.9]; from 2025Q3: -15.3% [-18.0,-12.4], +5.2% [1.9,8.9]. Matches per 1k: +24.6/26.4/24.3% (no CI).
    Report a sensitivity range, not one slope.
15. strata.csv Wilson CIs and the quarter bootstrap ignore finite-population effects; fully coded 2025 strata show sampling CIs though there is no sampling. In bootstrap replicates thin strata
    can be pooled (CI:634), narrowing intervals. CIs exclude coder error, search recall, and the denominator.
16. Unflagged stratum matters: it has 3-7% LoC (screening false negatives) and supplies ~14% of the 2026Q3 share (75% of issues x 3.1%), but is only 14-25% deep-coded in 2026.
17. Minor: attempts.json is read once per run and overwritten (CI:350,393; concurrent runs would clobber); stage-1 file has 1 duplicate key (11,719 rows/11,718 unique);
    rubric files are written only if absent (CI:127-131), so editing the script text later changes nothing.

Reading for the essay (mine): LoC reports/qtr rose ~25x (30 -> 700-800) while all issues rose ~10x; LoC per 1k doubled 2025Q2->Q3 and has been roughly flat (14.5-19.8) since; LoC share of matches fell.
That fits "mostly volume of issues, plus a one-off step up", but the per-repo split, low-confidence share, duplicates and sampler change all need to be stated.
