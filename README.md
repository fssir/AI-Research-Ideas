# AI Research Ideas (ARI)

**An open AI+Idea research library built around original human ideas.**

Humans contribute the **key research idea and core prompt**. AI may then assist with literature discovery and organization, coding, data preparation and analysis, experiments, result generation, figures, manuscript drafting, and repository preparation.

> **Novelty policy:** submissions must be original to the contributor and, after a reasonable public literature/prior-art search, the contributor must not be aware of public academic work that already discloses the same core idea. ARI does **not** certify absolute worldwide novelty.

## Research model

```text
Human
  └─ original key idea + core prompt
        ↓
AI-assisted research execution
  ├─ literature search and organization
  ├─ code generation and implementation
  ├─ data preparation and analysis
  ├─ experiments and evaluation
  ├─ result generation
  ├─ figures and visualization
  ├─ manuscript drafting
  └─ repository preparation
        ↓
Open research record
```

AI output is not treated as verified evidence by default. Contributors remain responsible for checking citations, methods, data provenance, calculations, research ethics, licensing, and the accuracy of claims.

## Browse ideas

See **[ideas/README.md](ideas/README.md)** for the human-readable index. Each entry shows the title, summary, field, owner, creation time, and status before the reader opens the full folder.

Official folders use:

```text
000001_YYYYMMDD_HHMMSS_GMTp3
```

Example:

```text
000001_20260907_093612_GMTp3
```

Public IDs use `ORI-000001`. Timestamps are assigned by the platform at allocation time using fixed **GMT+3 (`+03:00`)**, recorded to the second. IDs are never reused.

## Contribute

Public contributors do not need write access to the repository.

1. Fork this repository.
2. Create `submissions/<your-github-username>/<short-slug>/`.
3. Add at least `README.md` and `metadata.yml` using `templates/idea/`.
4. Open a pull request.
5. After review/validation, a maintainer/platform allocates the official ORI ID and GMT+3 timestamp.

The recorded owner may later update or delete their own official idea by pull request. Non-owners may not modify another contributor's idea.

See **[CONTRIBUTING.md](CONTRIBUTING.md)**.

## Required originality record

Every proposal must record:

- originality declaration;
- search date;
- databases/sources searched;
- actual search queries/keywords;
- closest known public work;
- explanation of the difference between that work and the submitted core idea.

See **[NOVELTY_POLICY.md](NOVELTY_POLICY.md)**.

## Repository integrity

The intended model is **fork → pull request → automated validation → merge**. Core infrastructure is maintainer-controlled. Validation checks path ownership, metadata, official folder naming, originality declarations, owner identity, protected paths, and common unsafe binary extensions.

## Licensing

Unless an individual idea declares a compatible alternative:

- code: Apache-2.0;
- original research text/documentation/figures: CC BY 4.0;
- third-party data/content: remains under its original license and must be identified.

See **[LICENSE.md](LICENSE.md)**.
