# Contributing

Thanks for your interest. The project is early; see [ROADMAP.md](ROADMAP.md) for what's planned.

## Licence of contributions

By contributing, you agree that your contribution is licensed under the [Apache License 2.0](LICENSE), as described in section 5 of that licence.

Every commit must carry a [Developer Certificate of Origin](https://developercertificate.org/) sign-off, certifying that you wrote the change or otherwise have the right to submit it under this licence:

```bash
git commit -s -m "Your message"
```

This adds a line like `Signed-off-by: Your Name <you@example.com>`.

## Development

All development runs on GitHub Actions; no local machine is needed.

- **CI** (`ci.yml`) runs on every push and pull request: repo hygiene check, ruff lint and format, pytest on Python 3.10–3.13, then builds and smoke-tests the wheel. It uses synthetic data only.
- **Experiments** (`experiment.yml`) are started by hand from the Actions tab → *Experiment* → *Run workflow*. Pick the branch, the experiment and the datasets. The run downloads data from the original sources, runs `experiments/<name>.py`, uploads the results, and opens a PR with them into the branch you picked.

To add an experiment: create `experiments/<name>.py` that accepts `--out DIR --datasets "a b"` and writes only `.json`, `.png` and `README.md` to `DIR`, then add `<name>` to the workflow's `experiment` options.

If you do work locally, the same checks are:

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest
python scripts/check_repo_hygiene.py
```

## Branches and releases

- `main` is protected: no direct pushes. Work on a branch and open a pull request; CI must pass before merging.
- Releases are cut by pushing a tag `vX.Y.Z` that matches `__version__` in `src/bearingshift/__init__.py`. The release workflow re-runs the checks, builds the package and creates a GitHub pre-release. Publishing to PyPI is off until explicitly enabled.

## Ground rules

- **Never commit data.** No signals, no processed features from real datasets, no model weights. Use the synthetic generator for tests.
- **Don't copy code** from projects whose licence is incompatible with Apache 2.0 (for example GPL), or from papers' supplementary code without a clear licence.
- **Splits are by bearing.** Any change to evaluation must keep the leakage test passing.
- **Don't change the evaluation protocol silently.** Protocol changes go in their own PR with a changelog note explaining why.
- **Report negative results.** A model that loses to the physics baseline is a result, not a failure.
