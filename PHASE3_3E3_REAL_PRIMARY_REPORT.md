# Phase 3E-3 real primary execution report

**PRIMARY COMPLETE — READY FOR CONTROLS AND ANALYSIS REVIEW**

All **19,200 real scientific conditions** in the original 20-seed primary
inventory passed independent reconciliation. **Controls were not executed.
Final statistical analysis was not completed.** This report describes
observations from the frozen CPU simulation.

## Baseline and execution

| Identity | Value |
| --- | --- |
| Branch | `phase-3-memory-aware-scheduling` |
| Scientific HEAD and initial live remote | `df794b67e72740bffb6272248b9d609c8decfaea` |
| Platform and Python | macOS-15.6-x86_64-i386-64bit, CPython 3.12.3 |
| Output directory | [Primary records](phase3/research_batch/3e3/primary) |
| Manifest file SHA-256 | `17983e334c0980cbaabafa9da4fe2e9935977848475043de92db4906105a8b48` |
| Manifest identity SHA-256 | `bd289f8d52cc58bf8c0a14e57fb9231c394e092e3de78d4583df69eb7620c84d` |
| Ordered inventory SHA-256 | `a578f5f9912c062b6fd9899cba22e7798bffd9be524db44be443796840be90e0` |
| Approved historical v0.5 SHA-256 | `378ea13bfbbecf63cf1135c815a4b3161245d41c02511327b2951c2675a2a7d0` |
| Approved historical v0.4 SHA-256 | `899392a7b75349e43083fe8f66ad9b290108880a501cedd630f1990c3b042af3` |
| F2 closure SHA-256 | `0f7b03d6bf69440a1162fe5d2fd2bdbe351b452628afdeaed4d5e07983d56dd3` |

| Pinned file | SHA-256 |
| --- | --- |
| `phase3_experiment.py` | `2175c9f253696757d2337df6508150f6c1008ae8605cea9b01634953e292f5b4` |
| `phase3_simulator.py` | `610f978a4fb48eaf4d0c68d08a9b590828da2af22a7a7ae9e851a3957b431bec` |
| `phase3_workloads.py` | `372ea34f29086b53e50d366ad145b847e4ca00861ca056da4e43217421fb1684` |
| `PHASE3_RESEARCH_BATCH_PROTOCOL.md` | `b74171bf0577ca2b38c71bc5008b7e77271107319966abca32b1743c7b8336c8` |
| `phase3/configs/pilot.json` | `c1fac4619259bf7b059881e39c5d958fe37f4f742f54905bc43f18e600fcef25` |
| `phase3_batch.py` | `76b6cdb2ad0d0b07b32b552f7d1583de4369d48e086bf172aba6ff535b9168db` |
| `phase3_research_batch.py` | `c983a5eb3142bc5f727da0b81a0ca8cbcede7c3daf490307a4ebcf3704e6e9f7` |

The existing research-batch API ran the owner-authorized primary scope.
Its scientific source, wrapper, and existing smoke CLI remained unchanged.
The pilot was independently revalidated (384 rows). Its artifacts use a
different run identity and were preserved separately. No smoke, pilot, or
synthetic records were imported.

Commands ran from the repository root:

```sh
python3 -B -m unittest -v test_phase3_research_batch test_phase3_batch test_phase3_experiment test_phase3_workloads test_phase3_simulator
/usr/bin/time -p python3 -B - start < /tmp/phase3-3e3-primary.py
python3 -B - < /tmp/phase3-3e3-verify.py
```

The execution driver validated the pilot and froze the Cartesian primary
inventory before dispatch. Its substantive call after those checks was:

```python
from pathlib import Path
import phase3_research_batch as research
from phase3_workloads import generate

plan, configs = research.inventory_plan('primary')
workloads = [generate(config) for config in configs]
by_hash = {w.sha256: w for w in workloads}
items = [(by_hash[c['workload_sha256']], c)
         for c in research.inventory(workloads, plan)]
research.run_batch(Path('phase3/research_batch/3e3/primary'), plan, items, 'primary')
```

## Frozen inventory, validation, and resume

The `primary` manifest pins 20 seeds from 20261117 through 20261136,
4 lengths, 2 splits and 3 arrival patterns, yielding 480 distinct
workloads with 200 requests and M=2048. Each workload has 40 conditions
from five budgets (2048, 4096, 8192, 16384, 32768), four allocators and two
compute scenarios (unlimited, G8). Before dispatch, the launcher verified
every strategy tuple, condition ID and canonical position. The ordered ID
list was hashed before the existing runner durably published its manifest.

