# Phase 3 publication decisions

This is an owner decision record for the CPU simulation study. The verified local candidate is version `1.0.0-rc1`. Scientific HEAD is `df794b67e72740bffb6272248b9d609c8decfaea`. The publication version and release commit require separate approval. [Manuscript](MANUSCRIPT.md) · [Artifact release plan](ARTIFACT_RELEASE_PLAN.md) · [Candidate verification](RELEASE_CANDIDATE_VERIFICATION.md) · [Submission readiness](SUBMISSION_READINESS.md)

| Decision | Owner entry |
|---|---|
| Author names, order and affiliations | PENDING |
| Corresponding author and contact | PENDING |
| Contributions, contributor approval and permission to publish | PENDING |
| Software license and copyright attribution | PENDING |
| Data license and rights clearance | PENDING |
| Public Git repository URL and visibility | PENDING |
| Research-data archive and deposit owner | PENDING |
| Target journal, conference or preprint route | PENDING |
| Anonymization, embargo and reviewer access | PENDING |
| Funding and grant identifiers | PENDING |
| Competing-interest statement | PENDING |
| Public release version, tag and release date | PENDING |
| Release title, creator list and archival citation metadata | PENDING |
| Release commit and archival identifier | PENDING |
| Authorization to publish and submit | PENDING |

## Preserved candidate

The durable copy is at `/Users/mac/Downloads/paged_attention_release/phase3-kv-allocation-v1.0.0-rc1`. All 59 files and eight subdirectories matched the temporary original. Both copies matched the 58-entry master checksum list, and the list itself matched the verified 3E-8 SHA-256 `cf91a8b5003fcdfc1afe330aef80dd613acac87308050ceb76f07babbd93672c`. The original remains in place.

## Distribution boundaries

Paths below are relative to the preserved candidate directory. These classifications are proposed for a future approved release.

| Destination | Exact selection |
|---|---|
| Git source and results | The 47 payload paths in `phase3-kv-allocation-v1.0.0/SHA256SUMS.code-and-results`, subject to license and metadata approval. These include frozen source and configs, tests, the runner and analysis, reports, figures and paper files. Publish a checksum list for the final Git payload. Add approved license, citation and public reproduction instructions. |
| Research-data deposit | `phase3-raw-v1.0.0.tar.gz`, `SHA256SUMS.archive` and `SHA256SUMS.data`. The archive contains the 19,200 primary and 80 control records, their original manifests and the original control specification. The data checksum list is also at archive root. |
| Local-only validation | `validation-support/scientific-head-trees.pack`, `wheelhouse/numpy-1.26.4-cp312-cp312-macosx_10_9_x86_64.whl`, `REPRODUCE.sh`, `requirements.lock`, `README.md`, `RELEASE_METADATA.json`, `safety-scan.json` and `SHA256SUMS.distribution`. The Git pack contains author and committer metadata. Keep the wheel local pending explicit license and redistribution review. Use the pinned NumPy requirement and an approved package source in newly written public instructions. The master checksum list covers the full local candidate. |

Public instructions should document Python 3.12.3 and installation of `numpy==1.26.4` into a fresh virtual environment from the owner-approved package index. Pin the hash of the approved wheel for each supported environment. The verified local environment was macOS x86-64. The existing analysis-readiness report includes four repository-local historical links. Identify them as out of scope in the public README. Review remaining repository references and provenance fields for venue anonymization before release.

## Authorized publication sequence

1. Record every owner decision above and approve the exact public scope. Resolve contributor permissions, both licenses, identifiers in provenance, venue anonymization, and the archive and repository destinations. Preserve the verified candidate as a reference copy.
2. Prepare a clean release checkout. In a separate staging directory, verify the preserved candidate before copying files.

   ```sh
   cd /Users/mac/Downloads/paged_attention_release/phase3-kv-allocation-v1.0.0-rc1
   shasum -a 256 -c SHA256SUMS.distribution
   shasum -a 256 -c SHA256SUMS.archive
   cd phase3-kv-allocation-v1.0.0
   shasum -a 256 -c SHA256SUMS.code-and-results
   ```

3. Use the 47 listed paths to construct the release checkout at the same relative paths. Stage only those approved paths and the reviewed release documentation, licenses and citations. Review `git diff --cached --name-status` against the allowlist and confirm the manifest-pinned file hashes. If the destination is an existing repository, review inherited history before changing visibility. A new allowlist-only repository is an option if the owner wants to exclude prior history.
4. Create the authorized release commit and record its full SHA separately from scientific HEAD `df794b67e72740bffb6272248b9d609c8decfaea`. Create the approved version tag against the release commit. Verify the tag target, then push only the approved refs to the approved destination.
5. Deposit the three archive files named above. Confirm the raw archive SHA-256 is `ca8c6053f4e5519aab03f7c5521ec0214f1cb343a1abc6ac62453659d3c4dea3`. Record the version-specific identifier upon deposit. Cross-link the data record and exact Git commit or tag using release and deposit metadata.
6. Verify a fresh Git checkout and a fresh archive download using the public or venue-approved reviewer access mode. Check the archive checksum, extract it at the checkout root, and run `shasum -a 256 -c SHA256SUMS.data`. Follow the [reproduction steps](ARTIFACT_RELEASE_PLAN.md) with the approved package source. Confirm the 73 fixture tests pass and the 17 generated analysis files match the distributed results byte for byte.
7. Update the manuscript availability statement with the verified code URL, release SHA or tag, archive identifier, archive digest and reviewer access instructions. Treat any post-tag manuscript edit as a separately identified revision. Preserve the tagged payload and its checksums. Prepare the venue-specific manuscript, disclosure forms, artifact instructions and figure package. Seek owner authorization before submission.
