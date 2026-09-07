# Repository setup checklist

Repository: `fssir/AI-Research-Ideas`

Visibility: **Public**

Suggested description:

> Open AI+Idea research library: humans contribute original research ideas and core prompts; AI assists literature, code, data, experiments, figures, results, manuscripts, and repository preparation.

Suggested topics:

```text
open-science
research-ideas
ai-for-science
ai-assisted-research
scientific-machine-learning
research
reproducible-research
open-research
```

## Main branch protection

After the first `ori-validation` workflow has run successfully, configure a ruleset for `main`:

- require a pull request before merging;
- require status checks before merging;
- require `ori-validation`;
- block force pushes;
- block branch deletion;
- require conversation resolution (recommended);
- require Code Owner review for protected infrastructure (recommended).

Unknown contributors should not receive direct write access. Public users should contribute via fork and pull request.