**67 relevant tests passed.** Independent verification regenerated the expected
workloads and condition IDs from the frozen axes. It checked the exact
canonical inventory, recomputed manifest, record and scientific-row hashes,
validated provenance and every scientific row, and reconciled the exact
on-disk condition file set. Results were 19,200 expected and 19,200 valid,
with neither missing, duplicate nor unexpected condition files.

Two resume invocations followed validation. Both guarded against any
simulator call and confirmed:

- Resume 1: primary: dispatched=0 skipped=19200 wall=182.831027s; all 19,201 JSON artifacts byte-identical.

- Resume 2: primary: dispatched=0 skipped=19200 wall=185.446195s; all 19,201 JSON artifacts byte-identical.

The execution log contains 19200 dispatch entries and 19,200
unique completions. There are 0 separately recorded
failure files. The post-run resumes dispatched nothing.
The execution log shows one invocation, no runner failures or retries, and
no incomplete conditions. Clock observations show extended intervals
between some recorded completions, as detailed below.

## Descriptive scientific results

These are fixed-design descriptive summaries. Arithmetical means below
weight conditions equally unless noted otherwise. Latency, waiting and
makespan are in simulator ticks. Progressing and active requests are
counts. Wall seconds refer to CPU execution. Pooled utilization divides
summed used by summed allocated slot ticks. Fragmentation is the share of
pooled allocated slot ticks unused. Peak occupancy fields use the memory
budget as denominator. Every condition admitted and completed 200
requests, and the scientific validator checked final release.

### Memory, waiting, and concurrency

| Budget | Allocator | n | Pooled utilization % | Pooled fragmentation % | Mean peak reserved % | Mean peak live % | Mean waiting ticks | Mean progressing requests | Mean peak active |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2048 | fixed | 960 | 32.24 | 67.76 | 100.00 | 64.92 | 32430.88 | 1.000 | 1.00 |
| 2048 | paged8 | 960 | 99.47 | 0.53 | 65.01 | 64.92 | 32430.88 | 1.000 | 1.00 |
| 2048 | paged16 | 960 | 98.88 | 1.12 | 65.09 | 64.92 | 32430.88 | 1.000 | 1.00 |
| 2048 | paged32 | 960 | 97.71 | 2.29 | 65.18 | 64.92 | 32430.88 | 1.000 | 1.00 |
| 4096 | fixed | 960 | 32.24 | 67.76 | 100.00 | 58.10 | 15513.99 | 1.960 | 2.00 |
| 4096 | paged8 | 960 | 99.85 | 0.15 | 78.56 | 78.41 | 20558.29 | 2.381 | 22.49 |
| 4096 | paged16 | 960 | 99.67 | 0.33 | 78.69 | 78.35 | 20639.25 | 2.520 | 21.72 |
| 4096 | paged32 | 960 | 99.32 | 0.68 | 78.95 | 78.25 | 21083.12 | 2.627 | 19.96 |
| 8192 | fixed | 960 | 32.24 | 67.76 | 100.00 | 47.40 | 7303.08 | 3.538 | 4.00 |
| 8192 | paged8 | 960 | 99.91 | 0.09 | 78.53 | 78.29 | 7790.13 | 4.581 | 50.89 |
| 8192 | paged16 | 960 | 99.81 | 0.19 | 78.73 | 78.18 | 8304.67 | 4.689 | 48.91 |
| 8192 | paged32 | 960 | 99.62 | 0.38 | 79.10 | 77.81 | 9402.83 | 4.728 | 45.15 |
| 16384 | fixed | 960 | 32.24 | 67.76 | 95.05 | 38.14 | 3243.94 | 6.484 | 7.60 |
| 16384 | paged8 | 960 | 99.86 | 0.14 | 68.21 | 67.70 | 838.74 | 6.805 | 74.06 |
| 16384 | paged16 | 960 | 99.69 | 0.31 | 68.77 | 67.70 | 890.28 | 6.823 | 73.60 |
| 16384 | paged32 | 960 | 99.40 | 0.60 | 69.77 | 67.59 | 1065.65 | 6.768 | 71.80 |
| 32768 | fixed | 960 | 23.68 | 76.32 | 87.10 | 28.32 | 2111.37 | 8.876 | 13.94 |
| 32768 | paged8 | 960 | 99.62 | 0.38 | 50.90 | 50.34 | 209.90 | 8.478 | 77.55 |
| 32768 | paged16 | 960 | 99.00 | 1.00 | 51.49 | 50.26 | 219.41 | 8.672 | 77.45 |
| 32768 | paged32 | 960 | 97.36 | 2.64 | 52.70 | 50.12 | 240.88 | 8.939 | 77.19 |

### Workload and compute variation

Mean p95 latency is the mean of condition-level percentiles. It is not
a pooled percentile of individual requests.

