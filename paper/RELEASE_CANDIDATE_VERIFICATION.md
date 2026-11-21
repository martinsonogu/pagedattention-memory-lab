# Phase 3E-8 release candidate verification

**RELEASE CANDIDATE VERIFIED — AWAITING PUBLICATION APPROVAL**

The versioned local candidate is at `/tmp/phase3-kv-allocation-v1.0.0-rc1.CVwvYi`. It contains the source-and-results tree, the raw archive, offline test dependencies, reproduction instructions and release metadata. Copy this directory as a unit to retain it beyond the lifetime of temporary storage.

## Baseline and package inventory

The branch is `phase-3-memory-aware-scheduling` at scientific HEAD `df794b67e72740bffb6272248b9d609c8decfaea`. The tracked tree matched HEAD and the index was empty. The pre-existing untracked files include the already audited reports, raw evidence, analysis outputs and manuscript. SHA-256 comparison against the 3E-7 baseline agreed for frozen files. The documented manuscript edit and the two 3E-7 additions were the only differences from that baseline. The build checked both manifest identities, every manifest-pinned source, the frozen primary configuration and analysis plan, the implementation and conventions, and the bootstrap CSV hash against the original evidence. [Artifact release plan](ARTIFACT_RELEASE_PLAN.md) · [Analysis metadata](../phase3/analysis/3e5/metadata.json)

| Component | Files or members | Logical bytes |
|---|---:|---:|
| Candidate directory including the master checksum list | 59 files | 198,382,491 |
| Versioned source-and-results tree including its checksum list | 48 files | 14,698,263 |
| Raw study files extracted from the archive | 19,283 files | 1,001,361,591 |
| Primary manifest and condition records | 19,201 files | 997,052,770 |
| Control manifest, specification and condition records | 82 files | 4,308,821 |
| Raw archive including the embedded checksum list | 1 file, 19,284 members | 159,862,810 |
| Offline NumPy wheel | 1 file | 20,335,901 |
| Local Git test-support pack | 1 file | 1,276 |

The candidate occupied 193,864 KiB of allocated filesystem space. The extracted test workspace, virtual environment and analysis outputs occupied 1,177,348 KiB. The 47 payload paths in the source tree are enumerated in `phase3-kv-allocation-v1.0.0/SHA256SUMS.code-and-results`. They include 14 tracked Phase 3 files, five batch and analysis additions, four evidence reports, 18 analysis inputs and outputs, and six paper or audit files. The master list enumerates all 58 candidate files beside itself. The archive member list reconciles one-for-one with 19,200 original primary and 80 original control condition IDs, their two manifests, and one control specification. The optional historical runs, including pilot records, are excluded. Empty locks, caches, F2 operational files, and unrelated sources are excluded.

The raw tar uses original relative paths and regular files with normalized mode, time, ownership and name fields. The data list is at archive root, outside the validated directories. Gzip has a zero timestamp and no stored filename. An independent streaming reserialization checked every stored file hash and reproduced the archive SHA-256.

| File | SHA-256 |
|---|---|
| `phase3-raw-v1.0.0.tar.gz` | `ca8c6053f4e5519aab03f7c5521ec0214f1cb343a1abc6ac62453659d3c4dea3` |
| `SHA256SUMS.archive` | `1245fd1beab1fe837ed9fe7485305aff1c8afaca01ec4ae33b3ce769ee4086e5` |
| `SHA256SUMS.data` | `0013848811250279182d70654a071ec15497ba496e02ee4c42d61ce318890808` |
| `SHA256SUMS.distribution` | `cf91a8b5003fcdfc1afe330aef80dd613acac87308050ceb76f07babbd93672c` |
| `phase3-kv-allocation-v1.0.0/SHA256SUMS.code-and-results` | `40bbf08b14936aadcbc0bb8c160a35749236fedcf631af336a604f9dbe23f389` |
| NumPy 1.26.4 macOS x86-64 wheel | `b3ce300f3644fb06443ee2222c2201dd3a89ea6040541412b8fa189341847218` |

## Isolated verification

From the candidate directory, run the packaged validation script.

```sh
cd /tmp/phase3-kv-allocation-v1.0.0-rc1.CVwvYi
shasum -a 256 -c SHA256SUMS.distribution
sh REPRODUCE.sh
```

