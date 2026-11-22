# Data licences

**This repository contains no datasets.** BearingShift downloads data from the original sources through [`bearing-datasets`](https://github.com/VictorBauler/BearingDatasets) (MIT-licensed code; it also distributes no data). Each dataset keeps the licence set by its authors. The Apache 2.0 licence on BearingShift's code gives you **no rights** to any dataset.

Before using a dataset, run `bearing-datasets info <name>` and check the original source. The table below is a best-effort summary, last checked **2026-11-22**. It is not legal advice, and licences can change; the source is authoritative.

| Dataset | Used for | Licence / terms (as found) | Commercial use? | Cite |
|---|---|---|---|---|
| IMS (Univ. of Cincinnati, via NASA PCoE) | Run-to-failure, main eval | Listed on data.gov as a U.S. Government Work. NASA: data used at the user's own risk | Appears permitted; verify | Lee, Qiu, Yu, Lin & Rexnord Technical Services (2007), "Bearing Data Set", NASA Prognostics Data Repository |
| XJTU-SY | Run-to-failure, main eval | Publicly released by the authors; some third parties report CC BY 4.0. **Verify at source** | Unclear; verify | Wang, Lei, Li & Li (2020), *IEEE Trans. Reliability* 69(1):401–412 |
| FEMTO / PRONOSTIA (IEEE PHM 2012) | Run-to-failure, main eval | **No licence stated** | Unclear; ask the authors | Nectoux et al. (2012), "PRONOSTIA: An experimental platform for bearings accelerated degradation tests", IEEE PHM |
| Paderborn (KAt DataCenter), incl. run-to-failure | Run-to-failure and seeded/real-damage checks | **CC BY-NC 4.0** | **No**, without the authors' permission | Lessmeier et al. (2016), PHM Society European Conference |
| CWRU Bearing Data Center | Seeded-fault sanity check only | **No licence stated** | Unclear; ask the authors | Case Western Reserve University Bearing Data Center |
| Wind turbine HSS bearing (`wt_hss`) | Optional field check | **CC BY-NC-SA** | **No** | See `bearing-datasets info wt_hss` |
| Pulp and paper mill field data (`sca`) | Optional field check | No licence stated in `bearing-datasets` listing | Unclear; verify | See `bearing-datasets info sca` |

## Rules this project follows

1. **No raw or processed data is committed.** `.gitignore` blocks common data and model formats; CI uses synthetic data only.
2. **No pretrained weights are distributed.** Models trained on non-commercial data could carry those restrictions, so users train locally.
3. **Results only.** The repository may contain aggregate results (metrics, plots) derived from the datasets, with citations. It never contains the signals themselves.
4. **"No licence stated" means "all rights reserved".** We download, use for research and cite; we never rehost.
5. **Non-commercial means non-commercial.** If you use BearingShift commercially, use only datasets whose licences allow it, or your own data.

If you are a dataset author and want something here corrected or removed, please open an issue.
