"""
Cross-Constant Transfer in Irrational Decimal Expansions
Low-compute reproducible experiment.

Training sources:
    pi, e, sqrt(2), sqrt(3)

Completely unseen transfer constants:
    sqrt(5), cbrt(2), golden ratio phi, ln(2), ln(3), zeta(3)

Task:
    use the most recent 32 decimal digits to predict the next digit.

Primary model:
    a 3,442-parameter causal dilated Temporal Convolutional Network (TinyTCN)

Baselines:
    validation-selected n-gram (orders 0--3)
    IID uniform digits
    single-constant TinyTCN training

Diagnostic control:
    Champernowne's constructed nonperiodic decimal

Chronological split:
    training     [0, 24000)
    validation   [26000, 29000)
    future test  [34000, 44000)

The code intentionally avoids large Transformers so that the experiment is
appropriate for a CPU-only or modest personal computer.
"""

from pathlib import Path
from collections import defaultdict
import json, math, os, platform, random, sys, time

import mpmath as mp
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import matplotlib.pyplot as plt

ROOT = Path("cross_constant_results")
ROOT.mkdir(parents=True, exist_ok=True)
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

CFG = {
    "n_digits": 48000,
    "train_end": 24000,
    "val_start": 26000,
    "val_end": 29000,
    "test_start": 34000,
    "test_end": 44000,
    "context": 32,
    "batch_size": 256,
    "steps": 260,
    "seeds": [11, 29, 47],
}
(ROOT / "config.json").write_text(json.dumps(CFG, indent=2), encoding="utf-8")

torch.set_num_threads(min(2, os.cpu_count() or 1))
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def decimal_digits(name, n):
    """Return n digits after the decimal point."""
    mp.mp.dps = n + 60
    functions = {
        "pi": lambda: mp.pi,
        "e": lambda: mp.e,
        "sqrt2": lambda: mp.sqrt(2),
        "sqrt3": lambda: mp.sqrt(3),
        "sqrt5": lambda: mp.sqrt(5),
        "cbrt2": lambda: mp.root(2, 3),
        "phi": lambda: (1 + mp.sqrt(5)) / 2,
        "ln2": lambda: mp.log(2),
        "ln3": lambda: mp.log(3),
        "zeta3": lambda: mp.zeta(3),
    }
    x = functions[name]()
    text = mp.nstr(x, n + 15, strip_zeros=False)
    frac = text.split(".")[1][:n]
    if len(frac) != n:
        raise RuntimeError(f"Could not generate {n} digits for {name}")
    return np.fromiter((ord(c) - 48 for c in frac), dtype=np.int64)


def champernowne(n):
    parts, total, i = [], 0, 1
    while total < n:
        s = str(i)
        parts.append(s)
        total += len(s)
        i += 1
    s = "".join(parts)[:n]
    return np.fromiter((ord(c) - 48 for c in s), dtype=np.int64)


def windows(arr, start, end, context):
    segment = torch.from_numpy(np.asarray(arr[start:end]).copy()).long()
    X = segment.unfold(0, context, 1)[:-1].contiguous()
    y = segment[context:].contiguous()
    return X, y


class CausalConv(nn.Module):
    def __init__(self, cin, cout, dilation):
        super().__init__()
        self.left_pad = 2 * dilation
        self.conv = nn.Conv1d(cin, cout, kernel_size=3, dilation=dilation)
        self.residual = nn.Conv1d(cin, cout, 1) if cin != cout else nn.Identity()

    def forward(self, x):
        y = self.conv(F.pad(x, (self.left_pad, 0)))
        return F.gelu(y) + self.residual(x)


class TinyTCN(nn.Module):
    def __init__(self):
        super().__init__()
        self.embedding = nn.Embedding(10, 12)
        self.network = nn.Sequential(
            CausalConv(12, 16, 1),
            CausalConv(16, 16, 2),
            CausalConv(16, 16, 4),
            CausalConv(16, 16, 8),
        )
        self.classifier = nn.Linear(16, 10)

    def forward(self, digits):
        z = self.embedding(digits).transpose(1, 2)
        z = self.network(z)
        return self.classifier(z[:, :, -1])


@torch.no_grad()
def evaluate(model, X, y, chunk=2048):
    model.eval()
    total_n = total_correct = 0
    total_loss = 0.0
    for i in range(0, len(y), chunk):
        xb = X[i:i + chunk].to(DEVICE)
        yb = y[i:i + chunk].to(DEVICE)
        logits = model(xb)
        total_correct += int((logits.argmax(-1) == yb).sum().item())
        total_loss += float(F.cross_entropy(logits, yb, reduction="sum").item())
        total_n += len(yb)
    ce = total_loss / total_n
    return total_correct / total_n, ce, math.exp(ce)


def train_tcn(Xtrain, ytrain, Xval, yval, seed, steps=260):
    set_seed(seed)
    model = TinyTCN().to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-4)
    generator = torch.Generator().manual_seed(seed + 555)
    best_ce = float("inf")
    best_state = None

    for step in range(1, steps + 1):
        idx = torch.randint(0, len(ytrain), (CFG["batch_size"],), generator=generator)
        xb = Xtrain[idx].to(DEVICE)
        yb = ytrain[idx].to(DEVICE)
        logits = model(xb)
        loss = F.cross_entropy(logits, yb)

        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        if step % 65 == 0:
            ids = torch.linspace(0, len(yval) - 1, min(1500, len(yval))).long()
            _, val_ce, _ = evaluate(model, Xval[ids], yval[ids], chunk=1500)
            if val_ce < best_ce:
                best_ce = val_ce
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)
    return model


