# Reproducing the Experiment

## Scope

This directory documents the low-compute reference experiment for ORI-000001.

The pooled training constants are:

- pi
- e
- sqrt(2)
- sqrt(3)

The zero-shot transfer constants are:

- sqrt(5)
- cbrt(2)
- golden ratio phi
- ln(2)
- ln(3)
- zeta(3)

## Install

```bash
python -m pip install -r ../code/requirements.txt
```

## Run

```bash
python ../code/experiment_full.py
```

The script creates a local `cross_constant_results/` directory containing generated data, run-level CSV files, and an environment record.

## Reference configuration

- 48,000 decimal digits generated per constant
- context length: 32
- training range: `[0, 24000)`
- validation range: `[26000, 29000)`
- future-test range: `[34000, 44000)`
- TinyTCN parameters: 3,442
- optimizer: AdamW
- learning rate: 0.003
- batch size: 256
- update steps: 260
- seeds: 11, 29, 47

## Interpretation boundary

This experiment does **not** prove that any tested constant is random, normal, or theoretically unpredictable. It tests only whether the specified models can extract transferable next-digit information from the selected raw decimal representations at the tested scale.

Before external publication, the human author should rerun the experiment on local hardware and verify all generated CSV files, figures, and manuscript values.
