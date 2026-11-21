# Phase 3 independent editorial audit

**EDITORIAL AUDIT COMPLETE — ARTIFACT RELEASE DECISION READY**

The primary and control findings reconcile with the frozen records and analysis. The audit clarified descriptions of the estimand, scheduler and measurement units. No numerical estimate, interval, result table, scientific source or figure needed correction. Public artifact release requires a separate owner decision.

## Scope and identities

Reviewed the full manuscript, references, figure index, and 3E-6 readiness report against the frozen analysis plan, 3E-5 report, exact seed pairs, primary cell and grid summaries, diagnostic and control tables, shared resamples, six SVGs, and the implementation and validators. The local branch, cached tracking ref and live origin branch all matched `df794b67e72740bffb6272248b9d609c8decfaea` on `phase-3-memory-aware-scheduling`. The Git index was empty and tracked files matched HEAD. Untracked evidence made the baseline working tree non-clean. [Analysis plan](../PHASE3_ANALYSIS_PLAN.md) · [3E-5 report](../PHASE3_3E5_PRIMARY_STATISTICAL_RESULTS.md) · [3E-6 readiness review](SUBMISSION_READINESS.md)

| Verified input | SHA-256 |
|---|---|
| Primary manifest file | `17983e334c0980cbaabafa9da4fe2e9935977848475043de92db4906105a8b48` |
| Control manifest file | `6ca36528c01b1af6c6d95814d850ce68a2b034e5d4de3976b97c9e5049ee99fe` |
| Frozen primary config | `3753af5cb496b4ba395a8f846b4871c0060407de75828e00d445206bad46d8fa` |
| Frozen analysis plan | `eff60269f9fa72efa552be796f432cce46ee231def9b3676999d2d565f860c93` |
| Analysis implementation | `708af9d99730a66cef6955099ee3e4e37243be75e4245172b968421e322928a9` |
| Shared seed-index CSV | `b99485a155a35e9f47a55916fe50a7bc752ca72d68e1d77386cdafa4d5f2f7de` |

## Evidence-to-claim reconciliation

