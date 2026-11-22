"""Smoke experiment: end-to-end check of the experiment pipeline on synthetic data.

Simulates a bearing run to failure (healthy, then an outer-race defect that grows),
tracks envelope-spectrum energy at BPFO per snapshot, sets an alarm threshold from the
commissioning window only, and reports when a sustained alarm would have fired.
No real data is used; this exists to prove the Actions workflow works before the
Phase 0 feasibility experiment on IMS / XJTU-SY.

Usage: python experiments/smoke.py --out results/smoke
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from bearingshift.synthetic import band_energy, bearing_signal, envelope_spectrum  # noqa: E402

FS = 20_000.0
SHAFT_HZ = 33.3
BPFO_ORDER = 3.58
N_SNAPSHOTS = 200
DEFECT_START = 140  # snapshot where the synthetic defect appears
COMMISSIONING = 50  # first N snapshots treated as healthy
K_SIGMA = 5.0
PERSIST = 3  # consecutive snapshots above threshold for a sustained alarm


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--datasets", default="", help="unused; synthetic only")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    bpfo_hz = BPFO_ORDER * SHAFT_HZ
    hi = np.empty(N_SNAPSHOTS)
    for i in range(N_SNAPSHOTS):
        sev = 0.0 if i < DEFECT_START else 0.5 + 0.15 * (i - DEFECT_START)
        x = bearing_signal(
            fs=FS, shaft_hz=SHAFT_HZ, defect_order=BPFO_ORDER, severity=sev, seed=1000 + i
        )
        hi[i] = band_energy(*envelope_spectrum(x, FS), bpfo_hz, 3.0)

    log_hi = np.log10(hi)
    base = log_hi[:COMMISSIONING]
    threshold = float(base.mean() + K_SIGMA * base.std(ddof=1))
    above = log_hi > threshold
    alarm = None
    for i in range(COMMISSIONING, N_SNAPSHOTS - PERSIST + 1):
        if above[i : i + PERSIST].all():
            alarm = i + PERSIST - 1
            break

    false_alarm = alarm is not None and alarm < DEFECT_START
    summary = {
        "experiment": "smoke",
        "data": "synthetic",
        "n_snapshots": N_SNAPSHOTS,
        "commissioning_snapshots": COMMISSIONING,
        "true_defect_start": DEFECT_START,
        "threshold_log10": round(threshold, 4),
        "first_sustained_alarm": alarm,
        "lead_time_snapshots": None if alarm is None else N_SNAPSHOTS - 1 - alarm,
        "false_alarm": bool(false_alarm),
        "detected": alarm is not None and not false_alarm,
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    fig, ax = plt.subplots(figsize=(8, 4), dpi=110)
    ax.plot(log_hi, lw=1.2, label="BPFO envelope energy (log10)")
    ax.axvspan(0, COMMISSIONING - 1, color="0.9", label="commissioning window")
    ax.axhline(threshold, ls="--", c="k", lw=1, label=f"threshold (mean + {K_SIGMA:g}σ)")
    ax.axvline(DEFECT_START, c="tab:orange", lw=1, label="synthetic defect starts")
    if alarm is not None:
        ax.axvline(alarm, c="tab:red", lw=1.5, label="first sustained alarm")
    ax.set_xlabel("snapshot")
    ax.set_ylabel("log10 band energy")
    ax.set_title("Smoke test: synthetic run to failure")
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(args.out / "health_indicator.png")

    status = "PASS" if summary["detected"] else "FAIL"
    (args.out / "README.md").write_text(
        f"# Smoke experiment: {status}\n\n"
        "Synthetic data only; checks the experiment pipeline end to end.\n\n"
        f"- Defect starts at snapshot {DEFECT_START} of {N_SNAPSHOTS}\n"
        f"- First sustained alarm: {alarm}\n"
        f"- False alarm before defect: {summary['false_alarm']}\n\n"
        "![health indicator](health_indicator.png)\n"
    )
    print(json.dumps(summary, indent=2))
    if not summary["detected"]:
        raise SystemExit("smoke experiment did not detect the synthetic defect")


if __name__ == "__main__":
    main()
