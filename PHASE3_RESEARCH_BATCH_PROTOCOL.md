# Phase 3E-1 research batch protocol

**Prospective scope, 2026-11-20.** This separate CPU simulation workflow
authorizes four smoke conditions and one isolated determinism rerun of the
short fixed condition. Stop after the four results, a validated resume, and
the isolated rerun. No pilot, primary matrix, controls, or additional
scientific conditions are authorized. The closed F2 executor and its
synthetic evidence remain separate from this workflow.

## Frozen design and selection

The simulation uses M=2048 and 200 requests per workload. The four length
regimes are short (32–256), medium (257–1024), long (1025–2048), and mixed
(60/30/10). Each crosses two splits and three arrival classes. The pilot
uses seed 20261117, budgets 2048 and 8192, fixed and paged8/16/32, and
unlimited compute and G8, giving 24 workloads × 16 strategies = 384
conditions. The primary inventory crosses seeds 20261117–20261136 inclusive
and budgets 2048, 4096, 8192, 16384 and 32768 with the same axes, giving
480 workloads × 40 strategies = 19,200 conditions. Concrete controls remain
to be specified prospectively.

In order run short fixed, short paged16, long fixed, and long paged16.
All four use seed 20261117, budget 8192, generation-heavy split, dense
arrivals and unlimited compute. Identify each through the existing
workload hash and condition-ID algorithm. Execute sequentially, with
unchanged allocation, FIFO admission, protection, generation, event order,
metric definitions, and scientific result schema.

## Records and interruption

Use `phase3/research_batch/3e1/smoke` for the four results and
`phase3/research_batch/3e1/verification` for the isolated short fixed rerun.
The canonical run manifest pins the scientific revision and source hashes,
batch and wrapper sources, frozen config and protocol digests, environment,
seed, realized workloads, ordered condition IDs, and creation time.
Completed-condition envelopes record the unchanged scientific row, its
wall-clock execution duration, and checksums bound to the manifest.

Use a cooperative writer lock and same-directory staged writes with file
synchronization, atomic no-overwrite linking, and directory synchronization.
A failed or unsupported barrier prevents reporting success. Resume checks
the manifest identity, exact expected inventory, canonical record,
checksums, and validated row schema before skipping any condition.
Re-establish local barriers for a complete matching record left visible
at interruption. Temporary data never count. Corrupt, conflicting or
foreign records stop the run. Do not overwrite them or retry automatically.
A caught failed attempt is recorded separately and the invocation stops.
Only an explicit later resume can run a condition that has no completed
record. An abrupt kill can leave no failure record, so absence of that
record supplies no evidence that execution never began.

The workflow makes no hard real-time deadline, crash-proof storage,
verified authority-loss cleanup, GPU or vLLM throughput claim. The smoke
outputs validate the scientific execution path. They do not test hypotheses
or justify selecting an allocator or launching the pilot.
