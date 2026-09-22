# Administration

## Keep the current main rules

Keep the branch ruleset active on `main`: require PRs, block force pushes/deletion, require `ori-validation` from GitHub Actions, and use zero mandatory human approvals for ordinary Idea changes. Administrator bypass is for manual recovery only; the publisher does not use it. Enabling "Require branches to be up to date before merging" adds another guard against concurrent-base changes.

Allow GitHub Actions to create pull requests in Settings → Actions → General. The YAML declares the needed write permissions per workflow; it is not necessary to make every workflow's default token writable. Keep general workflow token defaults read-only where feasible. Auto-merge may remain enabled, but ticking that option alone does not run a validator or merge every PR.

## Publication engine

`ORI platform` runs on new/edited Issues, main pushes, completion of `ORI contribution checks`, manual dispatch and an hourly recovery scan. All of these execute trusted `main` code. No `pull_request_target` event, external PAT, secret API key, uploaded artifact or untrusted checkout is needed. PR jobs from bot-created PRs may await approval under GitHub policy; publication does not depend on running those jobs. The trusted publisher independently verifies the complete candidate tree and creates the required `ori-validation` check through the Checks API.

There is one generated branch/PR, `automation/ori-platform`. When content and metadata do not change, no timestamp-only commit or PR is made. Pending content is regenerated from current main and source issues; no arbitrary user PR is rewritten. A publication PR that has not merged is a proposal, not a permanent allocation. Once on main, ID/time are fixed and deleted IDs remain as tombstones.

Source Issue comments give publication state and links. An automatically published issue is closed as completed, not deleted. Original body, provenance and Git history stay accessible.

If a workflow fails, read the explicit Actions error before retrying. Do not delete required checks, put the general Actions bot on an unconditional admin whitelist, or add `|| true` to suppress publication failures. Repository size limits and truncated API responses cause visible errors instead of incomplete catalogs. GitHub can coalesce/suspend scheduled events; the full scan and **Run workflow** provide recovery, not a hard real-time guarantee.

## Metadata and exposure

The existing description is retained. Topics currently include `ai`, `idea`, `research`; more specific optional topics are `research-ideas`, `ai-for-science`, `llm-for-science`, `automated-research`, `open-science`, `research-automation`. These are About metadata, not README tags. No Pages site is enabled by this audit. Catalog inclusion is not a guarantee of external search-engine indexing.

## Licensing

CC0 covers original material for which the contributor has rights; see `LICENSING.md`. No required attribution or retained-notice condition is imposed on CC0 material. Third-party notices, patents, trademarks and non-waivable rights remain outside that promise.
