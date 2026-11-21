# Submission readiness

**MANUSCRIPT COMPLETE — READY FOR SCIENTIFIC EDITORIAL REVIEW**

The [manuscript](MANUSCRIPT.md) contains 4,596 whitespace-delimited words including headings and tables. The abstract is 214 words. The draft uses the frozen study and analysis artifacts. It is ready for scientific editorial review.

## Evidence review

| Check | Result |
|---|---|
| Design and coverage | Reconciled the frozen design, 2,160 unique contrast cells, 20 defined pairs in every cell, and 43,200 unique seed–outcome rows. |
| Primary findings | Checked all nine designed-grid point estimates, both sets of interval endpoints, and every win/tie/loss count against the CSV. Recomputed the exact mean tick differences from seed-level fractions. Checked the sign counts, 8,640 smallest-budget ties, and the four estimates and intervals in the two workload examples. |
| Exploratory analyses | Recomputed the reported design marginals, compute and block-size means, scheduling diagnostics, progressing-request means, and control allocation shares. Reconciled all 80 control check rows. |
| Figures and tables | Checked the six existing SVGs, all embedded asset paths, table references, and caption units, weighting, and interpretation. The heatmaps retain outcome-specific color ranges. |
| Citations | Checked PagedAttention against the indexed ACM proceedings record, official conference proceedings, and author manuscript. The direct ACM page returned a restricted response to the browser, and the indexed ACM record supplied the page range. Verified Orca against the USENIX citation and paper description. [Reference details](REFERENCES.md) |
| Scientific scope | Checked the abstract and conclusion against the table results, including adverse, favorable, and tied outcomes. The manuscript distinguishes prespecified contrasts from exploratory observations, and limits inference to the CPU simulator and frozen workload design. |
| Reproducibility | Checked the file and embedded manifest identities, configuration and plan hashes, script and convention hashes, and the shared draw CSV checksum. The manuscript attributes the two byte-identical analysis runs and 73 passing validation tests to 3E-5. |

## Open editorial items

- Confirm authors, affiliations, corresponding author, contributions, acknowledgments, funding, and competing-interest declarations.
- Choose a target venue and apply its formatting, anonymization, citation, and artifact policies. Check SVG legibility and color reproduction at the selected print width after typesetting.
- Confirm the repository distribution and archival plan, including license and permissions, public artifact URL, and a citable release identifier. The draft documents repository-local availability.
- The discrepancy among the primary execution clocks remains unresolved. The manuscript reports all three measured values independently of simulated outcomes.

## Repository integrity

The baseline and final SHA-256 inventories matched for all 19,759 pre-existing tracked and non-ignored files, including the scientific sources, frozen analysis, datasets, and historical F2 evidence. The only additions were the four requested Markdown files. Scientific HEAD remained `df794b67e72740bffb6272248b9d609c8decfaea`, the Git index remained empty, and `git diff --check` passed. The four new files also passed whitespace and local-link checks. This review read existing outputs and ran no scientific conditions. Nothing was staged, committed, pushed, or submitted.
