"""Fail if the repository tracks data, model weights, oversized files, or lacks licence files.

Run from the repository root: ``python scripts/check_repo_hygiene.py``.
Enforces the rules in DATA_LICENSES.md: no datasets and no pretrained weights in git.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MAX_BYTES = 1_000_000  # 1 MB

FORBIDDEN_SUFFIXES = {
    # data
    ".mat",
    ".csv",
    ".tdms",
    ".npy",
    ".npz",
    ".h5",
    ".hdf5",
    ".parquet",
    ".feather",
    ".zip",
    ".rar",
    ".7z",
    ".tar",
    ".gz",
    ".wav",
    ".flac",
    # model weights / artefacts
    ".pt",
    ".pth",
    ".ckpt",
    ".onnx",
    ".pkl",
    ".joblib",
    ".safetensors",
}
ALLOWED_PATHS_PREFIX = ("tests/fixtures/",)
REQUIRED_FILES = ("LICENSE", "NOTICE", "DISCLAIMER.md", "DATA_LICENSES.md")


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], check=True, capture_output=True, text=True
    ).stdout
    return [p for p in out.split("\0") if p]


def main() -> int:
    problems: list[str] = []

    for rel in tracked_files():
        path = Path(rel)
        if not path.exists():
            continue
        suffix = path.suffix.lower()
        if suffix in FORBIDDEN_SUFFIXES and not rel.startswith(ALLOWED_PATHS_PREFIX):
            problems.append(f"forbidden file type (data/weights): {rel}")
        size = path.stat().st_size
        if size > MAX_BYTES:
            problems.append(f"file larger than {MAX_BYTES // 1000} kB ({size} bytes): {rel}")

    for name in REQUIRED_FILES:
        if not Path(name).is_file():
            problems.append(f"required file missing: {name}")

    if problems:
        print("Repository hygiene check failed:")
        for p in problems:
            print(f"  - {p}")
        print("See DATA_LICENSES.md: datasets and model weights must never be committed.")
        return 1
    print("Repository hygiene check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
