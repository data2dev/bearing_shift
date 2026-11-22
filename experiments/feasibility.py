"""Phase 0 feasibility: does a simple physics indicator rise before failure on real data?

For every run-to-failure bearing in the requested datasets, computes per snapshot:
  - envelope-spectrum energy around BPFO and BPFI (physics health indicators)
  - RMS and kurtosis (what plants run today)
then sets a threshold from the first part of life only (commissioning window) and reports
when each indicator first departs from it for several consecutive snapshots.

There are no fault-onset labels, so this does not measure accuracy. It answers one
question: is there a visible, sustained departure before the end of life? See ROADMAP.md,
Phase 0 gate.

Usage (normally via the Experiment workflow):
    python experiments/feasibility.py --out results/feasibility --datasets "ims xjtu_sy"
"""

from __future__ import annotations

import argparse
import json
import re
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy.stats import kurtosis  # noqa: E402

from bearingshift.synthetic import band_energy, envelope_spectrum  # noqa: E402

# Protocol constants for Phase 0 (fixed before looking at results).
COMMISSIONING_FRACTION = 0.2  # first 20% of snapshots treated as healthy
MIN_COMMISSIONING = 10
K_SIGMA = 5.0
PERSIST = 3
BAND_REL = 0.02  # ±2% band around each defect frequency (slip tolerance)
MIN_SNAPSHOTS = 30
INDICATORS = ("bpfo", "bpfi", "rms", "kurtosis")

# Fallbacks from published bearing geometry, used only when metadata lacks them.
# IMS: Rexnord ZA-2115 at 2000 rpm (Qiu et al. 2006). XJTU-SY: LDK UER204 (Wang et al. 2020).
FALLBACK = {
    "ims": {"shaft_hz": 2000 / 60, "bpfo_order": 7.09, "bpfi_order": 8.91},
    "xjtu_sy": {"shaft_hz": None, "bpfo_order": 3.08, "bpfi_order": 4.92},
}
XJTU_CONDITION_HZ = {"1": 35.0, "2": 37.5, "3": 40.0}

TIME_COLS = ("timestamp", "datetime", "time", "elapsed_s", "life_s", "snapshot", "file_index")
SPEED_HZ_COLS = ("shaft_hz", "speed_hz", "rotation_hz")
SPEED_RPM_COLS = ("rpm", "speed_rpm", "shaft_rpm", "speed")
AXIS_COLS = ("axis", "sensor_axis", "direction", "channel")


def natural_key(s: object) -> list:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(s))]


def first_col(columns, candidates) -> str | None:
    lower = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand in lower:
            return lower[cand]
    return None


def col_containing(columns, token: str) -> str | None:
    for c in columns:
        if token in c.lower():
            return c
    return None


