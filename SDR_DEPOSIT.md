# Stanford Digital Repository deposit preparation

This is a draft deposit record for the AGU 2026 project. **No SDR item or DOI has been created yet.** The current poster and model remain a research draft; release the archival version after the figures, author list, and rights have been checked.

## Recommended route

Use the [Stanford Digital Repository (SDR) GitHub workflow](https://sdr.library.stanford.edu/documentation/github-workflow) for this evolving code-and-data project. SDR archives **new public GitHub releases made after the SDR form is saved**, checks for releases nightly, assigns a DOI, and keeps later releases as versions of the same work. A one-time data/poster deposit can instead use the standard workflow if the team wants a separate dataset DOI.

The **Manage files** screen under **Stanford Research Data → Untitled deposit** is the standard file-upload workflow, not the GitHub workflow. To archive only the current data and poster there, upload the final poster PDF/PPTX, original stage and source CSVs, and the methods/source-audit documentation; link the exact GitHub code commit under **Related content**. Keep local `.git`, `.env`, backup, and generated Monte Carlo draws out of the upload. If the goal is instead automatic archiving of later repository releases, save this standard deposit as a draft and start a new **GitHub repository** deposit from the SDR dashboard.

Repository URL: https://github.com/geoz-lab/swe_token_energy

## Draft metadata for the SDR form

| Field | Proposed entry |
|---|---|
| Title | What Should We Count? Token Accounting for the Carbon Footprint of Agentic AI: Data, Code, and AGU 2026 Poster |
| Resource | Research software with supporting data and conference poster |
| Creators, in poster order | Ge Zhang; Jingru Cheng; Zitong Huang; Zhibo Dai; Anthony R. Kovscek |
| Affiliation | Department of Energy Science & Engineering, Stanford University |
| Description | This release contains a seven-stage, scenario-based model connecting attempted delegation of software-engineering work to agent sessions, token demand, benchmark-equivalent GPU time, facility electricity, U.S. electricity-source factors, and life-cycle emissions. It includes source ledgers, local task-token and A100/H100/H200 measurements, Monte Carlo scripts and summaries, and the AGU 2026 poster. The estimates are conditional on stated workload and serving assumptions; they do not measure accepted labor replacement or commercial-provider energy. |
| Keywords | agentic AI; software engineering; token accounting; GPU inference; data-center electricity; carbon footprint; Monte Carlo |
| Geographic scope | United States electricity-source scenarios; local GPU experiments on Stanford Sherlock |
| Related resource | Public GitHub repository above |
| Access | Public, once the archival release is approved by the authors |
| DOI | Request/reserve in SDR; do not enter a provisional or invented DOI |

Before completing the form, confirm the creator order and affiliations, add the depositor contact email and available ORCID iDs, and provide funder information if applicable. These are intentionally absent from `CITATION.cff` until confirmed.

## Files and rights

The release should archive the curated GitHub repository: poster PPTX/PDF/preview; numerical input and evidence CSVs; model scripts and compact outputs; figure source/exports; task-token records; GPU cell summaries, benchmark JSON, and power time series. The current tracked tree is about 9 MB, well below SDR's ordinary web-upload threshold, but the GitHub workflow avoids a separate manual file upload.

Project-authored source code uses [MIT](LICENSE). Original research data, scientific text, and figure/poster content use [CC BY 4.0](LICENSE-DATA.md), subject to the exclusions stated there. SDR currently applies licenses **at the item level**, not individually to each file. For a standard data-and-poster deposit containing no source code, choose CC BY 4.0 after the rights check. For an archive of the whole mixed-license repository, retain both license files and ask SDR staff about an appropriate custom use statement or separate deposits; do not label the whole mixed archive as solely MIT or solely CC BY. [SDR's guidance](https://sdr.library.stanford.edu/documentation/copyrights-licenses-and-access-restrictions) also permits file-level license notes in labels or within the files.

The poster contains Stanford branding and may contain other embedded marks. Confirm that all coauthors agree to the archive and that the poster's embedded media may be deposited under the SDR [Terms of Deposit](https://sdr.library.stanford.edu/documentation/understanding-sdr-terms-deposit). The benchmark task datasets and external factors are cited rather than relicensed here. Local `Experiment/.env` and `Experiment/.git_backup/` are Git-ignored and must stay out of the release.

## Release sequence

1. Freeze the poster and numerical claims; rerun the documented commands in [README.md](README.md) and check the [source audit](AGU_Token/numerical/SOURCE_AUDIT.md).
2. Complete the creator, contact, ORCID, funding, and rights entries above. Review the GitHub release contents and verify that credentials and local backups are absent.
3. Open the [SDR self-deposit application](https://sdr.stanford.edu/), choose the **GitHub repository** workflow, enter the public repository URL and metadata, request a DOI, and **save the form before creating any GitHub release**. First-time users may need to request SDR access.
4. If SDR provides a DOI before archiving, add it to `CITATION.cff` and the repository README; commit and push those changes.
5. Create the first public GitHub release from that exact commit. SDR checks nightly and archives releases created after the form was saved. Confirm the resulting PURL, DOI, metadata, file list, and license statement on the SDR record.

References: [Stanford repository-choice guide](https://guides.library.stanford.edu/data-sharing/where), [SDR GitHub workflow](https://sdr.library.stanford.edu/documentation/github-workflow), [SDR DOI service](https://library.stanford.edu/dois-digital-object-identifier), [SDR license options](https://sdr.library.stanford.edu/documentation/license-options), and [SDR Terms of Deposit](https://sdr.library.stanford.edu/documentation/understanding-sdr-terms-deposit).
