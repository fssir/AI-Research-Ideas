# Reproducing the Experiment

## Scope

This directory documents the low-compute reference experiment for ORI-000001. The pooled training constants are pi, e, sqrt(2), and sqrt(3). Zero-shot transfer is evaluated on sqrt(5), cbrt(2), the golden ratio, ln(2), ln(3), and zeta(3).

## Install and run

From a local clone, change into this Idea's `reproducibility/` directory before running the relative commands:

```bash
cd ideas/000001_20260908_151012_GMTp3/reproducibility
python -m pip install -r ../code/requirements.txt
python ../code/experiment_full.py
```

Use a separate virtual environment and review the code before executing it. The script creates `cross_constant_results/` under the current working directory; it does not overwrite the archived repository results.

## Output coverage — important

The current `code/experiment_full.py` writes generated constant sequences, the pooled `tcn_runs.csv`, `ngram_results.csv`, `constructed_control.csv`, `config.json`, and `environment.json`.

It does **not** currently regenerate every file archived in this research package: the per-constant/group summary tables, single-constant-versus-pooled comparisons, diagnostic baseline/prefix-audit tables and publication SVG figures need additional analysis/plot-generation steps that are not implemented in this script. Treat those as archived reference artifacts, not as outputs automatically reproduced by the single command above.

The repository-infrastructure audit did not re-run the research experiment or independently verify its reported numerical results. Before a paper submission, complete and execute the missing analysis steps, compare regenerated outputs against the archives, and record any differences. Do not claim full end-to-end reproducibility on the basis of this script alone.

## Reference configuration

- 48,000 decimal digits generated per constant
- context length: 32
- training range: `[0, 24000)`
- validation range: `[26000, 29000)`
- future-test range: `[34000, 44000)`
- TinyTCN parameters: 3,442
- optimizer: AdamW; learning rate: 0.003
- batch size: 256; update steps: 260; seeds: 11, 29, 47

## Interpretation boundary

This experiment does **not** prove that any tested constant is random, normal, or theoretically unpredictable. It tests whether the specified models can extract transferable next-digit information from the selected raw decimal representations at the tested scale. Verify generated CSV files, figures and manuscript values before making scientific claims.
