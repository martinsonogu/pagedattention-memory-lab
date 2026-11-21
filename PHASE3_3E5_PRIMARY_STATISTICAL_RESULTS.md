# Phase 3E-5 paired statistical results

All three paged allocators increased mean latency, p95 latency and makespan on average across the frozen design grid. Each also improved outcomes in many cells. At 2,048 slots every measured timing outcome tied fixed on all 20 seeds. The separately analyzed ample-memory control also showed exact timing agreement, alongside substantial differences in allocation overhead.

## Provenance

The local branch and live origin branch were `phase-3-memory-aware-scheduling` at `df794b67e72740bffb6272248b9d609c8decfaea`. The index was empty. The primary dataset contains 19,200 validated conditions from 480 seeded workloads. Each of 20 seeds contributes all 24 workload definitions, five budgets, two compute settings and four allocators. The 384 pilot records and 80 control records are outside primary inference. The source digest checks include the workload generator, simulator, batch validator and research-batch protocol. [Primary execution report](PHASE3_3E3_REAL_PRIMARY_REPORT.md) · [Analysis readiness](PHASE3_3E4A_CONTROLS_ANALYSIS_READINESS.md) · [Control report](PHASE3_3E4B_AMPLE_MEMORY_CONTROL_REPORT.md) · [Research-batch protocol](PHASE3_RESEARCH_BATCH_PROTOCOL.md)

| Frozen artifact | SHA-256 |
|---|---|
| Primary manifest file | `17983e334c0980cbaabafa9da4fe2e9935977848475043de92db4906105a8b48` |
| Primary manifest identity | `bd289f8d52cc58bf8c0a14e57fb9231c394e092e3de78d4583df69eb7620c84d` |
| Primary config | `3753af5cb496b4ba395a8f846b4871c0060407de75828e00d445206bad46d8fa` |
| Paired analysis plan | `eff60269f9fa72efa552be796f432cce46ee231def9b3676999d2d565f860c93` |
| Exploratory control manifest file | `6ca36528c01b1af6c6d95814d850ce68a2b034e5d4de3976b97c9e5049ee99fe` |
| Exploratory control manifest identity | `6198d22c9d16d52f994a85e908fb42a36466fdeab186e300d06ceb5190dcb8fd` |

## Prespecified questions and estimands

For each frozen workload, budget and compute setting, how does each paged block size change mean end-to-end latency, nearest-rank p95 end-to-end latency and makespan relative to fixed? How regularly does the direction recur across the 20 seeds?

Each comparison pairs fixed and paged on seed, condition dimensions and realized workload hash. The unit of replication is the seed. Each condition's mean latency is an exact fraction of integer request ticks and p95 is the 190th sorted latency among 200 requests. The absolute change is paged minus fixed in simulator ticks. The percentage change averages seed-level ratios with the fixed value as denominator. Exact seed-level signs determine wins, ties and losses. All 2,160 planned cells have 20 matched pairs, including all 43,200 seed–outcome contrasts, with zero missing or undefined denominators. [Frozen plan](PHASE3_ANALYSIS_PLAN.md) · [Pre-effect implementation specification](phase3/analysis/3e5/IMPLEMENTATION_SPEC.md) · [Complete contrasts](phase3/analysis/3e5/primary_contrasts.csv) · [Exact seed pairs](phase3/analysis/3e5/seed_pairs.csv)

Each pointwise 95% interval uses 10,000 draws of 20 seed indices with replacement from one shared matrix generated with Python `random.Random(20261118)`. Each selected seed carries its complete paired grid. The endpoints interpolate linearly at indices `(n − 1) × 0.025` and `(n − 1) × 0.975` in the sorted bootstrap estimates. The intervals describe seed uncertainty. They carry no multiplicity adjustment or confirmatory significance claim. [Reproducibility metadata](phase3/analysis/3e5/metadata.json) · [Shared seed indices](phase3/analysis/3e5/bootstrap_seed_indices.csv)

