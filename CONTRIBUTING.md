# Contributing to AI Research Ideas

## What belongs here

A contribution should begin with a **specific, original research idea**, not merely a broad topic.

Good examples include a new hypothesis, mechanism, modeling formulation, experimental design, benchmark, or scientifically meaningful combination whose contribution is clearly distinguished from known public work.

Not sufficient by itself: generic topics such as “use AI for batteries,” copied paper ideas with altered wording, or bulk AI-generated text with no identifiable original contribution.

## Originality declaration

Before submission, perform a reasonable public literature/prior-art search and complete the originality section of `metadata.yml`.

You must provide: search date, sources/databases searched, queries/keywords used, closest public work found, specific differences, and `declaration: true`.

The repository does not certify absolute novelty.

## Submission path

Create:

```text
submissions/<your-github-username>/<short-slug>/
```

Do not create `ideas/000123_...` yourself. Official IDs and timestamps are assigned by the platform/maintainer.

## Required files

```text
README.md
metadata.yml
```

Recommended: `code/`, `data/`, `figures/`, `paper/`, `references/`.

Do not commit secrets, credentials, confidential research, private datasets without authorization, or content you do not have permission to redistribute.

## AI-assisted execution

AI may assist with literature searching/organization, programming, data work, simulation/experiments, analysis, plots/figures, research writing, documentation, and repository preparation.

The contributor remains responsible for validation. Fabricated citations, invented datasets represented as real, falsified experiments, or unsupported claims are prohibited.

## Ownership rule

For an official idea, ownership is recorded in `metadata.yml`.

A non-maintainer pull request may modify content only in its own submission path or an official idea whose recorded `owner.github` equals the pull-request actor. Core paths such as `.github/`, `scripts/`, `config/`, `registry/`, and root governance files are maintainer-controlled.

## Deleting an idea

The recorded owner may submit a pull request deleting the entire official idea folder. Its ORI ID is never reused; the registry keeps a tombstone record.

## Pull requests

Use the repository PR template. Automated validation must pass before merge. By contributing, you confirm that you have the right to publish the submitted material under its declared licenses.