| Manuscript claim | Independent audit result | Authority |
|---|---|---|
| Sections 5–6 and Appendix B. Frozen grid, workload distributions, pairing and experimental unit | Reconciled 480 seeded workloads, 19,200 conditions, and 2,160 unique contrast keys. Every cell has 20 pairs and no undefined relative difference. Raw record validation checked source pins, workload hashes, order and identities. The 200 request latencies define within-condition means and nearest-rank p95. Resampling units are seeds. | [Primary config](../phase3/configs/primary.json) · [Workload generator](../phase3_workloads.py) · [Batch validator](../phase3_batch.py) |
| Sections 6–7 and Tables 2 and A2. Grid effects and pointwise intervals | Independently formed exact differences and relative values from the individual saved pair operands. Reconstructed 10,000 index vectors with the stated RNG, then directly averaged the indexed seed values and interpolated sorted endpoints. Reconciled both timing scales for all 2,160 cells and all nine grid summaries at the CSV's reported precision. In the grid intervals each selected seed contributes its own equal-weight mean over 240 cells. Each relative term uses its own fixed denominator. | [Exact pairs](../phase3/analysis/3e5/seed_pairs.csv) · [Grid CSV](../phase3/analysis/3e5/designed_grid_summary.csv) · [Cell CSV](../phase3/analysis/3e5/primary_contrasts.csv) |
| Section 7 and Figure 1. Direction, exact ties and examples | Recounted all 43,200 signed tick differences as wins, ties or losses. Every win is an exact negative difference and each loss is positive. All 8,640 differences at 2,048 slots were zero. The favorable and adverse 8,192-slot examples, their four relative intervals and signs agreed with the saved cells. At the minimum budget, fixed reservation or the sum of the oldest paged allocation and its protection consume the full budget, allowing one active request at a time. | [Simulator](../phase3_simulator.py) · [Cell CSV](../phase3/analysis/3e5/primary_contrasts.csv) |
| Sections 4 and 8 and Table A1. Scheduler, utilization and counts | Source confirms FIFO without bypass, instant prefill, oldest protection, per-tick successful-generation cap, physical-first failure classification and memory sampling before completion release. Recomputed reported condition-level means and marginal effects. Unused allocated slot-ticks exclude unallocated headroom. Physical and protection admission blocks are tick counts. Growth stalls and deferrals are active request-ticks. Progressing requests share information with makespan because generated tokens agree within a pair. Diagnostic associations have no controlled ablation. | [Simulator](../phase3_simulator.py) · [Diagnostics](../phase3/analysis/3e5/diagnostics.csv) · [Progressing requests](../phase3/analysis/3e5/secondary_progressing.csv) |
| Section 9 and Table 3. Exploratory control | Verified all 80 rows, all three zero-disagreement fields and all four exact pooled unused shares. The comparison uses one prospectively specified canonical workload under unlimited compute and ample memory, outside primary inference. The historical 640 count lacks an executable specification. | [Prospective design](../phase3/research_batch/3e4b/ample_memory_control/specification.json) · [Control checks](../phase3/analysis/3e5/exploratory_control_checks.csv) · [Memory totals](../phase3/analysis/3e5/exploratory_control_memory.csv) |
| Sections 2 and 14. Related work and scope | SOSP proceedings and the author manuscript confirm the PagedAttention authors, venue, year, DOI and bibliographic identity. Indexed ACM metadata confirms pages 611–626. USENIX confirms Orca authors, venue, year and pages 521–538. The related-work descriptions accurately distinguish block-addressed attention, cache sharing and serving measurements in vLLM, and iteration-level scheduling and selective batching in Orca. The manuscript's measurements concern the CPU simulation. | [ACM proceedings](https://doi.org/10.1145/3600006.3613165) · [SOSP program](https://sigops.org/s/conferences/sosp/2023/toc.html) · [Author manuscript](https://arxiv.org/abs/2309.06180) · [USENIX proceedings](https://www.usenix.org/conference/osdi22/presentation/yu) |
| Figures and cross-references | Parsed all six embedded SVGs, checked caption labels, count populations, units, averaging or pooling, and relative paths. The three outcome heatmaps each retain their own scale. Verified the manuscript tables and appendix links against their sources. | [Figure and table index](FIGURE_TABLE_INDEX.md) |
| Sections 10–13. Scope and limitations | Findings apply to the chosen workload and scheduling model. The clock discrepancy remains reported separately from simulated ticks without a causal explanation. The artifact statement now identifies the additional files required beyond scientific HEAD. | [Primary execution report](../PHASE3_3E3_REAL_PRIMARY_REPORT.md) · [Release plan](ARTIFACT_RELEASE_PLAN.md) |

## Corrections

### Scientific wording and reproducibility

