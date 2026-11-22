"""Phase 1 check: the data layer and protocol on the real run-to-failure datasets.

Loads each dataset through bearingshift.data (metadata only, no signals), and reports
one row per machine: bearings, failure outcome, snapshots, duration, commissioning size
under protocol v1, and where speed and defect orders came from. Fails if any machine
can't get a valid commissioning window or a split fails the leakage check.

Usage: python experiments/data_check.py --out results/data_check --datasets "ims xjtu_sy"
"""

from __future__ import annotations

import argparse
import json
import traceback
from pathlib import Path

import numpy as np

from bearingshift.data import load_runs
from bearingshift.protocol import PROTOCOL, commissioning_mask
from bearingshift.splits import check_no_leakage, commissioning_end, per_machine_split
from bearingshift.windowing import WindowTable


def summarise(name: str) -> dict:
    runs = load_runs(name)
    rows, problems = [], []
    for r in runs:
        row = {
            "machine": r.machine_id,
            "bearings": len(r.bearings),
            "failed_bearings": [b.key for b in r.bearings if b.failed],
            "failure_modes": sorted({b.failure_mode for b in r.bearings if b.failed}),
            "snapshots": r.n_snapshots,
            "duration_h": round(float(r.times_s[-1]) / 3600, 2),
            "median_interval_s": float(np.median(np.diff(r.times_s))),
            "fs": r.fs,
            "shaft_hz": None if r.shaft_hz is None else round(r.shaft_hz, 3),
            "orders": {k: round(v, 4) for k, v in r.fault_orders.items()},
            "sources": dict(r.sources),
        }
        try:
            mask = commissioning_mask(r.times_s, name)
            row["commissioning_snapshots"] = int(mask.sum())
            row["commissioning_life_frac"] = round(float(mask.sum()) / r.n_snapshots, 3)
            # One window per snapshot is enough to exercise the split check.
            table = WindowTable.build(
                [(r.machine_id, r.bearings[0].key, i, float(t), 0) for i, t in enumerate(r.times_s)]
            )
            ends = commissioning_end(
                {r.machine_id: r.times_s}, PROTOCOL.commissioning_seconds(name)
            )
            fit, ev = per_machine_split(table, ends)
            check_no_leakage(table, fit, ev, ends, "per_machine")
        except Exception as e:  # noqa: BLE001 - report every machine's problem
            problems.append(f"{r.machine_id}: {e}")
            row["commissioning_snapshots"] = None
        rows.append(row)
    return {"machines": rows, "problems": problems}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--datasets", default="ims xjtu_sy")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    report = {}
    for name in args.datasets.split() or ["ims", "xjtu_sy"]:
        try:
            report[name] = summarise(name)
        except Exception:  # noqa: BLE001
            report[name] = {"error": traceback.format_exc()}
            print(report[name]["error"])

    (args.out / "summary.json").write_text(
        json.dumps({"protocol_version": PROTOCOL.version, "datasets": report}, indent=2) + "\n"
    )

    lines = [f"# Data layer check (protocol v{PROTOCOL.version})", ""]
    ok = True
    for name, rep in report.items():
        lines += [f"## {name}", ""]
        if "error" in rep:
            ok = False
            lines += ["```", rep["error"].strip()[-1500:], "```", ""]
            continue
        if rep["problems"]:
            ok = False
            lines += ["**Problems:**", ""] + [f"- {x}" for x in rep["problems"]] + [""]
        lines += [
            "| machine | bearings | failed | mode | snapshots | duration h | interval s "
            "| commissioning | of life | shaft Hz | speed / BPFO source |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for m in rep["machines"]:
            lines.append(
                f"| {m['machine']} | {m['bearings']} | {', '.join(m['failed_bearings']) or '—'} "
                f"| {'; '.join(m['failure_modes']) or '—'} | {m['snapshots']} | {m['duration_h']} "
                f"| {m['median_interval_s']:g} | {m['commissioning_snapshots']} "
                f"| {m.get('commissioning_life_frac', '—')} | {m['shaft_hz']} "
                f"| {m['sources'].get('speed')} / {m['sources'].get('bpfo')} |"
            )
        lines.append("")
    lines.append(f"**Status: {'PASS' if ok else 'FAIL'}**")
    (args.out / "README.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    if not ok:
        raise SystemExit("data check failed; see results README")


if __name__ == "__main__":
    main()
