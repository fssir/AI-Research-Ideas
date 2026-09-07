# AI Research Ideas

An open research-idea library where **people provide the key original idea and prompt, and AI can assist with the rest of the research workflow**: literature search, coding, data organization, experiments, analysis, figures, results, manuscript drafting, and GitHub preparation.

## Minimum requirement

A research idea can be very simple. **One Markdown (`.md`) file is enough.**

For example:

```markdown
# My research idea

I think ...

Key idea: ...

Prompt for AI: ...
```

You may also add code, data, images, PDFs, notebooks, or other research files, but none of them are required.

Contributors should submit ideas they genuinely believe are original and not already publicly disclosed in the academic literature. See [NOVELTY_POLICY.md](NOVELTY_POLICY.md).

## How to submit

1. Fork this repository.
2. Create a temporary folder:

```text
submissions/<your-github-username>/<any-short-name>/
```

3. Put at least one `.md` file inside it.
4. Open a Pull Request to `main`.

Example:

```text
submissions/alice/new-transformer-idea/idea.md
```

No `metadata.yml`, abstract form, keyword list, code, data, or literature-search form is required.

## Official folder creation

After a submission is merged, the platform assigns the next permanent number and a GMT+3 timestamp, then moves the complete submission into:

```text
ideas/000001_YYYYMMDD_HHMMSS_GMTp3/
```

Example:

```text
ideas/000001_20260907_093612_GMTp3/
```

The number is never reused. The creation time is fixed to **GMT+3 (`+03:00`)** and recorded to the second.

The platform internally records the GitHub owner in `registry/ideas.json`; contributors do not need to create or edit metadata files.

## Ownership

The owner of an Idea can later add, edit, rename, or delete files inside their own official Idea folder through Pull Requests. They may also delete their entire Idea folder.

Other ordinary users cannot modify that Idea. Core platform files such as `.github/`, `scripts/`, and `registry/` are maintainer-controlled.

## Browse before opening folders

See [ideas/README.md](ideas/README.md). The index automatically extracts a title and short preview from the first Markdown file in each active Idea, so readers can understand the approximate content before opening the folder.

## Contribution model

```text
Any GitHub user
      ↓
Fork + Pull Request
      ↓
Only ownership/path validation
      ↓
Merge
      ↓
Automatic number + GMT+3 timestamp
      ↓
Official ideas/ folder
```

The goal is low-friction participation: **one idea, one Markdown file, and everything else is optional.**