| Location | Before | After | Evidence |
|---|---|---|---|
| Introduction | “two generation caps” | “two compute settings” | The unlimited setting has no finite cap. [Primary config](../phase3/configs/primary.json) |
| Section 4, prefill | “without consuming a generation opportunity” | “takes no simulated time, and consumes no generation opportunity” | Prefill and admission occur at the same tick. [Simulator](../phase3_simulator.py) |
| Section 4, G8 | “visits after eight successful generations count as compute deferrals” | “the cap is eight successful token generations per tick. Later eligible visits in that tick count as compute deferrals before any memory eligibility check.” | Cap is reset each tick and checked before growth. [Simulator](../phase3_simulator.py) |
| Section 6, signs | “Exact absolute differences determine improvements, ties, and regressions.” | “The sign of the exact tick difference determines a win (negative), tie (zero), or loss (positive).” | Exact pair subtraction and tally. [Analysis implementation](../phase3_primary_analysis.py) |
| Section 6, grid | “Each designed-grid summary weights all 240 cells for the stated outcome and allocator equally. The relative estimand averages paired percentages.” | “the designed-grid statistic averages the 240 cell differences within each seed, then averages those 20 seed means.” Each percentage uses its matched fixed condition as denominator. | The script constructs one vector of 20 grid averages per outcome and allocator. [Analysis implementation](../phase3_primary_analysis.py) |
| Section 6, intervals | “Each sampled seed carries its complete matched grid” | Retained that statement and added “Each designed-grid bootstrap replicate averages the 20 selected seed means, including repeated selections.” | Resampling uses a common matrix over seed columns. [Implementation conventions](../phase3/analysis/3e5/IMPLEMENTATION_SPEC.md) |
| Section 7, evidence location | “The complete cell table describes all 43,200 paired seed–outcome differences with intervals and distributions by cell.” | “The complete cell table reports intervals and distributions for the 2,160 cells.” The seed-pair table holds the 43,200 individual differences. | [Cell CSV](../phase3/analysis/3e5/primary_contrasts.csv) · [Pair CSV](../phase3/analysis/3e5/seed_pairs.csv) |
| Section 8, concurrency | “peak active concurrency averaged 5.71 requests with fixed and ranged from 43.02 to 45.20 for paged” | “The condition-level peak active counts averaged 5.71 requests for fixed and ranged from 43.02 to 45.20 across paged allocators.” Each condition contributes its maximum observed count with equal weight. | Peak snapshots and cell diagnostic means. [Simulator](../phase3_simulator.py) · [Diagnostics](../phase3/analysis/3e5/diagnostics.csv) |
| Section 8, memory | “Paged unused allocation measures slack within allocated blocks.” | “Paged unused allocation measures internal block-rounding slack.” The separate definitions of fixed reservation slack and unallocated headroom remain explicit. | Fixed maximum and rounded resident length. [Simulator](../phase3_simulator.py) |
| Section 8, admission | “Admission blocking counts a failed queue-head attempt once per tick.” | Added “A physical failure occurs when adding the candidate allocation would exceed capacity before accounting for headroom. A protection failure occurs when the total allocation fits but adding protected headroom would exceed capacity.” | Failure checks physical capacity before protected headroom. [Simulator](../phase3_simulator.py) |
| Section 12, availability | “The paths below describe repository-local availability.” | Added “At the scientific HEAD, the research-batch runner, its protocol, saved condition records, and analysis pipeline are outside the tracked tree.” Linked the release plan. | Git tree, manifest pins and release inventory. |
| Appendix B, streams | “independent length, split, and arrival streams” | “separate pseudorandom length, split, and arrival streams” | Seed derivation creates distinct generator streams. The bootstrap keeps all reused workload streams together by seed. [Generator](../phase3_workloads.py) · [Analysis plan](../PHASE3_ANALYSIS_PLAN.md) |

No standalone cosmetic edits were needed. The 3E-6 readiness review records the earlier draft's 4,596-word count. The revised manuscript has 4,738 whitespace-delimited words including tables and headings. The abstract remains 214 words.

## Reproducibility and publication blockers

A read-only run from the local checkout revalidated the 19,200 primary and 80 control records, then regenerated 17 output files in a temporary directory. All 17 matched byte for byte. It took 192.06 seconds elapsed on the audit host. The focused fixture suite passed 73 tests in 5.194 seconds. Neither the read-only run nor the tests dispatched new study conditions. The reproducibility check exercised the existing local checkout. Clean distribution testing remains a release checklist item.

Scientific HEAD alone lacks the untracked inputs and pinned tooling needed by that run. The release plan specifies the Git allowlist, original data inventory, archive and per-file checksum verification, dependency pins, expected storage and clean-checkout procedure. The principal data package contains 19,283 files and 1,001,361,591 extracted bytes. [Release plan](ARTIFACT_RELEASE_PLAN.md)

Before public release, obtain owner authorization, software and data license decisions and contributor permissions, and complete a metadata review. Confirm authorship and venue-specific access and anonymization rules. Prepare and independently verify the approved Git and archive package, select the public archive and persistent identifier, and test reviewer access. This audit established the branch identity only. It did not establish public availability of the complete artifact. The unresolved execution-clock discrepancy remains a documented limitation. Venue typesetting and print-scale figure review remain editorial tasks.

## Integrity and changed files

Verified byte identity for all 19,762 pre-existing tracked and non-ignored files outside the edited manuscript. This includes all frozen sources, configs, manifests, primary, pilot and control records, the analysis script, tables, seed matrix, existing figures and historical F2 evidence. The index remained empty and the tracked diff and whitespace checks passed. No staging, commit, push, tag, archive or publication occurred.

- Edited [MANUSCRIPT.md](MANUSCRIPT.md).
- Added [INDEPENDENT_EDITORIAL_AUDIT.md](INDEPENDENT_EDITORIAL_AUDIT.md).
- Added [ARTIFACT_RELEASE_PLAN.md](ARTIFACT_RELEASE_PLAN.md).
