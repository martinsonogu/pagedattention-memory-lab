# Phase 3 artifact release plan

Proposed version `phase3-kv-allocation-v1.0.0`. This plan describes a future release for owner approval. No release object, tag, archive, DOI, or upload was created in this milestone.

## Provenance and current availability

Local branch `phase-3-memory-aware-scheduling`, its cached tracking ref, and a live read of the same origin branch all returned `df794b67e72740bffb6272248b9d609c8decfaea`. Origin is `https://github.com/martinsonogu/pagedattention-memory-lab.git`. The read confirms the branch identity. Public access to a complete study artifact has yet to be verified.

The scientific HEAD contains the simulator, generator, original replay tooling, frozen configurations and analysis plan. It lacks the research-batch wrapper and its protocol, both study manifests and their saved records, the analysis implementation and conventions, all analysis outputs, and the paper. Checking out that SHA alone cannot regenerate the reported estimates from the original records. The research-batch CLI exposes only smoke and verification scopes. The primary and control inventories are embedded in their manifests, with workloads and condition identities. The saved-record analysis is the reproduction route for the paper.

Baseline Git classification used `git ls-files --cached`, `git ls-files --others --exclude-standard`, and `git ls-files --others --ignored --exclude-standard`. Counts and logical sizes are before this audit's edits. Sizes are exact bytes.

| Git state | Files | Bytes | Contents |
|---|---:|---:|---|
| Tracked | 30 | 439,864 | Phase 3 frozen source, configs, documentation and tests, plus earlier-phase files |
| Untracked, visible to Git | 19,733 | 1,036,680,872 | Raw records, manifests and study reports, 3E-5 and 3E-6 outputs, and historical engineering or operational evidence |
| Ignored | 17 | 327,276 | Python bytecode under `__pycache__/` |

The measured counts can be reproduced from exact path lists using these read-only commands.

```sh
git ls-files --cached
git ls-files --others --exclude-standard
git ls-files --others --ignored --exclude-standard
```

Of the baseline untracked files, 19,680 are in the five measured research-batch directories, 18 are in the analysis directory, and 35 are elsewhere. The latter include the four 3E-6 paper files, 16 milestone or protocol reports, the historical F2 audit helper, and 14 root-level Python modules or tests. The 16 other tracked files outside the release subset are earlier-phase or engineering files, their tests and results, and repository metadata or documentation.

The repository `.gitignore` contains `__pycache__/` and `*.pyc`. Use an explicit release allowlist. Exclude interpreter caches, local environment files, locks, and unrelated engineering artifacts from the public claim package.

## Release inventory

Keep the existing relative paths. Put source and review results in a versioned Git release, and the immutable raw inputs in an independently downloadable archive. A Git release commit may have a different SHA from scientific HEAD. Record both identifiers and preserve all pinned source bytes.

| Group | Current state | Files | Bytes | Proposed location |
|---|---|---:|---:|---|
| Tracked Phase 3 release subset | Tracked | 14 | 160,218 | Git |
| Batch and analysis additions | Untracked | 5 | 51,351 | Git |
| Primary, readiness, control, and statistical reports | Untracked | 4 | 58,837 | Git |
| Frozen analysis outputs and conventions | Untracked | 18 | 14,351,184 | Git |
| Paper and 3E-6 supporting files | Untracked | 4 | 43,730 | Git |
| 3E-7 audit and release plan | New | 2 | Measured when cutting the release | Git |
| Primary manifest and records | Untracked | 19,201 | 997,052,770 | Archive |
| Control manifest, specification and records | Untracked | 82 | 4,308,821 | Archive |
| Supplementary pilot manifest and records | Untracked | 385 | 20,239,647 | Optional provenance archive |
| Historical smoke and verification manifests and records | Untracked | 7 | 300,774 | Optional provenance archive |

The primary, control, pilot, smoke and verification directories each also contain one empty `.lock`. The analysis ignores those lock files. The primary and control archive requires **19,283 files and 1,001,361,591 bytes** extracted before filesystem overhead. Its 19,280 condition records plus two manifests and one specification preserve the observed data and complete realized workload definitions. Pilot and other historical runs have separate scopes and are unnecessary for the main paper reproduction.

**Git allowlist**