## Primary estimates

These designed-grid summaries weight all 240 workload–budget–compute cells and all 20 seeds equally within each allocator–outcome combination. Positive values indicate higher times for paged. Brackets show pointwise 95% intervals. Wins, ties and losses count the 4,800 seed–cell observations for each row. [Full cell estimates and paired distributions](phase3/analysis/3e5/primary_contrasts.csv) · [Designed-grid table](phase3/analysis/3e5/designed_grid_summary.csv) · [Win, tie and loss figure](phase3/analysis/3e5/win_tie_loss.svg)

| Allocator | Outcome | Paired change in ticks [95% interval] | Paired change in % [95% interval] | Wins / ties / losses |
|---|---|---:|---:|---:|
| paged8 | Mean latency | +8,441.83 [+8,308.01, +8,578.97] | +30.57 [+29.65, +31.53] | 1,642 / 1,791 / 1,367 |
| paged8 | P95 latency | +14,573.42 [+14,370.72, +14,780.90] | +26.80 [+25.99, +27.63] | 1,511 / 1,944 / 1,345 |
| paged8 | Makespan | +14,479.92 [+14,275.21, +14,689.75] | +26.22 [+25.53, +26.94] | 1,352 / 2,124 / 1,324 |
| paged16 | Mean latency | +8,169.48 [+8,029.09, +8,312.28] | +26.29 [+25.33, +27.27] | 1,680 / 1,776 / 1,344 |
| paged16 | P95 latency | +13,904.03 [+13,696.28, +14,117.06] | +21.79 [+20.96, +22.65] | 1,572 / 1,947 / 1,281 |
| paged16 | Makespan | +13,804.64 [+13,593.94, +14,018.92] | +22.36 [+21.64, +23.10] | 1,396 / 2,133 / 1,271 |
| paged32 | Mean latency | +8,061.27 [+7,921.36, +8,200.76] | +23.98 [+22.99, +24.99] | 1,671 / 1,769 / 1,360 |
| paged32 | P95 latency | +13,460.03 [+13,260.02, +13,662.27] | +18.51 [+17.68, +19.35] | 1,619 / 1,955 / 1,226 |
| paged32 | Makespan | +13,350.71 [+13,147.59, +13,554.54] | +19.81 [+19.09, +20.53] | 1,439 / 2,146 / 1,215 |

The cell-average tick differences were negative, zero and positive in 242, 258 and 220 of the 720 mean-latency cells, respectively. The corresponding counts were 247, 261 and 212 for p95 latency and 234, 280 and 206 for makespan. All 8,640 seed–outcome comparisons at 2,048 slots were exact ties. Fixed and paged both drain each request before the next starts when the budget equals the 2,048-slot maximum and oldest-request protection is active. [All primary cells](phase3/analysis/3e5/primary_contrasts.csv) · [Simulator](phase3_simulator.py)

Two 8,192-slot dense long-workload cells illustrate the range of scheduling outcomes. With generation-heavy workloads and unlimited compute, paged8 raised mean latency by 270.72% [270.28%, 271.14%] and makespan by 249.75% [248.78%, 250.79%], with 20 losses each. With prompt-heavy workloads and G8, paged32 reduced mean latency by 14.75% [13.48%, 15.95% reduction] and p95 latency by 14.67% [13.88%, 15.49% reduction], with 20 wins each. These are individual planned cells. Several design factors differ between the examples. [Mean latency by workload and budget](phase3/analysis/3e5/mean_latency_ticks.svg) · [P95 latency by workload and budget](phase3/analysis/3e5/p95_latency_ticks.svg) · [Makespan by workload and budget](phase3/analysis/3e5/makespan.svg)

## Exploratory interactions and scheduling diagnostics