| Axis | Level | n | Mean latency ticks | Mean p95 latency ticks | Mean makespan ticks | Mean waiting ticks | Mean progressing requests |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| length | short | 4800 | 1694.17 | 3161.58 | 5940.88 | 1473.73 | 5.361 |
| length | medium | 4800 | 15731.54 | 28527.38 | 32175.42 | 11284.06 | 4.689 |
| length | long | 4800 | 48350.90 | 87863.76 | 93448.33 | 30352.13 | 3.573 |
| length | mixed | 4800 | 8861.16 | 16706.57 | 20225.30 | 6717.88 | 4.950 |
| split | generation-heavy | 9600 | 35973.34 | 65597.08 | 70602.79 | 23656.43 | 4.522 |
| split | prompt-heavy | 9600 | 1345.54 | 2532.56 | 5292.18 | 1257.48 | 4.765 |
| arrival | dense | 6400 | 19629.18 | 35644.12 | 37760.66 | 13018.63 | 5.575 |
| arrival | moderate | 6400 | 16621.33 | 30782.28 | 38274.76 | 11224.07 | 2.751 |
| arrival | bursty | 6400 | 19727.82 | 35768.06 | 37807.04 | 13128.15 | 5.604 |
| compute | unlimited | 9600 | 19676.08 | 36160.68 | 39997.84 | 12596.60 | 5.426 |
| compute | G8 | 9600 | 17642.81 | 31968.96 | 35897.13 | 12317.31 | 3.861 |

### Paired descriptive contrasts

Allocator contrasts pair the same workload including seed, memory budget,
and compute scenario. Compute contrasts pair workload, budget, and allocator.
Counts are lower / equal / higher for the alternative relative to its reference.
Delta equals alternative minus reference. Ties and adverse outcomes are included.

| Alternative vs reference | Pairs | Makespan lower/equal/higher | Mean makespan delta ticks | Mean latency lower/equal/higher | Mean latency delta ticks |
| --- | ---: | --- | ---: | --- | ---: |
| paged8 vs fixed | 4800 | 1352/2124/1324 | +14479.92 | 1642/1791/1367 | +8441.83 |
| paged16 vs fixed | 4800 | 1396/2133/1271 | +13804.64 | 1680/1776/1344 | +8169.48 |
| paged32 vs fixed | 4800 | 1439/2146/1215 | +13350.71 | 1671/1769/1360 | +8061.27 |
| G8 vs unlimited | 9600 | 1648/5021/2931 | -4100.72 | 1326/5007/3267 | -2033.27 |

### Seed variation

Each seed has 960 conditions. The quantities below describe variation
across seeds, with other axes held to the full frozen inventory.

| Seed | n | Mean latency ticks | Mean makespan ticks | Mean progressing requests | Sum wall seconds |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 20261117 | 960 | 18796.93 | 38389.79 | 4.626 | 1185.137 |
| 20261118 | 960 | 18592.60 | 38220.94 | 4.681 | 1119.724 |
| 20261119 | 960 | 18041.83 | 37091.45 | 4.574 | 1102.983 |
| 20261120 | 960 | 18595.85 | 37685.22 | 4.650 | 1236.406 |
| 20261121 | 960 | 19400.76 | 38528.56 | 4.728 | 1196.783 |
| 20261122 | 960 | 19461.23 | 39289.60 | 4.665 | 1200.919 |
| 20261123 | 960 | 19485.73 | 39343.53 | 4.571 | 1206.057 |
| 20261124 | 960 | 18380.91 | 37052.46 | 4.630 | 1169.667 |
| 20261125 | 960 | 18779.53 | 37504.13 | 4.675 | 1115.162 |
| 20261126 | 960 | 18272.55 | 37344.44 | 4.688 | 1098.086 |
| 20261127 | 960 | 18907.89 | 38496.94 | 4.606 | 1199.697 |
| 20261128 | 960 | 18463.09 | 37426.63 | 4.673 | 1106.918 |
| 20261129 | 960 | 18274.50 | 37368.62 | 4.623 | 1120.140 |
| 20261130 | 960 | 18011.19 | 37129.81 | 4.671 | 1107.403 |
| 20261131 | 960 | 18249.39 | 37649.24 | 4.577 | 1130.528 |
| 20261132 | 960 | 18733.44 | 38770.58 | 4.691 | 1552.880 |
| 20261133 | 960 | 19210.06 | 38146.24 | 4.667 | 1138.808 |
| 20261134 | 960 | 19237.97 | 38840.69 | 4.602 | 1156.326 |
| 20261135 | 960 | 18616.25 | 38012.54 | 4.662 | 1166.757 |
| 20261136 | 960 | 17677.12 | 36658.27 | 4.606 | 1099.854 |

