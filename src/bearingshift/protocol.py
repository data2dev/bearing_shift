"""The evaluation protocol, frozen in code.

Everything that decides how results are scored lives here, so that models can't
quietly change it. Changing any value means bumping ``PROTOCOL_VERSION`` and adding a
changelog entry in ROADMAP.md ("Protocol changelog") that explains why.

Definitions (see ROADMAP.md, "Evaluation protocol"):

- Unit of analysis: one machine (one run-to-failure record, ``run_id``) with all its
  bearings. Alarms are machine-level.
- Commissioning: a fixed amount of operating time from the start of each run, per
  dataset. Never a fraction of life, which would need the failure time in advance.
- Onset ``T_o``: first snapshot where the max over defect orders of the envelope
  indicator, on any bearing of the machine, exceeds its commissioning mean + ``k``
  sigma for ``m`` consecutive snapshots. ``None`` (undefined) if that never happens.
- False alarm: a sustained alarm before ``T_o``; not counted when onset is undefined.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

import numpy as np

PROTOCOL_VERSION = 1


@dataclass(frozen=True)
class Protocol:
    version: int
    # Operating time from the start of each run treated as healthy, per dataset.
    commissioning_s: Mapping[str, float]
    # Minimum snapshots inside commissioning for a threshold to be estimated at all.
    min_commissioning_snapshots: int
    # Onset / departure rule: mean + k_sigma * std of commissioning, m consecutive.
    k_sigma: float
    persist: int
    # Relative half-width of the band around each defect frequency (slip tolerance).
    band_rel: float
    # Defect orders used for the onset indicator.
    onset_orders: tuple[str, ...]
    # Baselines that must appear in every results table.
    required_baselines: tuple[str, ...] = field(default=("rms", "envelope"))

    def commissioning_seconds(self, dataset: str) -> float:
        try:
            return float(self.commissioning_s[dataset])
        except KeyError:
            raise KeyError(
                f"no commissioning duration defined for dataset '{dataset}'; "
                "add one to bearingshift.protocol.PROTOCOL (and bump the version)"
            ) from None


PROTOCOL = Protocol(
    version=PROTOCOL_VERSION,
    commissioning_s=MappingProxyType(
        {
            "ims": 24 * 3600.0,  # 24 h of a multi-week endurance test
            "xjtu_sy": 10 * 60.0,  # 10 min of an accelerated test lasting 42 min to 42 h
            "synthetic": 50.0,  # tests and demo
        }
    ),
    min_commissioning_snapshots=8,
    k_sigma=5.0,
    persist=3,
    band_rel=0.02,
    onset_orders=("bpfo", "bpfi"),
)


def commissioning_mask(
    times_s: np.ndarray, dataset: str, protocol: Protocol = PROTOCOL
) -> np.ndarray:
    """Boolean mask of snapshots inside the commissioning window.

    ``times_s`` are snapshot times in seconds; the window starts at the first snapshot.
    Raises if the window holds fewer than ``protocol.min_commissioning_snapshots``.
    """
    t = np.asarray(times_s, dtype=float)
    if t.ndim != 1 or t.size == 0:
        raise ValueError("times_s must be a non-empty 1-D array")
    mask = (t - t.min()) < protocol.commissioning_seconds(dataset)
    if mask.sum() < protocol.min_commissioning_snapshots:
        raise ValueError(
            f"commissioning window for '{dataset}' holds {int(mask.sum())} snapshots, "
            f"fewer than the minimum {protocol.min_commissioning_snapshots}"
        )
    return mask


def sustained_departure(
    values: np.ndarray,
    commissioning: np.ndarray,
    k_sigma: float = PROTOCOL.k_sigma,
    persist: int = PROTOCOL.persist,
) -> int | None:
    """Index of the first snapshot ending a run of ``persist`` values above threshold.

    Threshold = mean + ``k_sigma`` * std of ``values[commissioning]``. Only snapshots
    after the commissioning window are searched. Returns ``None`` if there is none.
    """
    v = np.asarray(values, dtype=float)
    c = np.asarray(commissioning, dtype=bool)
    if v.shape != c.shape:
        raise ValueError("values and commissioning must have the same shape")
    base = v[c]
    sd = base.std(ddof=1) if base.size > 1 else np.nan
    if not np.isfinite(sd) or sd == 0:
        return None
    return _first_sustained(v > base.mean() + k_sigma * sd, c, persist)


def _first_sustained(above: np.ndarray, commissioning: np.ndarray, persist: int) -> int | None:
    """First index after commissioning that ends ``persist`` consecutive ``True`` values."""
    if persist < 1:
        raise ValueError("persist must be >= 1")
    start = int(np.flatnonzero(commissioning).max()) + 1
    run = 0
    for i in range(start, above.size):
        run = run + 1 if above[i] else 0
        if run >= persist:
            return i
    return None


def onset_index(
    envelope_by_bearing_order: Mapping[tuple[str, str], np.ndarray],
    commissioning: np.ndarray,
    protocol: Protocol = PROTOCOL,
) -> int | None:
    """Machine onset ``T_o`` as a snapshot index, or ``None`` if undefined.

    ``envelope_by_bearing_order`` maps ``(bearing_key, order_name)`` to a per-snapshot
    envelope indicator (e.g. log band energy) for one machine. Orders not listed in
    ``protocol.onset_orders`` are ignored. Each series is standardised against its own
    commissioning statistics (z-score), the max is taken per bearing across orders, and
    the onset is the earliest point where that max stays above ``k_sigma`` for
    ``persist`` consecutive snapshots, on any bearing.
    """
    commissioning = np.asarray(commissioning, dtype=bool)
    by_bearing: dict[str, list[np.ndarray]] = {}
    for (bearing, order), series in envelope_by_bearing_order.items():
        if order not in protocol.onset_orders:
            continue
        s = np.asarray(series, dtype=float)
        base = s[commissioning]
        sd = base.std(ddof=1)
        if not np.isfinite(sd) or sd == 0:
            continue
        by_bearing.setdefault(bearing, []).append((s - base.mean()) / sd)

    onsets = []
    for zs in by_bearing.values():
        z = np.max(np.vstack(zs), axis=0)
        idx = _first_sustained(z > protocol.k_sigma, commissioning, protocol.persist)
        if idx is not None:
            onsets.append(idx)
    return min(onsets) if onsets else None