def fit_ngram(arrays, order, alpha=0.5):
    global_counts = np.zeros(10, dtype=np.float64)
    counts = defaultdict(lambda: np.zeros(10, dtype=np.float64))
    for arr in arrays:
        global_counts += np.bincount(arr, minlength=10)
        if order > 0:
            for i in range(order, len(arr)):
                counts[tuple(arr[i-order:i])][arr[i]] += 1
    return counts, global_counts


def eval_ngram(arr, start, end, order, counts, global_counts, alpha=0.5):
    global_prob = (global_counts + alpha) / (global_counts.sum() + 10 * alpha)
    correct = 0
    loss = 0.0
    n = 0
    for i in range(start + order, end):
        if order == 0:
            prob = global_prob
        else:
            c = counts.get(tuple(arr[i-order:i]))
            if c is None or c.sum() == 0:
                prob = global_prob
            else:
                prob = (c + alpha) / (c.sum() + 10 * alpha)
        y = arr[i]
        correct += int(np.argmax(prob) == y)
        loss += -math.log(float(prob[y]))
        n += 1
    ce = loss / n
    return correct / n, ce, math.exp(ce)


def main():
    start_time = time.time()
    train_constants = ["pi", "e", "sqrt2", "sqrt3"]
    unseen_constants = ["sqrt5", "cbrt2", "phi", "ln2", "ln3", "zeta3"]
    all_constants = train_constants + unseen_constants

    seq = {name: decimal_digits(name, CFG["n_digits"]) for name in all_constants}
    seq["iid"] = np.random.default_rng(20260908).integers(
        0, 10, CFG["n_digits"], dtype=np.int64
    )
    seq["champernowne"] = champernowne(CFG["n_digits"])

    for name, arr in seq.items():
        np.save(ROOT / f"{name}.npy", arr)

    # Pooled training windows. Boundaries are never crossed.
    Xtr, ytr, Xv, yv = [], [], [], []
    for name in train_constants:
        X, y = windows(seq[name], 0, CFG["train_end"], CFG["context"])
        Xtr.append(X); ytr.append(y)
        X, y = windows(seq[name], CFG["val_start"], CFG["val_end"], CFG["context"])
        Xv.append(X); yv.append(y)
    Xtrain = torch.cat(Xtr); ytrain = torch.cat(ytr)
    Xval = torch.cat(Xv); yval = torch.cat(yv)

    # Main pooled TinyTCN.
    rows = []
    for seed in CFG["seeds"]:
        model = train_tcn(Xtrain, ytrain, Xval, yval, seed, CFG["steps"])
        for name in all_constants + ["iid"]:
            X, y = windows(seq[name], CFG["test_start"], CFG["test_end"], CFG["context"])
            acc, ce, ppl = evaluate(model, X, y)
            group = (
                "seen" if name in train_constants
                else "unseen" if name in unseen_constants
                else "iid"
            )
            rows.append({
                "seed": seed, "constant": name, "group": group,
                "accuracy": acc, "ce_nats": ce, "perplexity": ppl
            })

    pd.DataFrame(rows).to_csv(ROOT / "tcn_runs.csv", index=False)

    # Validation-selected pooled n-gram baseline.
    candidates = []
    train_arrays = [seq[name][:CFG["train_end"]] for name in train_constants]
    for order in [0, 1, 2, 3]:
        counts, gc = fit_ngram(train_arrays, order)
        val_ce = np.mean([
            eval_ngram(seq[name], CFG["val_start"], CFG["val_end"], order, counts, gc)[1]
            for name in train_constants
        ])
        candidates.append((val_ce, order, counts, gc))
    _, best_order, counts, gc = min(candidates, key=lambda x: x[0])

    ngram_rows = []
    for name in all_constants + ["iid"]:
        acc, ce, ppl = eval_ngram(
            seq[name], CFG["test_start"], CFG["test_end"], best_order, counts, gc
        )
        ngram_rows.append({
            "order": best_order, "constant": name,
            "accuracy": acc, "ce_nats": ce, "perplexity": ppl
        })
    pd.DataFrame(ngram_rows).to_csv(ROOT / "ngram_results.csv", index=False)

    # Constructed nonperiodic control.
    Xc, yc = windows(seq["champernowne"], 0, CFG["train_end"], CFG["context"])
    Xcv, ycv = windows(
        seq["champernowne"], CFG["val_start"], CFG["val_end"], CFG["context"]
    )
    control_model = train_tcn(Xc, yc, Xcv, ycv, seed=101, steps=320)
    Xct, yct = windows(
        seq["champernowne"], CFG["test_start"], CFG["test_end"], CFG["context"]
    )
    acc, ce, ppl = evaluate(control_model, Xct, yct)
    pd.DataFrame([{
        "sequence": "Champernowne", "accuracy": acc,
        "ce_nats": ce, "perplexity": ppl
    }]).to_csv(ROOT / "constructed_control.csv", index=False)

    env = {
        "python": sys.version,
        "platform": platform.platform(),
        "torch": torch.__version__,
        "mpmath": mp.__version__,
        "device": str(DEVICE),
        "elapsed_seconds": time.time() - start_time,
        "parameter_count": sum(p.numel() for p in TinyTCN().parameters()),
    }
    (ROOT / "environment.json").write_text(json.dumps(env, indent=2), encoding="utf-8")
    print(json.dumps(env, indent=2))


if __name__ == "__main__":
    main()
