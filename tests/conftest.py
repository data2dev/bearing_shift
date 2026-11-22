"""Synthetic metadata in the layouts bearing-datasets uses for IMS and XJTU-SY.

Column names and value formats mirror the real schemas logged by the Phase 0 run
(results/feasibility/*_schema.json). No real data is used.
"""

import numpy as np
import pandas as pd
import pytest

from bearingshift.synthetic import bearing_signal


def ims_like(n_snapshots: int = 20, step_s: float = 600.0) -> pd.DataFrame:
    rows = []
    for run, failed, axes in (
        ("test1", "bearing_3+bearing_4", ["x", "y"]),
        ("test2", "bearing_1", [None]),
    ):
        for t in range(n_snapshots):
            rec = f"{run}/2004.02.{12 + t // 24:02d}.{t % 24:02d}.00.00"
            for b in range(1, 5):
                for ax in axes:
                    ch = f"bearing{b}" + (f"_{ax}" if ax else "")
                    rows.append(
                        dict(
                            signal_id=f"{rec}/{ch}",
                            recording_id=rec,
                            channel=ch,
                            axis=ax or "none",
                            fs=20000,
                            speed_rpm=2000.0,
                            bpfo=7.0921,
                            bpfi=8.9079,
                            bsf=4.1981,
                            ftf=0.4371,
                            run_id=run,
                            time_s=step_s * t,
                            failed_bearing=failed,
                            failure="bearing failed",
                        )
                    )
    # Shuffled, like a real metadata table with no guaranteed order.
    return pd.DataFrame(rows).sample(frac=1, random_state=0).reset_index(drop=True)


def xjtu_like(n_snapshots: int = 30) -> pd.DataFrame:
    rows = []
    for run, rpm, mode in (("Bearing1_1", 2100.0, "outer race"), ("Bearing2_3", 2250.0, "cage")):
        for t in range(1, n_snapshots + 1):
            for ax in ("vertical", "horizontal"):
                rec = f"{run}_{t:04d}"
                rows.append(
                    dict(
                        signal_id=f"{rec}/{ax}",
                        recording_id=rec,
                        channel=ax,
                        axis=ax,
                        fs=25600,
                        speed_rpm=rpm,
                        bpfo=3.08307,
                        bpfi=4.91693,
                        run_id=run,
                        time_s=60.0 * (t - 1),
                        snapshot=t,
                        failure=mode,
                    )
                )
    return pd.DataFrame(rows).sample(frac=1, random_state=1).reset_index(drop=True)


class FakeDataset:
    """Stands in for a bearing_datasets dataset: metadata() and iter_signals()."""

    def __init__(self, meta: pd.DataFrame):
        self.meta = meta
        self._by_id = meta.set_index("signal_id")

    def metadata(self, backend: str = "pandas") -> pd.DataFrame:
        return self.meta

    def iter_signals(self, ids):
        for i in ids:
            r = self._by_id.loc[i]
            seed = abs(hash(i)) % 2**31
            yield i, bearing_signal(fs=float(r.fs), duration=0.1, seed=seed)


@pytest.fixture
def ims_meta():
    return ims_like()


@pytest.fixture
def xjtu_meta():
    return xjtu_like()


@pytest.fixture
def rng():
    return np.random.default_rng(0)
