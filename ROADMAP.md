# Roadmap

Target: a solid v1 in about 6 weeks, at no cost. **Everything runs on GitHub Actions**: CI on every push, and experiments through the manual `Experiment` workflow, which downloads data from the original sources on the runner and returns only results. Nothing runs on a local PC.

Runner budget per experiment job (free standard runner, public repo): 4 CPU, 16 GB RAM, ~14 GB disk, 6 h. Downloaded datasets are kept in the Actions cache (10 GB per repo) between runs. Anything that won't fit gets split across jobs, one dataset per job.

Each phase ends with a **gate**: a concrete check that must pass before moving on. If a gate fails, we write down why and change course instead of pushing on.

---

## Phase 0: Feasibility check (week 1)

**Question:** does a simple physics indicator visibly rise before failure on real run-to-failure data? If not, there is no ground truth to build a tool on.

- [x] Experiment workflow proven end to end on synthetic data (`experiments/smoke.py`).
- [x] `experiments/feasibility.py`: all IMS tests and all 15 XJTU-SY bearings via `bearing-datasets`, run through the Experiment workflow.
- [x] Compute envelope-spectrum energy at BPFO / BPFI over each bearing's life.
- [x] Plot indicator vs. time to failure, one panel per bearing.
- [x] Verdict recorded: **pass** (2026-11-22). Results: [`results/feasibility/`](results/feasibility/README.md).

**Gate:** the indicator departs from its early-life baseline before failure on at least the IMS bearing and most of the XJTU-SY bearings checked. If it does not, stop and reassess scope before writing any package code.

### Phase 0 findings and what they changed

| Finding | Change |
|---|---|
| IMS test 2 bearing 1 (outer race) departs at 72% of life; all 4 failed IMS bearings and 13/15 XJTU-SY bearings depart before failure. | Gate passed. |
| On IMS, 7/8 bearings that *survived* also depart in the last 2–5% of life: four bearings share one shaft and one housing, so the failing one shakes its neighbours. | **Unit of analysis is the machine** (`run_id`), not the bearing. IMS counts as 3 machines, XJTU-SY as 15. Alarms are machine-level; which bearing is failing is not claimed. |
| RMS often departs as early as the envelope indicator (IMS test 2: 55% vs 72% of life). | RMS is reported in **every** results table, and a model only counts as an improvement if it beats RMS, not just the physics indicator. |
| BPFO and BPFI energies usually rise together, including on outer-race failures. | The envelope indicator is treated as a generic impact indicator. **No fault-location diagnosis is claimed.** Onset uses the max over defect orders. |
| Phase 0 used "first 20% of life" as commissioning, which needs the failure time in advance (future information). | **Commissioning is a fixed amount of operating time** per dataset, never a fraction of life. |
| XJTU-SY Bearing1_4 (cage failure) and Bearing3_5 (abrupt failure) show no physics departure at all. | Both are listed up front in "Where it fails"; onset is undefined for them (see protocol). |

## Phase 1: Data layer and protocol (week 2)

- [x] Package skeleton: `src/bearingshift/`, `pyproject.toml`, `pytest`, `ruff`, GitHub Actions CI/CD.
- [x] Thin wrapper over `bearing-datasets`: run-to-failure datasets only, one record per machine with its bearings, sampling rate, speed, fault orders and failure outcome (`bearingshift.data`).
- [x] Windowing with machine and bearing IDs attached to every window (`bearingshift.windowing`).
- [x] **Leakage checks** (`bearingshift.splits`), tested in CI: fails if a machine is on both sides of a cross-machine split, or if any fitted window from a machine is not strictly inside that machine's commissioning period.
- [x] Freeze the [evaluation protocol](#evaluation-protocol) below in code (`bearingshift.protocol`) before any model is tuned.
- [x] Synthetic signal generator (healthy + injected impacts at BPFO) for tests and the demo. No real data in the repo or in CI.

**Gate:** CI runs green end-to-end on synthetic data in under 5 minutes; leakage test in place.

## Phase 2: Baseline ladder (weeks 3–4)

- [ ] Rung 1: RMS, kurtosis, crest factor; limits from commissioning window. RMS stays in every later table.
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

- [ ] Main results: lead time and false alarms, per machine, with bootstrap CIs over machines.
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
- **Saying which bearing or which component failed.** Phase 0 showed neighbouring bearings and different defect orders rise together.
- **A certified or safety-rated monitoring system.** See [DISCLAIMER.md](DISCLAIMER.md).
- **Redistributing data or pretrained weights.**

---

## Evaluation protocol

Frozen in code as `bearingshift.protocol.PROTOCOL` (version 1). Changes bump the version and need a changelog note explaining why.

| Item | Definition |
|---|---|
| Unit of analysis | One **machine**: one run-to-failure record (`run_id`), with all its bearings. IMS = 3 machines (4 bearings each), XJTU-SY = 15 machines (1 bearing each) |
| Split | By machine. Per-machine mode: fit only on that machine's commissioning windows. Cross-machine mode: fit and calibration machines are disjoint from evaluation machines |
| Commissioning window | A fixed amount of operating time from the start of the run, set per dataset: IMS 24 h, XJTU-SY 10 min (accelerated tests). Never a fraction of life, which would need the failure time in advance |
| Failure time *T_f* | End of the run-to-failure record |
| Onset *T_o* | First snapshot where the max over defect orders (BPFO, BPFI) of the envelope indicator exceeds its commissioning mean + 5σ for 3 consecutive snapshots, on any bearing of the machine. Computed once by the protocol, never by the model under test. **Undefined** if this never happens |
| Lead time | *T_f* − (time of first sustained alarm) |
| False alarm | Any sustained alarm before *T_o*. Not counted for machines with undefined onset; those only report detection and lead time |
| False-alarm rate | False alarms per machine, and per 1,000 operating hours of pre-onset data (the latter is only meaningful for IMS: XJTU-SY lives are hours long) |
| Missed failure | No sustained alarm before *T_f* |
| Abstention rate | Share of windows where the tool returns "unknown" |
| Baselines in every table | RMS (rung 1) and the envelope indicator (rung 2) |
| Reporting | Per machine, plus median and bootstrap 95% CI across machines |

Known weaknesses of this protocol, stated up front:

- Onset isn't directly observed; *T_o* is a proxy and favours the physics baseline it is built from. Lead time to *T_f* is therefore the primary metric; detection delay after *T_o* and the false-alarm count are reported alongside it, and a sensitivity check varies *k* and *m*.
- The commissioning durations were set after Phase 0, which plotted the envelope indicator over life; they were not tuned on any model's lead time or false alarms.
- Few independent units (18 machines). Confidence intervals will be wide.
- Accelerated life tests are not field conditions.

### Protocol changelog

- **v1 (2026-11-22):** unit of analysis changed from bearing to machine; commissioning changed from fraction of life to fixed operating time; onset uses the max over defect orders and may be undefined. Reasons: [Phase 0 findings](#phase-0-findings-and-what-they-changed).
