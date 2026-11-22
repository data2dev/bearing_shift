# BearingShift

[![CI](https://github.com/data2dev/bearing_shift/actions/workflows/ci.yml/badge.svg)](https://github.com/data2dev/bearing_shift/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

**Give it healthy vibration data from a machine. It tells you whether it would have warned you before the bearing failed, and how often it would have cried wolf.**

> **Status: pre-alpha, under active development.** No results yet. Everything below describes the plan; sections marked *(planned)* do not exist yet. See [ROADMAP.md](ROADMAP.md).
>
> **Not a safety system.** BearingShift is research and educational software. Do not use it as the only safeguard for any machine, process or person. Read [DISCLAIMER.md](DISCLAIMER.md).

---

## The problem

Most public bearing-fault projects train a classifier on labelled fault data (CWRU, Paderborn) and report 95–99% accuracy. Two things make those numbers misleading for anyone running a real machine:

1. **Window leakage.** Recordings are chopped into overlapping windows, and windows from the same recording end up on both sides of the train/test split. The model memorises the recording, not the fault.
2. **Wrong question.** A plant doesn't have labelled examples of its own machine failing. It has a few days or weeks of healthy data from commissioning, and it wants to know:
   - *Will this warn me before the bearing fails?* (lead time)
   - *How often will it raise a false alarm?* (false alarms per 1,000 operating hours)
   - *Does it know when it's outside what it has seen?* (abstention)

Accuracy on a held-out split of labelled faults answers none of these.

## What BearingShift does

- **Trains on healthy data only.** Each machine's model is fitted on the first part of its life (the "commissioning window"). No fault labels are used for training.
- **Evaluates on real run-to-failure data.** Bearings that were run until they actually failed (IMS, XJTU-SY, FEMTO/PRONOSTIA, Paderborn run-to-failure), plus one field dataset as a sanity check.
- **Reports deployment metrics, not accuracy.** Detection lead time, false alarms and missed failures, per machine, with confidence intervals.
- **Makes ML beat physics.** Every learned model is compared against an envelope-spectrum health indicator at the bearing's defect frequencies (BPFO, BPFI, BSF), which is what a vibration analyst would check first.
- **Splits by machine, never by window.** Models are fitted only on a machine's commissioning data, and every split goes through a leakage check that CI tests against deliberately leaky splits.
- **Abstains when out of envelope.** If speed or load leaves the range seen during commissioning, the tool says "unknown" instead of guessing.

## Model ladder

Each rung must beat the one below it to justify its complexity.

| Rung | Method | Why it's here |
|---|---|---|
| 1 | RMS, kurtosis and crest factor with limits set from healthy data | What most plants actually run |
| 2 | Envelope-spectrum energy at the bearing's fault orders | Physics baseline |
| 3 | kNN distance to a memory bank of healthy, order-normalised spectral features | Main model: cheap, explainable, no labels |
| 4 | Learned embeddings (autoencoder or time-series foundation model) + kNN | Does representation learning help? |
| 5 | *(experiment)* PatchCore / AnomalyDINO on order-normalised spectrograms | Do image anomaly detectors transfer to vibration? |

The alarm logic matters as much as the model: thresholds calibrated on healthy data to a target false-alarm rate, persistence rules so a single spike doesn't trigger an alarm, and speed normalisation so a change in RPM isn't mistaken for damage.

## Evaluation protocol (summary)

The full protocol is fixed in [ROADMAP.md](ROADMAP.md#evaluation-protocol) before any model is tuned.

- **Unit of analysis:** the machine (one run-to-failure record, with all its bearings). On a shared shaft a failing bearing shakes its neighbours, so alarms are machine-level. Results are reported per machine, never pooled across windows.
- **Commissioning window:** a fixed amount of operating time from the start of each run (IMS 24 h, XJTU-SY 10 min), treated as healthy. Never a fraction of life, which would need the failure time in advance.
- **Failure time:** the end of the run-to-failure record.
- **Onset:** defined independently of any model under test (based on the envelope-spectrum indicator departing from its healthy baseline), so lead time isn't graded by the model being graded.
- **Metrics:** lead time before failure, false alarms per 1,000 operating hours before onset, missed failures, and abstention rate.

## Quickstart *(planned)*

```bash
pip install -e .
bearingshift demo   # runs end-to-end on bundled synthetic data in ~2 minutes, no downloads
```

Real datasets are never bundled. They are downloaded from their original sources, by you, via [`bearing-datasets`](https://github.com/VictorBauler/BearingDatasets), and stay under their own licences.

## Results

**Phase 0 feasibility (passed).** A simple envelope-spectrum indicator departs from its healthy baseline before failure on all 4 failed IMS bearings and 13 of 15 XJTU-SY bearings. It also showed what the protocol must handle: neighbouring bearings on a shared shaft rise together, plain RMS is a strong baseline, and two XJTU-SY failures (a cage failure and an abrupt one) show no physics signature at all. Details: [`results/feasibility/`](results/feasibility/README.md) and [ROADMAP.md](ROADMAP.md#phase-0-findings-and-what-they-changed).

Main results (lead time and false alarms per machine, against RMS and the physics baseline) come in Phase 4, with a **"Where it fails"** section listing every missed failure and false alarm.

## Data and licensing

| What | Licence |
|---|---|
| BearingShift source code | [Apache License 2.0](LICENSE) |
| Datasets | Each keeps its **own** licence. None are redistributed here. See [DATA_LICENSES.md](DATA_LICENSES.md). |
| Pretrained weights | Not distributed. Models are trained locally from data you download yourself. |

Some datasets used here are **non-commercial only** (for example Paderborn, CC BY-NC 4.0). The Apache licence on this code does **not** grant you any rights to the data. Check [DATA_LICENSES.md](DATA_LICENSES.md) before using BearingShift on anything other than research.

## Related work

BearingShift builds on, and does not replace:

- [**bearing-datasets**](https://github.com/VictorBauler/BearingDatasets): unified loaders, bearing IDs and fault-frequency metadata. BearingShift uses it as its data layer.
- [**PDMBench**](https://github.com/zshuai8/PDMBench): supervised fault-classification benchmark across many datasets and models, including cross-condition evaluation.

BearingShift asks a different question: label-free detection from healthy commissioning data, evaluated on run-to-failure data with deployment metrics. Onset detection on IMS and FEMTO has its own academic literature; the contribution here is a packaged, leakage-free, honestly evaluated tool, not a new concept.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Contributions are accepted under the Apache 2.0 licence with a DCO sign-off.

## Licence

Copyright 2026 data2dev and BearingShift contributors.

Licensed under the [Apache License, Version 2.0](LICENSE). The software is provided **"AS IS", without warranties or conditions of any kind**, and the authors are not liable for any damages arising from its use; see sections 7 and 8 of the licence and [DISCLAIMER.md](DISCLAIMER.md).