The script copies the 48-file source tree to a fresh directory, validates the payload checksums, extracts the raw archive, and validates all extracted data checksums. A four-object Git pack contains the existing scientific commit and its directory trees only. The script imports these into an isolated Git directory so the existing fixture tests can query HEAD and working-tree status. No new commit was created. The validation tree has no remote or alternate object-store dependency and does not use original untracked files. This partial pack is local test support. A future published Git checkout supplies its own Git metadata.

The environment was CPython 3.12.3, macOS 15.6 x86-64 and Git 2.43.0. A fresh virtual environment installed the included NumPy 1.26.4 wheel with pip `--no-index --no-deps --require-hashes`. The script clears Python user imports and inherited Git paths, and sets OpenBLAS and Accelerate thread limits to one. It runs the six test modules named in the release plan and invokes `phase3_primary_analysis.py --output <temporary-output-directory>` against the packaged records.

All **73 focused tests passed** in 4.592 seconds. The saved-record analysis validated 19,200 primary and 80 control conditions and reproduced 2,160 contrast cells. All **17 generated outputs matched byte for byte** in 227.96 seconds. The eighteenth analysis file is the frozen implementation specification used as input. No new scientific study conditions ran. No missing external files were necessary in the tested environment. The environment still requires an installed compatible Python, Git, tar and shasum. Other platforms have not been tested.

All local links in the manuscript, figure index and main result report resolve after extraction. All six original SVGs are in the source tree. The analysis-readiness report retains four historical links to the smoke report, pilot report, 4A readiness report and F2 closure. The candidate README identifies these as repository-local references outside the release scope. The literature links resolve through the corresponding proceedings or indexed bibliographic records. [PagedAttention](https://doi.org/10.1145/3600006.3613165) · [Author manuscript](https://arxiv.org/abs/2309.06180) · [SOSP proceedings](https://sigops.org/s/conferences/sosp/2023/toc.html) · [Orca](https://www.usenix.org/conference/osdi22/presentation/yu)

## Publication-safety review

Pattern-scanned all 47 original source and results files plus 19,283 original raw files for common credentials, token prefixes, private-key markers, URL credentials, email strings, personal home paths and host-identifier fields. No matches were found in those study files. This is a bounded screening result. Pinned files still preserve UTC execution timestamps, platform metadata, revision IDs, and the repository URL in the audit documentation. The owner and venue should review whether those identifiers are suitable for the chosen access model.

The local test pack contains original author and committer identity fields. The wheel carries upstream license and maintainer metadata. Four wheel members contain home-path patterns in packaged code or binary data. No private-key or selected credential-prefix patterns matched the wheel. Exclude the test pack from the public scientific artifact. Prefer installing the pinned wheel from the approved dependency source for public reproduction, or review all license notices before redistributing it. No pinned records were redacted or rewritten.

## Owner decisions and future release

- Approve the exact public scope and destinations. Confirm authorship, affiliation and contact metadata, code and data licenses, contributor permissions, dependency redistribution and venue anonymization. The candidate marks missing decisions as pending.
- After authorization, use the source checklist as the explicit Git allowlist. Review provenance identifiers and preserve the manifest-pinned bytes. Add the approved license and release citation, then create the authorized release commit and tag. Record its SHA alongside scientific HEAD. Keep the raw records, local test pack and environment out of Git.
- Deposit the exact verified raw archive and the archive and data checksum lists in the approved versioned archival repository. Obtain the persistent identifier through that repository after approval. Cross-link the repository commit or tag and archive record. Refresh the checksums for any approved public-facing packaging changes.
- Verify the resulting files from a clean checkout and fresh reviewer download. Check archive and per-file hashes, run the 73 tests and compare the 17 analysis files. Confirm the supported access model, archive identifier and availability statement before submission.

## Repository integrity

All 19,765 pre-existing tracked and non-ignored repository files remained byte-identical, including the frozen sources, configurations, primary, pilot and control records, tables, bootstrap data, figures and historical evidence. This report is the sole repository addition. The Git index stayed empty and `git diff --check` passed. Nothing was committed, tagged, pushed, uploaded, publicly released, assigned a DOI, or submitted.