- Frozen implementation and runner support. `phase3_simulator.py`, `phase3_workloads.py`, `phase3_experiment.py`, `phase3_batch.py`, and `phase3_smoke.py`. Include `phase3/configs/{primary,pilot,smoke}.json`, `PHASE3_README.md`, `PHASE3_ANALYSIS_PLAN.md`, and `test_phase3_{simulator,workloads,experiment,batch}.py`. The pilot config is required by the primary and control manifest source pins even without pilot records. The smoke module and config support the reproduction test command.
- Batch and analysis. `phase3_research_batch.py`, `PHASE3_RESEARCH_BATCH_PROTOCOL.md`, `phase3_primary_analysis.py`, `test_phase3_primary_analysis.py`, and `test_phase3_research_batch.py`. The analysis reads raw records with the original validator.
- Evidence reports. `PHASE3_3E3_REAL_PRIMARY_REPORT.md`, `PHASE3_3E4A_CONTROLS_ANALYSIS_READINESS.md`, `PHASE3_3E4B_AMPLE_MEMORY_CONTROL_REPORT.md`, and `PHASE3_3E5_PRIMARY_STATISTICAL_RESULTS.md`. If retaining the readiness report's link to historical F2 closure in the public copy, provide the approved closure and referenced history in a separately reviewed provenance supplement or identify the reference as repository-local in release notes.
- Analysis. All 18 files in `phase3/analysis/3e5/`. These are `IMPLEMENTATION_SPEC.md`, `SUMMARY.md`, `EXPLORATORY_CONTROL.md`, `metadata.json`, `bootstrap_seed_indices.csv`, `seed_pairs.csv`, `primary_contrasts.csv`, `designed_grid_summary.csv`, `diagnostics.csv`, `secondary_progressing.csv`, `exploratory_control_checks.csv`, `exploratory_control_memory.csv`, and the six SVGs indexed in [Figure and table index](FIGURE_TABLE_INDEX.md).
- Paper and audit. `paper/{MANUSCRIPT,REFERENCES,FIGURE_TABLE_INDEX,SUBMISSION_READINESS,INDEPENDENT_EDITORIAL_AUDIT,ARTIFACT_RELEASE_PLAN}.md`. Add a reviewed release README, software license, data license, dependency lock or wheel hashes, release citation, and checksum lists at release time.

**Raw archive allowlist**

- `phase3/research_batch/3e3/primary/manifest.json` and all 19,200 `condition-<run_id>.json` files listed in the manifest. The records occupy 984,460,372 bytes, and the manifest occupies 12,592,398 bytes.
- `phase3/research_batch/3e4b/ample_memory_control/{manifest,specification}.json` and all 80 `condition-<run_id>.json` files. Records occupy 3,966,836 bytes. The manifest and specification occupy 280,456 and 61,529 bytes, respectively.
- For optional legacy provenance, use the manifest and all listed condition records under `3e2/pilot/`, `3e1/smoke/`, and `3e1/verification/` under the same research-batch root. Keep each scope distinct and attach a separate checksum list.

No baseline regular file reaches GitHub's 50 MiB warning threshold or 100 MiB individual-file limit. The largest baseline path is the 12,689,992-byte exact seed-pair CSV. The largest individual primary condition record is 54,240 bytes. Raw data still belong in an archive due to their aggregate size and file count. That keeps the Git checkout small while making the original data independently obtainable. The compressibility and final transfer size have not been measured. [GitHub large-file guidance](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)

## Versioned layout and verification

Use one Git release and one data deposit, linked in both directions. Proposed release attachments are `phase3-raw-v1.0.0.tar.gz` and `SHA256SUMS.archive`. The archive root contains the two repository-relative data directories and `SHA256SUMS.data`. The Git tree carries `SHA256SUMS.code-and-results` for the release allowlist and the exact archive checksum or a trusted release-metadata pointer. Keep checksum documents outside the validated condition directories. The loader rejects unexpected files in those directories.

For the release, generate SHA-256 lists for every original byte stream in sorted relative path order. Record archive bytes separately, and retain the original manifest file and embedded identity hashes, control specification digest, and seed-matrix hash. Verify a fresh download's archive hash before extraction. Verify the extracted per-file list against the independently published checksum list, reconcile its paths with the manifest inventories, then run the analysis validator. The validator recomputes manifest and record checksums, checks the pinned scientific source and realized workloads, and binds every condition to its expected inventory. Protect the checksum lists with release provenance such as a signed tag or detached signature if the owner supplies a signing identity. Checksums alone detect mismatches in bytes.