Equal-weight marginal mean-latency changes across all three paged comparisons were −27.73% for short, +28.99% for medium, +102.66% for long and +3.87% for mixed. Generation-heavy and prompt-heavy averaged +76.36% and −22.46%. Dense, moderate and bursty averaged +27.22%, +26.36% and +27.27%. Across budgets from 2,048 through 32,768 slots, the corresponding marginal changes were 0.00%, +3.74%, +50.67%, +42.31% and +38.02%. These equal-weight marginal summaries collapse substantial workload-level variation. [Primary contrasts](phase3/analysis/3e5/primary_contrasts.csv)

| Block size | Unlimited mean-latency change | G8 mean-latency change |
|---|---:|---:|
| 8 | +44.27% | +16.88% |
| 16 | +35.20% | +17.38% |
| 32 | +27.06% | +20.91% |

The ordering across block sizes changes with compute setting. These marginal averages weight all budgets, workload definitions and seeds equally. Direct budget, G8-versus-unlimited and paged-versus-paged comparisons are exploratory. [Compute-scenario variation](phase3/analysis/3e5/compute_variation.svg)

Across the grid, fixed averaged 5.71 peak active requests and the paged allocators averaged 43.02 to 45.20. Mean admission waiting was 12,121 ticks for fixed and 12,366 to 12,845 ticks for paged. Fixed averaged 26,109 physical admission-blocked ticks per run. Paged averaged 560 to 575 physical admission-blocked ticks and 29,454 to 30,566 protection-related admission-blocked ticks. Paged also averaged approximately 1.36 to 1.52 million protected-headroom growth-stall request-ticks per condition, compared with zero for fixed. Mean compute deferrals ranged from 113,457 to 129,268 for paged and averaged 6,168 for fixed across both compute settings. These quantities use different clocks and denominators. They describe the observed concurrency and scheduling behavior without isolating a causal contribution from each mechanism. [Diagnostic cell table](phase3/analysis/3e5/diagnostics.csv)

Average unused allocation ranged from 0.51 million to 2.22 million slot-ticks for paged8 through paged32, and was 106.33 million for fixed. The unused share divides summed unused allocated slot-ticks by summed allocated slot-ticks. Unused allocation includes reservation slack for fixed and block rounding slack for paged. The diagnostics also report used and allocated slot-ticks, peak allocated and live occupancy as fractions of budget, and protected headroom slot-ticks separately. [Memory fragmentation figure](phase3/analysis/3e5/memory_fragmentation.svg) · [Diagnostic cell table](phase3/analysis/3e5/diagnostics.csv)

The paired mean of the progressing-request percentage changes was +9.96% for paged8, +12.23% for paged16 and +13.73% for paged32. Generated tokens are held constant within a pair, so progressing requests equals generated tokens divided by makespan and carries the same directional information within that pair. Averaging ratios of makespans and their reciprocals can produce positive grid averages for both. [Secondary progressing table](phase3/analysis/3e5/secondary_progressing.csv)

## Exploratory ample-memory control

All 80 saved conditions passed validation. All blocking and stall checks were zero, and request timing and aggregate timing agreed exactly among all four allocators within each seed. Each allocator used 40,340,732 slot-ticks. Fixed allocated 718,852,096 slot-ticks, paged8 41,568,896, paged16 42,971,104 and paged32 45,777,280. The pooled unused shares from the exact integer totals were 94.3881735583%, 2.95452638434%, 6.12125767120% and 11.8760835069%, respectively. This observation applies to the ample-memory workload under unlimited compute. The historical 640-control planning count lacked an executable specification, and no such suite was run. [Separate exploratory control summary](phase3/analysis/3e5/EXPLORATORY_CONTROL.md) · [Per-condition checks](phase3/analysis/3e5/exploratory_control_checks.csv) · [Exact allocation totals](phase3/analysis/3e5/exploratory_control_memory.csv)

## Limits and execution clocks

