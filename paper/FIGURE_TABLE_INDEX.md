# Figure and table index

All six figures are the existing validated analysis SVGs. The manuscript embeds them through relative paths.

| Figure | Manuscript location | Asset | Numerical authority and interpretation |
|---|---|---|---|
| 1. Direction of paired timing differences | Section 7 | [Win, tie and loss SVG](../phase3/analysis/3e5/win_tie_loss.svg) | [Grid tallies](../phase3/analysis/3e5/designed_grid_summary.csv). Counts per allocator and outcome, with exact signs and 4,800 comparisons per bar. |
| 2. Mean latency by workload and budget | Section 7 | [Mean latency SVG](../phase3/analysis/3e5/mean_latency_ticks.svg) | [All primary contrasts](../phase3/analysis/3e5/primary_contrasts.csv). Percent differences versus fixed, equal weights across 20 seeds per tile. |
| 3. Pooled unused share of allocated memory | Section 8 | [Memory SVG](../phase3/analysis/3e5/memory_fragmentation.svg) | [Diagnostics](../phase3/analysis/3e5/diagnostics.csv). Ratio of summed unused and allocated slot-ticks within allocator and budget. |
| A1. P95 latency by workload and budget | Appendix A | [P95 SVG](../phase3/analysis/3e5/p95_latency_ticks.svg) | [All primary contrasts](../phase3/analysis/3e5/primary_contrasts.csv). Each tile averages paired percentages of the condition-level nearest-rank p95. |
| A2. Makespan by workload and budget | Appendix A | [Makespan SVG](../phase3/analysis/3e5/makespan.svg) | [All primary contrasts](../phase3/analysis/3e5/primary_contrasts.csv). Each tile averages paired percentages of the condition-level makespan. |
| A3. Compute-scenario variation | Appendix A | [Compute SVG](../phase3/analysis/3e5/compute_variation.svg) | [All primary contrasts](../phase3/analysis/3e5/primary_contrasts.csv). Exploratory marginal percentages weight the 24 workload definitions and 20 seeds equally within each tile. |

| Table | Manuscript location | Evidence |
|---|---|---|
| 1. Frozen primary design | Section 5 | [Config](../phase3/configs/primary.json) · [Execution report](../PHASE3_3E3_REAL_PRIMARY_REPORT.md) |
| 2. Designed-grid effects | Section 7 | [Grid summary](../phase3/analysis/3e5/designed_grid_summary.csv) · [Exact seed pairs](../phase3/analysis/3e5/seed_pairs.csv) |
| 3. Exploratory control allocation totals | Section 9 | [Control memory totals](../phase3/analysis/3e5/exploratory_control_memory.csv) · [Record-level control checks](../phase3/analysis/3e5/exploratory_control_checks.csv) |
| A1. Scheduling and memory diagnostics | Appendix A | [Diagnostic cell means](../phase3/analysis/3e5/diagnostics.csv) |
| A2. Exact designed-grid tick differences | Appendix A | [Exact seed pairs](../phase3/analysis/3e5/seed_pairs.csv) |
| B1. SHA-256 identities | Appendix B | [Analysis metadata](../phase3/analysis/3e5/metadata.json) |

The [primary summary](../phase3/analysis/3e5/SUMMARY.md), [progressing-request estimates](../phase3/analysis/3e5/secondary_progressing.csv), [control summary](../phase3/analysis/3e5/EXPLORATORY_CONTROL.md), [shared seed draws](../phase3/analysis/3e5/bootstrap_seed_indices.csv), and [implementation conventions](../phase3/analysis/3e5/IMPLEMENTATION_SPEC.md) supplement the indexed figures and tables.
