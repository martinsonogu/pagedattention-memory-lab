# Primary contrasts

The nine designed-grid summaries weight each of 240 workload–budget–compute cells and all 20 seeds equally.
Negative changes favor paged. Brackets show pointwise 95% seed-bootstrap intervals.

| Allocator | Outcome | Mean ticks [95% interval] | Mean % [95% interval] | Wins / ties / losses |
|---|---|---:|---:|---:|
| paged8 | mean_latency_ticks | +8441.828 [+8308.007, +8578.970] | +30.573 [+29.655, +31.531] | 1,642 / 1,791 / 1,367 |
| paged8 | p95_latency_ticks | +14573.425 [+14370.716, +14780.895] | +26.796 [+25.988, +27.630] | 1,511 / 1,944 / 1,345 |
| paged8 | makespan | +14479.919 [+14275.214, +14689.746] | +26.216 [+25.526, +26.935] | 1,352 / 2,124 / 1,324 |
| paged16 | mean_latency_ticks | +8169.479 [+8029.087, +8312.284] | +26.291 [+25.333, +27.274] | 1,680 / 1,776 / 1,344 |
| paged16 | p95_latency_ticks | +13904.025 [+13696.278, +14117.057] | +21.790 [+20.959, +22.647] | 1,572 / 1,947 / 1,281 |
| paged16 | makespan | +13804.638 [+13593.940, +14018.921] | +22.360 [+21.638, +23.095] | 1,396 / 2,133 / 1,271 |
| paged32 | mean_latency_ticks | +8061.271 [+7921.361, +8200.761] | +23.981 [+22.993, +24.995] | 1,671 / 1,769 / 1,360 |
| paged32 | p95_latency_ticks | +13460.034 [+13260.024, +13662.268] | +18.509 [+17.676, +19.353] | 1,619 / 1,955 / 1,226 |
| paged32 | makespan | +13350.710 [+13147.588, +13554.535] | +19.808 [+19.091, +20.530] | 1,439 / 2,146 / 1,215 |

[All 2,160 primary cells](primary_contrasts.csv) · [Exact matched pairs](seed_pairs.csv) · [Designed-grid data](designed_grid_summary.csv) · [Bootstrap metadata](metadata.json)

## Exploratory secondary measures

Diagnostics retain the six design dimensions. They report seed-average waiting in ticks, peak active concurrency, occupancy, blocking, stalls, deferrals, allocated/used/unused slot-ticks and protected headroom. Occupancy ratios use budget as denominator. The pooled unused share divides summed unused slot-ticks by summed allocation slot-ticks. Protected headroom is recorded separately.

Mean progressing requests equals generated tokens divided by makespan. Matched comparisons of this secondary measure share the same seed-level makespan information.

[Full diagnostics](diagnostics.csv) · [Matched progressing comparisons](secondary_progressing.csv)
