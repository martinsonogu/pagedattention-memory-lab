# Phase 1: KV-cache allocation mechanism experiment

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
