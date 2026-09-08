# Cross-Constant Transfer in Next-Digit Prediction of Irrational Decimal Expansions

**ID:** ORI-000001  
**Author:** @fssir  
**Created:** 2026-09-08T15:10:12+03:00 (GMT+3)  
**Source issue:** #4

## Idea

Train a lightweight causal sequence model jointly on the decimal expansions of several irrational mathematical constants—initially pi, e, sqrt(2), and sqrt(3)—and test whether any learned next-digit predictive structure transfers to completely unseen irrational constants such as sqrt(5), cbrt(2), the golden ratio, ln(2), ln(3), and zeta(3). The core scientific question is not whether a model can memorize or predict one familiar constant such as pi, but whether there is transferable raw-decimal predictive structure shared across distinct computable irrational constants. The study uses chronological train/validation/future splits, small low-compute models, n-gram and IID baselines, and a structured nonperiodic diagnostic control so that negative results can be interpreted carefully. The work explicitly does not claim that chance-level prediction proves randomness or normality.

## Prompt for AI

Use the human-supplied research idea as the core contribution. Assist with literature checking, low-compute experimental design, code generation and execution, statistical analysis, publication-quality figures, manuscript drafting, reproducibility files, and repository preparation. Keep all scientific claims conservative, verify references, distinguish empirical unpredictability from mathematical randomness/normality, and preserve complete English-language research materials for public reproducibility.
