# Contributing

## New idea

Use **Issues → New issue → Submit a new Idea**. Supply a title, a description and consent to CC0. An AI prompt is optional. A single Markdown file is enough; there is no required `metadata.yml`, keyword form or literature-search questionnaire.

The publisher creates `ideas/000001_YYYYMMDD_HHMMSS_GMTp3/README.md`, records the submitting GitHub account and its stable numeric ID, and updates the catalog. Number and timestamp become permanent when the publication PR merges. Do not allocate numbers manually. Creation times use a fixed `+03:00` offset, not a daylight-saving region.

## Upload a complete research folder

After your numbered folder is published, fork the repository, copy your local files **inside your own numbered folder**, commit/push and open a PR. GitHub Desktop or Git is useful for many files; GitHub's **Add file → Upload files** is sufficient for smaller uploads. The repository owner can use the same workflow. Never add an extra `ideas/` layer inside the numbered folder.

Any regular files may accompany an Idea. Suggested (not mandatory) subfolders are `code/`, `paper/`, `data/`, `results/`, `figures/`, and `reproducibility/`. The catalog links directly to folders that actually exist.

## Edit or delete

Propose changes to your own Idea via PR and tick the CC0 checkbox for original additions. The trusted publisher checks the authenticated PR author's numeric GitHub ID against the registry on `main`, not against ownership claims in your PR. You may rename files or remove the entire Idea. An active Idea must retain nonempty UTF-8 Markdown. A deleted published ID is never reused.

Public deletion removes the active entry; it does not erase Git history, earlier clones, or the effect of CC0. Existing provenance/author records are retained for administration, not as a reuse-attribution requirement.

## Openness and safety

Anyone may reuse CC0-covered work without permission or attribution, including commercially and in closed-source products. This does **not** grant strangers direct write access to the maintained upstream repository. You cannot edit another author's folder or platform code automatically. Maintainer infrastructure PRs are reviewed/merged manually, never auto-merged by the publisher.

Do not include secrets, private/confidential material or third-party works you cannot redistribute. Keep third-party licenses and notices; merely uploading something does not put it under CC0. Originality is a good-faith contributor obligation, not an automated novelty certificate. Respect applicable law and research ethics.

## Operational limits

Automation accepts at most 1000 changed paths / 100 MiB per PR and 50 MiB per regular file. Symlinks, submodules and unsafe paths are rejected. Each Markdown file must be at most 2 MiB and an Idea's Markdown at most 32 MiB; oversize content produces an explicit error rather than a silently incomplete index. Split long documents or link large datasets to a suitable data repository. These are hosting/safety limits, not restrictions on downstream CC0 reuse.

## When a submission is pending

The normal path uses one machine-owned publication branch/PR, not a new index PR on every change. Check the source Issue comment and PR's `ori-validation` check. After editing consent or content, the next event/periodic scan retries. GitHub scheduling is best effort and publication is not guaranteed to be instantaneous. Maintainers can run **Actions → ORI platform → Run workflow**.