def as_float(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if np.isfinite(f) and f > 0 else None


@dataclass
class BearingResult:
    dataset: str
    bearing_id: str
    n_snapshots: int
    fs: float
    shaft_hz: float | None
    bpfo_hz: float | None
    bpfi_hz: float | None
    sources: dict = field(default_factory=dict)
    departure: dict = field(default_factory=dict)  # indicator -> snapshot index or None
    departure_life_frac: dict = field(default_factory=dict)
    commissioning_snapshots: int = 0


def schema_summary(meta) -> dict:
    out = {"n_rows": int(len(meta)), "columns": {}}
    for c in meta.columns:
        s = meta[c]
        info = {"dtype": str(s.dtype), "n_unique": int(s.nunique(dropna=False))}
        if info["n_unique"] <= 12:
            info["values"] = sorted(map(str, s.unique()))[:12]
        else:
            info["examples"] = list(map(str, s.head(3)))
        out["columns"][c] = info
    return out


def departure_index(values: np.ndarray, n_comm: int) -> int | None:
    base = values[:n_comm]
    sd = base.std(ddof=1)
    if not np.isfinite(sd) or sd == 0:
        return None
    thr = base.mean() + K_SIGMA * sd
    above = values > thr
    for i in range(n_comm, len(values) - PERSIST + 1):
        if above[i : i + PERSIST].all():
            return i + PERSIST - 1
    return None


def resolve_speed(dataset: str, rows, cols) -> tuple[float | None, str]:
    c = first_col(cols, SPEED_HZ_COLS)
    if c and (v := as_float(rows[c].iloc[0])):
        return v, f"metadata:{c}"
    c = first_col(cols, SPEED_RPM_COLS)
    if c and (v := as_float(rows[c].iloc[0])):
        return v / 60.0, f"metadata:{c}"
    fb = FALLBACK.get(dataset, {})
    if fb.get("shaft_hz"):
        return fb["shaft_hz"], "fallback:published"
    if dataset == "xjtu_sy":
        m = re.search(r"(\d)_\d", str(rows["bearing_id"].iloc[0]))
        if m and m.group(1) in XJTU_CONDITION_HZ:
            return XJTU_CONDITION_HZ[m.group(1)], "fallback:condition-from-bearing-id"
    return None, "missing"


def resolve_defect(dataset: str, which: str, rows, cols, shaft_hz) -> tuple[float | None, str]:
    c = col_containing(cols, which)
    if c and (v := as_float(rows[c].iloc[0])):
        # bearing-datasets stores fault frequencies as orders of shaft speed; treat
        # small values as orders and large ones as Hz.
        if v < 30 and shaft_hz:
            return v * shaft_hz, f"metadata:{c}(order)"
        return v, f"metadata:{c}(Hz)"
    order = FALLBACK.get(dataset, {}).get(f"{which}_order")
    if order and shaft_hz:
        return order * shaft_hz, "fallback:published"
    return None, "missing"


def pick_one_per_recording(rows, cols):
    """One signal per recording: prefer a horizontal / x axis channel, else the first."""
    axis_col = first_col(cols, AXIS_COLS)
    if axis_col:
        pref = rows[axis_col].astype(str).str.lower().isin(["horizontal", "x", "h", "radial"])
        rows = rows.assign(_pref=~pref).sort_values("_pref", kind="stable")
    return rows.groupby("recording_id", sort=False).head(1)


def analyse_bearing(ds, dataset: str, bearing_id, rows, cols) -> tuple[BearingResult, dict]:
    time_col = first_col(cols, TIME_COLS)
    rows = pick_one_per_recording(rows, cols)
    if time_col:
        rows = rows.sort_values(time_col, kind="stable")
        order_src = f"metadata:{time_col}"
    else:
        rows = rows.iloc[
            sorted(range(len(rows)), key=lambda i: natural_key(rows["recording_id"].iloc[i]))
        ]
        order_src = "natural-sort:recording_id"

    fs = float(rows["fs"].iloc[0])
    shaft_hz, speed_src = resolve_speed(dataset, rows, cols)
    bpfo_hz, bpfo_src = resolve_defect(dataset, "bpfo", rows, cols, shaft_hz)
    bpfi_hz, bpfi_src = resolve_defect(dataset, "bpfi", rows, cols, shaft_hz)

    series = {k: [] for k in INDICATORS}
    for _, x in ds.iter_signals(list(rows["signal_id"])):
        x = np.asarray(x, dtype=float).ravel()
        series["rms"].append(np.sqrt(np.mean((x - x.mean()) ** 2)))
        series["kurtosis"].append(kurtosis(x, fisher=False))
        freqs, amp = envelope_spectrum(x, fs)
        for name, f0 in (("bpfo", bpfo_hz), ("bpfi", bpfi_hz)):
            series[name].append(
                np.log10(band_energy(freqs, amp, f0, BAND_REL * f0) + 1e-30) if f0 else np.nan
            )

    arrays = {k: np.asarray(v, dtype=float) for k, v in series.items()}
    n = len(arrays["rms"])
    n_comm = max(MIN_COMMISSIONING, int(COMMISSIONING_FRACTION * n))
    res = BearingResult(
        dataset=dataset,
        bearing_id=str(bearing_id),
        n_snapshots=n,
        fs=fs,
        shaft_hz=shaft_hz,
        bpfo_hz=bpfo_hz,
        bpfi_hz=bpfi_hz,
        sources={"order": order_src, "speed": speed_src, "bpfo": bpfo_src, "bpfi": bpfi_src},
        commissioning_snapshots=n_comm,
    )
    for k, v in arrays.items():
        idx = None if np.isnan(v).all() else departure_index(v, n_comm)
        res.departure[k] = idx
        res.departure_life_frac[k] = None if idx is None else round(idx / (n - 1), 3)
    return res, arrays


def plot_dataset(dataset: str, results: list[BearingResult], curves: list[dict], out: Path):
    n = len(results)
    ncols = 3
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(4.2 * ncols, 2.8 * nrows), dpi=90, squeeze=False
    )
    for ax, res, arr in zip(axes.flat, results, curves, strict=False):
        life = np.linspace(0, 1, res.n_snapshots)
        for name, color in (("bpfo", "tab:blue"), ("bpfi", "tab:green")):
            v = arr[name]
            if np.isnan(v).all():
                continue
            z = (v - v[: res.commissioning_snapshots].mean()) / (
                v[: res.commissioning_snapshots].std(ddof=1) or 1.0
            )
            ax.plot(life, z, lw=0.9, c=color, label=name.upper())
            idx = res.departure[name]
            if idx is not None:
                ax.axvline(life[idx], c=color, ls=":", lw=1)
        ax.axhline(K_SIGMA, c="k", ls="--", lw=0.8)
        ax.axvspan(0, life[res.commissioning_snapshots - 1], color="0.92")
        ax.set_title(f"{res.bearing_id} (n={res.n_snapshots})", fontsize=9)
        ax.set_xlabel("fraction of life", fontsize=8)
        ax.set_ylabel("z vs commissioning", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.set_ylim(-5, max(4 * K_SIGMA, ax.get_ylim()[1] if ax.lines else 0))
        ax.set_yscale("symlog", linthresh=10)
    for ax in list(axes.flat)[n:]:
        ax.axis("off")
    if n:
        axes.flat[0].legend(fontsize=7, loc="upper left")
    fig.suptitle(f"{dataset}: envelope energy at defect frequencies over life", fontsize=11)
    fig.tight_layout()
    path = out / f"{dataset}_indicators.png"
    fig.savefig(path)
    plt.close(fig)
    return path.name


def run_dataset(dataset: str, out: Path) -> dict:
    import bearing_datasets as bd

    ds = bd.open(dataset)
    meta = ds.metadata(backend="pandas")
    (out / f"{dataset}_schema.json").write_text(json.dumps(schema_summary(meta), indent=2) + "\n")
    cols = list(meta.columns)
    for required in ("signal_id", "recording_id", "bearing_id", "fs"):
        if required not in cols:
            raise KeyError(f"metadata has no '{required}' column; see {dataset}_schema.json")

    results, curves = [], []
    for bearing_id, rows in sorted(meta.groupby("bearing_id"), key=lambda kv: natural_key(kv[0])):
        n_rec = rows["recording_id"].nunique()
        if n_rec < MIN_SNAPSHOTS:
            continue
        res, arr = analyse_bearing(ds, dataset, bearing_id, rows, cols)
        results.append(res)
        curves.append(arr)
        print(f"[{dataset}] {bearing_id}: n={res.n_snapshots} departure={res.departure_life_frac}")

    figure = plot_dataset(dataset, results, curves, out) if results else None
    return {"bearings": [asdict(r) for r in results], "figure": figure}


def write_readme(out: Path, report: dict) -> None:
    lines = [
        "# Phase 0 feasibility: physics indicators over bearing life",
        "",
        f"Threshold: mean + {K_SIGMA:g}σ of the first {COMMISSIONING_FRACTION:.0%} of snapshots "
        f"(min {MIN_COMMISSIONING}); departure = {PERSIST} consecutive snapshots above it. "
        "Cells show the fraction of life at first departure (— = never).",
        "",
        "**Gate:** BPFO/BPFI departs before end of life on the IMS outer-race bearing and on most "
        "XJTU-SY bearings. Verdict is written by a human in this PR.",
        "",
    ]
    for dataset, rep in report.items():
        lines.append(f"## {dataset}")
        lines.append("")
        if "error" in rep:
            lines += ["**Error:**", "", "```", rep["error"].strip()[-1500:], "```", ""]
            continue
        lines.append(
            "| bearing | snapshots | BPFO | BPFI | RMS | kurtosis | speed / defect source |"
        )
        lines.append("|---|---|---|---|---|---|---|")
        for b in rep["bearings"]:
            f = b["departure_life_frac"]
            cell = [("—" if f[k] is None else f"{f[k]:.2f}") for k in INDICATORS]
            src = f"{b['sources']['speed']} / {b['sources']['bpfo']}"
            lines.append(
                f"| {b['bearing_id']} | {b['n_snapshots']} | " + " | ".join(cell) + f" | {src} |"
            )
        lines.append("")
        if rep.get("figure"):
            lines += [f"![{dataset}]({rep['figure']})", ""]
        lines.append(f"Metadata schema: `{dataset}_schema.json`")
        lines.append("")
    (out / "README.md").write_text("\n".join(lines))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--datasets", default="ims xjtu_sy")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    datasets = args.datasets.split() or ["ims", "xjtu_sy"]

    report: dict = {}
    for name in datasets:
        try:
            report[name] = run_dataset(name, args.out)
        except Exception:  # record and continue: a schema surprise shouldn't lose the others
            report[name] = {"error": traceback.format_exc()}
            print(report[name]["error"])

    (args.out / "summary.json").write_text(
        json.dumps(
            {
                "experiment": "feasibility",
                "protocol": {
                    "commissioning_fraction": COMMISSIONING_FRACTION,
                    "min_commissioning": MIN_COMMISSIONING,
                    "k_sigma": K_SIGMA,
                    "persist": PERSIST,
                    "band_rel": BAND_REL,
                },
                "datasets": report,
            },
            indent=2,
            default=str,
        )
        + "\n"
    )
    write_readme(args.out, report)
    if all("error" in r for r in report.values()):
        raise SystemExit("all datasets failed; see results README")


if __name__ == "__main__":
    main()
