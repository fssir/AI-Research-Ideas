# Cross-Constant Transfer in Next-Digit Prediction of Irrational Decimal Expansions

**ID:** ORI-000001  
**Author:** @fssir  
**Created:** 2026-09-08T15:10:12+03:00 (GMT+3)  
**Source issue:** #4

## Idea

Train a lightweight causal sequence model jointly on the decimal expansions of several irrational mathematical constants—initially pi, e, sqrt(2), and sqrt(3)—and test whether any learned next-digit predictive structure transfers to completely unseen irrational constants such as sqrt(5), cbrt(2), the golden ratio, ln(2), ln(3), and zeta(3).

The core scientific question is **not** whether a model can memorize or predict one familiar constant such as pi. It is whether there is transferable raw-decimal predictive structure shared across distinct computable irrational constants.

## Research Field

- Artificial Intelligence / Machine Learning
- Mathematics / Statistics

## Keywords

cross-constant transfer; irrational numbers; decimal expansions; next-digit prediction; temporal convolutional network; numerical sequences; low-compute machine learning; generalization

## Current Low-Compute Result

A 3,442-parameter causal TinyTCN was trained jointly on pi, e, sqrt(2), and sqrt(3), then tested without fine-tuning on sqrt(5), cbrt(2), phi, ln(2), ln(3), and zeta(3).

Reference pilot means:

- seen training constants, future digits: **9.93%**
- completely unseen irrational constants: **9.99%**
- IID uniform-digit control: **10.10%**

The validation-selected n-gram baseline chose order 0, and the neural model did not improve cross entropy over the uniform reference. The current pilot therefore provides **no evidence of transferable raw-decimal next-digit structure** across the tested natural irrational constants at this scale.

A structured nonperiodic diagnostic based on Champernowne's decimal reached **54.7%** TinyTCN top-1 accuracy, showing that the same model can exploit some strong nonperiodic digit structure.

These findings do **not** prove randomness, normality, or theoretical unpredictability.

## Materials

### Paper

- [`paper/manuscript.md`](paper/manuscript.md) — complete English manuscript draft.

### Code

- [`code/experiment_full.py`](code/experiment_full.py) — complete low-compute reference experiment.
- [`code/requirements.txt`](code/requirements.txt) — Python dependencies.

### Results

- [`results/tcn_runs.csv`](results/tcn_runs.csv) — run-level pooled TinyTCN results.
- [`results/constant_summary.csv`](results/constant_summary.csv) — per-constant summary.
- [`results/group_summary.csv`](results/group_summary.csv) — seen/unseen/IID summary.
- [`results/ngram_results.csv`](results/ngram_results.csv) — validation-selected n-gram baseline.
- [`results/single_constant_tcn_runs.csv`](results/single_constant_tcn_runs.csv) — individual-constant runs.
- [`results/single_vs_pooled.csv`](results/single_vs_pooled.csv) — single versus pooled comparison.
- [`results/constructed_control.csv`](results/constructed_control.csv) — structured nonperiodic control.
- [`results/champernowne_baselines.csv`](results/champernowne_baselines.csv) — diagnostic-control baselines.
- [`results/prefix_audit.csv`](results/prefix_audit.csv) — generated constant-prefix checks.

### Figures

- [`figures/figure_1_experimental_design.svg`](figures/figure_1_experimental_design.svg)
- [`figures/figure_2_accuracy_by_constant.svg`](figures/figure_2_accuracy_by_constant.svg)
- [`figures/figure_3_cross_entropy_excess.svg`](figures/figure_3_cross_entropy_excess.svg)
- [`figures/figure_4_single_vs_pooled.svg`](figures/figure_4_single_vs_pooled.svg)
- [`figures/figure_5_champernowne_diagnostic.svg`](figures/figure_5_champernowne_diagnostic.svg)

### Reproducibility

- [`reproducibility/RUN.md`](reproducibility/RUN.md) — local reproduction instructions.
- [`reproducibility/config.json`](reproducibility/config.json) — reference configuration.
- [`reproducibility/reference_environment.json`](reproducibility/reference_environment.json) — executed reference environment.
- [`reproducibility/AI_ASSISTANCE.md`](reproducibility/AI_ASSISTANCE.md) — human contribution and AI assistance disclosure.
- [`CITATION.cff`](CITATION.cff) — citation metadata.

## Prompt for AI

Use the human-supplied research idea as the core contribution. Assist with literature checking, low-compute experimental design, code generation and execution, statistical analysis, publication-quality figures, manuscript drafting, reproducibility files, and repository preparation. Keep all scientific claims conservative, verify references, distinguish empirical unpredictability from mathematical randomness/normality, and preserve complete English-language research materials for public reproducibility.