The deterministic CPU simulator models fungible token slots under FIFO admission and oldest-request protection. It abstracts away allocator overhead, prefill compute, bandwidth, block sharing, swapping and GPU execution. The effect estimates apply to this workload generator and fixed design, with workload variation across 20 seeds. They provide no empirical estimate of vLLM throughput, GPU speed or deployment performance. The designed-grid weights represent the experiment, with each cell contributing equally.

The primary execution report recorded command elapsed time of **13 h 7 min 51 s**, workflow monotonic elapsed time of **6 h 34 min 32 s** and summed condition timers of **6 h 30 min 10 s**. The discrepancy remains unresolved. These host clocks measure execution cost and are separate from simulated tick outcomes. [Primary execution clocks](PHASE3_3E3_REAL_PRIMARY_REPORT.md)

## Claim-to-evidence map

| Claim | Supporting output |
|---|---|
| Designed-grid timing increases for all block sizes, with favorable, tied and adverse individual outcomes | [Grid summary](phase3/analysis/3e5/designed_grid_summary.csv) · [Cell estimates](phase3/analysis/3e5/primary_contrasts.csv) · [Win, tie and loss figure](phase3/analysis/3e5/win_tie_loss.svg) |
| Timing varies with workload and budget, and all timing comparisons tie at 2,048 slots | [Mean latency](phase3/analysis/3e5/mean_latency_ticks.svg) · [P95 latency](phase3/analysis/3e5/p95_latency_ticks.svg) · [Makespan](phase3/analysis/3e5/makespan.svg) |
| Mean latency varies with compute scenario and block size | [Compute variation](phase3/analysis/3e5/compute_variation.svg) |
| Memory savings coexist with concurrency, protection stalls and deferrals | [Diagnostics](phase3/analysis/3e5/diagnostics.csv) · [Memory fragmentation](phase3/analysis/3e5/memory_fragmentation.svg) |
| Progressing requests share information with makespan | [Progressing requests](phase3/analysis/3e5/secondary_progressing.csv) · [Exact makespan pairs](phase3/analysis/3e5/seed_pairs.csv) |
| Ample-memory timing agreement coexists with differing allocation overhead | [Separate control summary](phase3/analysis/3e5/EXPLORATORY_CONTROL.md) |

## Reproduction and verification

From the repository root, run the analysis or select a separate output directory with `--output`. The implementation loads and validates saved records. It never dispatches a simulation.

```sh
OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 python3 phase3_primary_analysis.py
python3 -m unittest -q test_phase3_primary_analysis test_phase3_research_batch test_phase3_batch test_phase3_experiment test_phase3_workloads test_phase3_simulator
```

[Analysis script](phase3_primary_analysis.py) · [Focused tests](test_phase3_primary_analysis.py) · [Human-readable output summary](phase3/analysis/3e5/SUMMARY.md)

- **Repeatability.** Two full runs produced byte-identical tables, figures, summaries, metadata and seed-index CSV. The seed matrix SHA-256 is `b99485a155a35e9f47a55916fe50a7bc752ca72d68e1d77386cdafa4d5f2f7de`.
- **Independent checks.** Reconciled the full Cartesian inventory, all 43,200 unique pair keys and all 10,000 shared resamples. Independently recomputed exact latency or makespan from raw arrivals and completions for four cells covering all three outcomes, ties, improvement and regression. The paired values, means, signs and directly resampled interval endpoints agreed. All six SVGs parsed successfully.
- **Tests.** All 73 tests passed, including six focused analysis tests and 67 existing scientific validation tests. The existing tests exercised test fixtures. No new scientific study conditions ran.
- **Integrity.** SHA-256 comparison verified all 19,738 pre-existing files byte for byte, including all 19,200 primary, 384 pilot and 80 control outputs, scientific source and configs, the frozen plan, approved v0.4/v0.5 and the F2 closure. Branch and HEAD stayed fixed, the index remained empty and `git diff --check` passed. Only the analysis script, focused test file, report and analysis directory were added. Nothing was staged, committed or pushed.

**ANALYSIS COMPLETE — READY FOR MANUSCRIPT**
