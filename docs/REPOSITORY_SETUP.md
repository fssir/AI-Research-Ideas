# Repository settings for the open model

The repository is designed so ordinary users never need direct repository-level Write permission. They contribute through fork + Pull Request and have maximum control over their own Idea folders.

## Ruleset for main

Recommended `Protect main` ruleset:

- Active
- Target: default branch (`main`)
- Require a Pull Request before merging
- Required approving reviews: `0`
- Do not require Code Owner review
- Block force pushes / non-fast-forward updates
- Restrict deletion of `main`
- Bypass: Repository administrators

## Required status check

After the `ori-validation` workflow has appeared at least once, edit the `Protect main` ruleset and enable **Require status checks to pass**, then add:

```text
ori-validation
```

This is the only required validation check needed for ordinary contributors.

## Auto-merge

Go to:

```text
Settings → General → Pull Requests
```

Enable **Allow auto-merge**.

The platform maintenance workflow uses auto-merge for its generated allocation/index PR after `ori-validation` passes.

## GitHub Actions permissions

Go to:

```text
Settings → Actions → General → Workflow permissions
```

Select **Read and write permissions** and enable **Allow GitHub Actions to create and approve pull requests**.

This allows the platform bot to create the follow-up PR that turns pending submissions into numbered official Idea folders.