## Execution runtime

- End-to-end command wall time summed across execution invocations:
  **47271.050 s (13.131 h)**.
- Sum of completed-condition timers: **23410.234 s (6.503 h)**.
- Recorded research workflow wall time: **23672.364 s**.
  The workflow minus completed-condition timers was **262.130 s**,
  encompassing manifest work, validation, publication, readback and reporting.
  Those components were not timed separately.
- Per-condition min 0.023214 s, median 0.054587 s,
  mean 1.219283 s, p90 2.924152 s,
  p95 7.243235 s, p99 16.414572 s, max 98.394674 s.
  Percentiles except the median use nearest rank.

**Elapsed-time anomaly.** Command wall time exceeded the runner's
monotonic workflow timer by **23,598.686 s**. The saved UTC timestamps span
47,156.649 s from manifest creation (2026-11-20 12:50:08.835 UTC) to final
completion (2026-11-21 01:56:05.485 UTC). The largest observed interval
between completions was 2,433.580 s, while the following condition's
local timer recorded 19.266 s. Neither host suspend state nor clock
adjustments were instrumented. The difference cannot be attributed to
scientific execution, validation, or publication from the available
timings. Both clocks are reported separately.

The prior 6.75-hour arithmetic was an assumption-dependent pilot projection.
Actual primary timing includes three additional budgets and 19 additional seeds.

| Axis | Level | n | Median wall s | P95 wall s | Max wall s | Sum wall s |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| allocator | fixed | 4800 | 0.0466 | 0.7706 | 6.4207 | 898.929 |
| allocator | paged8 | 4800 | 0.0582 | 11.6629 | 98.3947 | 7918.975 |
| allocator | paged16 | 4800 | 0.0577 | 9.6749 | 72.8345 | 7474.285 |
| allocator | paged32 | 4800 | 0.0572 | 9.9689 | 60.9519 | 7118.046 |
| budget | 2048 | 3840 | 0.0682 | 1.2394 | 2.7676 | 1092.545 |
| budget | 4096 | 3840 | 0.0543 | 7.1089 | 44.2700 | 4592.730 |
| budget | 8192 | 3840 | 0.0483 | 15.0370 | 73.6341 | 8725.024 |
| budget | 16384 | 3840 | 0.0475 | 11.7190 | 98.3947 | 5942.119 |
| budget | 32768 | 3840 | 0.0482 | 2.2230 | 24.9132 | 3057.816 |
| length | short | 4800 | 0.0458 | 0.2273 | 1.0665 | 301.464 |
| length | medium | 4800 | 0.2317 | 4.9475 | 16.6901 | 4370.926 |
| length | long | 4800 | 0.4567 | 15.9659 | 98.3947 | 16629.922 |
| length | mixed | 4800 | 0.1345 | 2.3597 | 5.2743 | 2107.922 |
| compute | unlimited | 9600 | 0.0515 | 10.5599 | 98.3947 | 13875.419 |
| compute | G8 | 9600 | 0.0580 | 6.4504 | 73.6341 | 9534.815 |

| Extreme | Condition | Seed | Length | Split | Arrival | Budget | Allocator | Compute | Wall s |
| --- | --- | ---: | --- | --- | --- | ---: | --- | --- | ---: |
| Fastest | [489f39b597b0c5336cc51ac58732656f1b2bb0053b40d832477344962aac3bfb](phase3/research_batch/3e3/primary/condition-489f39b597b0c5336cc51ac58732656f1b2bb0053b40d832477344962aac3bfb.json) | 20261128 | short | prompt-heavy | dense | 32768 | fixed | unlimited | 0.023214 |
| Slowest | [43bf7913d388281757a3a446b6e90703736705e9b250282bb06d6869f3f50709](phase3/research_batch/3e3/primary/condition-43bf7913d388281757a3a446b6e90703736705e9b250282bb06d6869f3f50709.json) | 20261132 | long | generation-heavy | dense | 16384 | paged8 | unlimited | 98.394674 |

## Integrity, limitations and stopping point

The conclusions are descriptive for the frozen deterministic simulator.
No GPU or vLLM throughput claims, inferential analysis, post hoc exclusions,
or paper-ready conclusions were produced. No scientific code, frozen
configuration, historical approved protocols, F2 closure, or earlier
pilot artifacts were changed. Raw primary records and manifest were retained.
The final integrity check verified all 30 tracked and 420 pre-existing
untracked files byte-for-byte. The Git index was empty and whitespace
checks passed. Nothing was staged, committed, or pushed.

**Controls were not executed. Final statistical analysis was not completed.**
