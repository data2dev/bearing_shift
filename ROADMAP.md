# Roadmap

Target: a solid v1 in about 6 weeks, at no cost. **Everything runs on GitHub Actions**: CI on every push, and experiments through the manual `Experiment` workflow, which downloads data from the original sources on the runner and returns only results. Nothing runs on a local PC.

Runner budget per experiment job (free standard runner, public repo): 4 CPU, 16 GB RAM, ~14 GB disk, 6 h. Downloaded datasets are kept in the Actions cache (10 GB per repo) between runs. Anything that won't fit gets split across jobs, one dataset per job.

Each phase ends with a **gate**: a concrete check that must pass before moving on. If a gate fails, we write down why and change course instead of pushing on.

---

## Phase 0: Feasibility check (week 1)

**Question:** does a simple physics indicator visibly rise before failure on real run-to-failure data? If not, there is no ground truth to build a tool on.

- [x] Experiment workflow proven end to end on synthetic data (`experiments/smoke.py`).
- [ ] `experiments/feasibility.py`: load IMS test 2 (outer-race failure on bearing 1) and 2–3 XJTU-SY bearings via `bearing-datasets`, run through the Experiment workflow.
- [ ] Compute envelope-spectrum energy at BPFO / BPFI over each bearing's life.
- [ ] Plot indicator vs. time to failure, one panel per bearing.
- [ ] Write a one-paragraph verdict in the results PR.

**Gate:** the indicator departs from its early-life baseline before failure on at least the IMS bearing and most of the XJTU-SY bearings checked. If it does not, stop and reassess scope before writing any package code.

## Phase 1: Data layer and protocol (week 2)

- [x] Package skeleton: `src/bearingshift/`, `pyproject.toml`, `pytest`, `ruff`, GitHub Actions CI/CD.
- [ ] Thin wrapper over `bearing-datasets`: run-to-failure datasets only, one record per bearing with sampling rate, speed, load and fault orders.
- [ ] Windowing with a bearing ID attached to every window.
- [ ] **Leakage test:** a CI test that fails if any bearing ID appears in both fit and evaluation sets.
- [ ] Freeze the [evaluation protocol](#evaluation-protocol) below in code (config + docstrings) before any model is tuned.
- [x] Synthetic signal generator (healthy + injected impacts at BPFO) for tests and the demo. No real data in the repo or in CI.

**Gate:** CI runs green end-to-end on synthetic data in under 5 minutes; leakage test in place.

## Phase 2: Baseline ladder (weeks 3–4)

- [ ] Rung 1: RMS, kurtosis, crest factor; limits from commissioning window.
- [ ] Rung 2: envelope-spectrum energy at fault orders.
- [ ] Order normalisation (resample spectra to orders of shaft speed).
- [ ] Rung 3: kNN distance to a memory bank of healthy order-normalised features.
- [ ] Rung 4: autoencoder or foundation-model embeddings + kNN (only if rungs 1–3 are done and evaluated).

**Gate:** rungs 1–3 evaluated on all run-to-failure bearings, per-bearing table produced.

## Phase 3: Alarm logic (week 4)

- [ ] Threshold calibration on healthy data to a target false-alarm rate.
- [ ] Persistence rule (k-of-n windows above threshold).
- [ ] Abstention when speed or load is outside the commissioning envelope.
- [ ] Ablation: each of the three switched off, one at a time.

**Gate:** ablation table shows what each component contributes, including if the answer is "nothing".

## Phase 4: Evaluation and honesty (week 5)

- [ ] Main results: lead time and false alarms per 1,000 h, per bearing, with bootstrap CIs over bearings.
- [ ] Cross-machine check: calibrate on one rig, run on another without refitting thresholds.
- [ ] Seeded-fault sanity check (Paderborn real-damage set): does the score separate healthy from damaged?
- [ ] Field-data sanity check (pulp and paper mill dataset), if its licence allows.
- [ ] **"Where it fails"** section: every missed failure and false-alarm cluster, with plots.

**Gate:** every number in the README can be regenerated with one command.

## Phase 5: Package and ship v1 (week 6)

- [ ] CLI: `bearingshift fit`, `bearingshift score`, `bearingshift evaluate`, `bearingshift demo`.
- [ ] `bearingshift demo` runs on synthetic data in about 2 minutes with no downloads.
- [ ] README headline plot and results table.
- [ ] Data-licence check in the CLI: print each dataset's licence and citation before first use; warn on non-commercial licences.
- [ ] Tag `v0.1.0`.

## Later / stretch

- PatchCore / AnomalyDINO on order-normalised spectrograms (rung 5), reported whether it wins or loses.
- Streaming scorer for one-window-at-a-time use.
- Variable-speed datasets with tachometer signals.
- A short write-up of the protocol and results.

## Non-goals

- **Fault-type classification.** PDMBench already covers this well.
- **Remaining-useful-life prediction.** A different problem with a different evaluation.
- **A certified or safety-rated monitoring system.** See [DISCLAIMER.md](DISCLAIMER.md).
- **Redistributing data or pretrained weights.**

---

## Evaluation protocol

Fixed before tuning. Changes require a note in the changelog explaining why.

| Item | Definition |
|---|---|
| Unit of analysis | One physical bearing (one run-to-failure record) |
| Split | By bearing. Thresholds are calibrated only on commissioning windows of the bearing being monitored, or of separate calibration bearings, never on its post-commissioning data |
| Commissioning window | First *N* operating hours of each run, or first *x*% of life for short accelerated tests (values set per dataset in config, before tuning) |
| Failure time *T_f* | End of the run-to-failure record |
| Onset *T_o* | First time the envelope-spectrum indicator at the failed component's fault order exceeds its commissioning mean + *k*σ for *m* consecutive snapshots. Defined once, independently of the models being compared |
| Lead time | *T_f* − (time of first sustained alarm) |
| False alarm | Any sustained alarm before *T_o* |
| False-alarm rate | False alarms per 1,000 operating hours of pre-onset data |
| Missed failure | No sustained alarm before *T_f* |
| Abstention rate | Share of windows where the tool returns "unknown" |
| Reporting | Per bearing, plus median and bootstrap 95% CI across bearings |

Known weaknesses of this protocol, stated up front:

- Onset isn't directly observed; *T_o* is a proxy and favours the physics baseline it is built from. Lead time to *T_f* is therefore the primary metric; detection delay after *T_o* and the false-alarm count are reported alongside it, and a sensitivity check varies *k* and *m*.
- Few independent units (tens of bearings, not thousands). Confidence intervals will be wide.
- Accelerated life tests are not field conditions.