| Identity | SHA-256 |
|---|---|
| Primary manifest file | `17983e334c0980cbaabafa9da4fe2e9935977848475043de92db4906105a8b48` |
| Primary manifest identity | `bd289f8d52cc58bf8c0a14e57fb9231c394e092e3de78d4583df69eb7620c84d` |
| Control manifest file | `6ca36528c01b1af6c6d95814d850ce68a2b034e5d4de3976b97c9e5049ee99fe` |
| Control manifest identity | `6198d22c9d16d52f994a85e908fb42a36466fdeab186e300d06ceb5190dcb8fd` |
| Control specification file | `9bf6dbebc546e0d3a321c29057cec32c45bd924f7b489f429ff24c2a8a40e4ed` |
| Shared bootstrap CSV | `b99485a155a35e9f47a55916fe50a7bc752ca72d68e1d77386cdafa4d5f2f7de` |

## Reproduction after release

Use a fresh Git checkout of the eventual release commit on a POSIX system with Git, Python 3.12.3, NumPy 1.26.4, `shasum` or its SHA-256 equivalent, and `tar`. The original reference environment used CPython on x86-64 macOS 15.6. Python's `fcntl` and `resource` modules are imported by the pipeline. A clean release-candidate test is required for any additional environment, and floating-point output bytes can depend on numerical libraries. Use the pinned runtime for the byte comparison. The results may be reproduced without replaying any scientific condition.

Run these commands after separately obtaining the approved release files, from the release checkout root. The archive name and checksum files below describe the proposed layout.

```sh
shasum -a 256 -c SHA256SUMS.code-and-results
shasum -a 256 -c SHA256SUMS.archive
tar -xzf phase3-raw-v1.0.0.tar.gz
shasum -a 256 -c SHA256SUMS.data
python3.12 -m venv /tmp/phase3-release-venv
. /tmp/phase3-release-venv/bin/activate
python -m pip install numpy==1.26.4
python -B -m unittest -q test_phase3_primary_analysis test_phase3_research_batch test_phase3_batch test_phase3_experiment test_phase3_workloads test_phase3_simulator
out="$(mktemp -d)"
OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 python -B phase3_primary_analysis.py --output "$out"
for path in "$out"/*; do
  cmp "$path" "phase3/analysis/3e5/$(basename "$path")" || exit 1
done
```

The four original simulator and replay modules can also be exercised with their focused fixtures. The release reproduction command validates the historical records and regenerates all 17 generated analysis files. The eighteenth analysis file, `IMPLEMENTATION_SPEC.md`, is the frozen input convention document. The validator compares recorded source/provenance against the manifests rather than requiring a release commit to have the historical SHA. Full re-execution would create new timing and provenance fields. The original 19,200-condition run reported 13 h 7 min 51 s command elapsed, 6 h 34 min 32 s workflow monotonic elapsed, and 6 h 30 min 10 s summed condition timers. Those discrepant timings describe the historical run and provide no forecast for another machine.

Allow at least 3 GiB free for a fresh checkout, extraction, archive, and analysis scratch space, plus more if keeping an extra staging copy or the optional histories. The two extracted study directories occupy about 995 MiB in allocated local filesystem blocks, the regenerated analysis about 14 MiB. Runtime for the read-only replay on the audit host is reported in the [independent audit](INDEPENDENT_EDITORIAL_AUDIT.md). Compression, download, and extraction times depend on the eventual archive and environment.

## Licensing and public identifiers

The checkout has no project license file. Obtain the owner's approved software and data license decisions. Record copyright holders and contributor permissions. Verify rights for any reused code, imported content, figures, and third-party dependencies. The paper cites PagedAttention and Orca. The artifact plan distributes original study figures and data alongside citations. Confirm any venue-specific review or anonymization requirements before distributing related provenance.

Use a version-specific DOI from a trusted research repository such as Zenodo, or an institutional archive with a persistent identifier. Cite the exact data version in the paper and pair it with the Git release SHA and archive checksum. An approved release tag helps navigate the Git history. The data DOI provides independently accessible archival identity. [Zenodo DOI guidance](https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/)

## Release checklist

- [ ] Obtain owner approval for exact scope, licensing and permissions, target destinations, and any Git or public release action.
- [ ] Confirm authorship, release citation, venue requirements, and the public or reviewer access model.
- [ ] Review the source allowlist and manifests for publication rights and unintended local or confidential metadata. Keep frozen bytes intact. If any cannot be shared, document the affected validation and resolve access before release.
- [ ] Select the immutable Git release commit, identify the scientific HEAD separately, and prepare the permitted versioned raw archive and checksums.
- [ ] Reproduce from a clean, isolated checkout plus the downloaded-equivalent raw data. Verify file manifests, run the focused suite, and compare generated outputs before approval to publish.
- [ ] After authorization, publish the paired Git and archive records and verify anonymous or venue-approved reviewer access, checksum links, and the version-specific identifier.
- [ ] Add release URLs and the archival identifier to the manuscript's availability statement for the approved version.
