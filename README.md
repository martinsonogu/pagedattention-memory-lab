# KV-cache allocation and scheduling simulation

This study asks whether allocating key–value cache memory in blocks improves latency and makespan under FIFO admission with oldest-request memory protection. It uses a deterministic CPU simulator with abstract token slots. The results measure simulator ticks and do not benchmark GPU inference or vLLM.

## Phase 3 findings

The frozen primary study contains 19,200 conditions across 20 matched seeds and 2,160 planned contrasts. Across the equally weighted design grid, paged allocation reduced unused allocation while increasing mean latency, p95 latency, and makespan on average.

| Allocator | Mean latency | P95 latency | Makespan |
|---|---:|---:|---:|
| paged8 | +30.57% | +26.80% | +26.22% |
| paged16 | +26.29% | +21.79% | +22.36% |
| paged32 | +23.98% | +18.51% | +19.81% |

These are mean paired changes versus fixed reservation. Individual cells showed improvements, regressions, and ties. In a separate 80-condition exploratory ample-memory control, request timings agreed exactly across allocators while unused allocation differed.

- [Manuscript](paper/MANUSCRIPT.md) and [figure and table index](paper/FIGURE_TABLE_INDEX.md)
- [Statistical results and uncertainty intervals](PHASE3_3E5_PRIMARY_STATISTICAL_RESULTS.md)
- [Complete contrast table](phase3/analysis/3e5/primary_contrasts.csv) and [exact seed pairs](phase3/analysis/3e5/seed_pairs.csv)
- [Analysis program](phase3_primary_analysis.py) and [analysis metadata](phase3/analysis/3e5/metadata.json)

## Reproducing the saved-record analysis

The complete raw records and manifests are not publicly archived. A separate data archive is planned and has no DOI. A fresh clone contains the source, results, and figures. The raw-record analysis additionally requires the verified archive extracted at the repository root so the manifests and records land at their original relative paths. Four historical references in the analysis-readiness report point to repository-local materials outside this source release.

With the archive available and verified, use Python 3.12.3 and NumPy 1.26.4, installed in a virtual environment from an approved package source. Run the read-only analysis from the checkout root.

```sh
OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 python -B phase3_primary_analysis.py --output "$(mktemp -d)"
```

The scientific baseline is `df794b67e72740bffb6272248b9d609c8decfaea`. The GitHub source-and-results identity is the commit containing this README update. In a checkout of that commit, use `git rev-parse HEAD` to obtain its SHA. The two identities serve different purposes. [Artifact release plan](paper/ARTIFACT_RELEASE_PLAN.md) · [Candidate verification](paper/RELEASE_CANDIDATE_VERIFICATION.md)

## Earlier experiments

### Phase 1 KV-cache allocation mechanism experiment

Source paper: Kwon et al., *Efficient Memory Management for Large Language Model Serving with PagedAttention* (SOSP 2023), https://arxiv.org/abs/2309.06180

## Question
Under a fixed memory budget, how do maximum-length upfront reservations compare with on-demand fixed-size blocks for a synthetic set of request lengths?

## Experimental choices
- 500 independent synthetic workloads generated with Python's `random.Random(20261117)`; 100 candidate requests per workload.
- Maximum sequence length: 2048 token slots. Available KV-cache capacity: 32768 token slots. Every token slot is treated as having the same byte cost.
- Length mixture: 60% uniform 32–256; 30% uniform 257–1024; 10% uniform 1025–2048.
- Fixed strategy reserves all 2048 slots on admission. Paged strategy reserves `ceil(actual_length / block_size) * block_size` with blocks 8, 16, 32, or 64.
- Candidates processed in generated order; those that do not fit are skipped. Same workloads and budget are reused across strategies.
- The experiment models a *snapshot* with known actual lengths. It does not model dynamic token generation, memory reuse on completion, fragmentation in a real allocator, KV block sharing, attention computation, GPU kernels, scheduler policy, or throughput.

## Run
`python -m unittest -v`
`python experiment.py --output results.csv`

## Interpretation warnings
- The fixed-reservation baseline is deliberately conservative. Real serving systems may allocate less aggressively, or employ more advanced techniques.
- The comparison heavily favors paging for short sequences because the fixed strategy reserves the full 2048 slots even when few are used. This is a **mechanism demonstration**, not a representative performance benchmark.
- `unused_fraction` is computed only for admitted requests, and is not the same as the fraction of the total budget left unused. The latter includes free capacity and is not reported here.
- More admitted requests in this static allocation model **does not imply** equivalent gains in throughput or latency.
- Results are synthetic and cannot be compared numerically to the original paper's vLLM performance results.

## Phase 2 work needed
1. Add a time-stepped arrival, token-generation, and completion simulator.
2. Implement memory release and compare policies at equal offered load.
3. Introduce a less naive contiguous baseline and fragmentation accounting.
4. Report per-seed distributions and confidence intervals; test alternative length distributions and memory budgets.
5. Only after these checks, draft the article as a limited allocation-mechanism replication.
