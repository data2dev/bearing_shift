"""Cut snapshots into analysis windows, with identity attached to every window.

Windows never span two snapshots, and every window carries its machine, bearing,
snapshot index and snapshot time. That identity is what ``bearingshift.splits`` uses
to prove there is no leakage.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


@dataclass(frozen=True)
class WindowSpec:
    length_s: float
    hop_s: float

    def __post_init__(self):
        if self.length_s <= 0 or self.hop_s <= 0:
            raise ValueError("length_s and hop_s must be positive")

    def samples(self, fs: float) -> tuple[int, int]:
        return int(round(self.length_s * fs)), int(round(self.hop_s * fs))


def frame(x: np.ndarray, length: int, hop: int) -> np.ndarray:
    """Split a 1-D signal into windows of ``length`` samples every ``hop`` samples.

    Returns a read-only (n_windows, length) view. Trailing samples that don't fill a
    whole window are dropped.
    """
    x = np.asarray(x)
    if x.ndim != 1:
        raise ValueError("x must be 1-D")
    if length < 1 or hop < 1:
        raise ValueError("length and hop must be >= 1")
    if x.size < length:
        return np.empty((0, length), dtype=x.dtype)
    return sliding_window_view(x, length)[::hop]


@dataclass(frozen=True, eq=False)
class WindowTable:
    """Identity of every window, as parallel arrays (one entry per window)."""

    machine_id: np.ndarray
    bearing_key: np.ndarray
    snapshot: np.ndarray
    time_s: np.ndarray
    window: np.ndarray  # index of the window within its snapshot

    def __len__(self) -> int:
        return int(self.snapshot.size)

    @classmethod
    def build(cls, entries: list[tuple[str, str, int, float, int]]) -> WindowTable:
        if not entries:
            empty = np.array([], dtype=object)
            return cls(empty, empty, np.array([], int), np.array([], float), np.array([], int))
        m, b, s, t, w = zip(*entries, strict=True)
        return cls(
            np.array(m, dtype=object),
            np.array(b, dtype=object),
            np.array(s, dtype=int),
            np.array(t, dtype=float),
            np.array(w, dtype=int),
        )

    def concat(self, other: WindowTable) -> WindowTable:
        return WindowTable(
            *(
                np.concatenate([getattr(self, f), getattr(other, f)])
                for f in ("machine_id", "bearing_key", "snapshot", "time_s", "window")
            )
        )


def window_snapshot(
    x: np.ndarray,
    fs: float,
    spec: WindowSpec,
    machine_id: str,
    bearing_key: str,
    snapshot: int,
    time_s: float,
) -> tuple[np.ndarray, WindowTable]:
    """Window one snapshot; return (windows, identity table)."""
    length, hop = spec.samples(fs)
    w = frame(x, length, hop)
    table = WindowTable.build(
        [(machine_id, bearing_key, snapshot, time_s, i) for i in range(w.shape[0])]
    )
    return w, table
