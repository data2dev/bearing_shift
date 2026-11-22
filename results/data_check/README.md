# Data layer check (protocol v1)

## ims

| machine | bearings | failed | mode | snapshots | duration h | interval s | commissioning | of life | shaft Hz | speed / BPFO source |
|---|---|---|---|---|---|---|---|---|---|---|
| test1 | 4 | test1_b3, test1_b4 | bearing 3 inner race; bearing 4 roller element | 2156 | 827.56 | 600 | 156 | 0.072 | 33.333 | metadata:speed_rpm / metadata:bpfo |
| test2 | 4 | test2_b1 | bearing 1 outer race | 984 | 163.83 | 600 | 144 | 0.146 | 33.333 | metadata:speed_rpm / metadata:bpfo |
| test3 | 4 | test3_b3 | bearing 3 outer race | 6324 | 1073.25 | 600 | 145 | 0.023 | 33.333 | metadata:speed_rpm / metadata:bpfo |

## xjtu_sy

| machine | bearings | failed | mode | snapshots | duration h | interval s | commissioning | of life | shaft Hz | speed / BPFO source |
|---|---|---|---|---|---|---|---|---|---|---|
| Bearing1_1 | 1 | Bearing1_1 | outer race | 123 | 2.03 | 60 | 10 | 0.081 | 35.0 | metadata:speed_rpm / metadata:bpfo |
| Bearing1_2 | 1 | Bearing1_2 | outer race | 161 | 2.67 | 60 | 10 | 0.062 | 35.0 | metadata:speed_rpm / metadata:bpfo |
| Bearing1_3 | 1 | Bearing1_3 | outer race | 158 | 2.62 | 60 | 10 | 0.063 | 35.0 | metadata:speed_rpm / metadata:bpfo |
| Bearing1_4 | 1 | Bearing1_4 | cage | 122 | 2.02 | 60 | 10 | 0.082 | 35.0 | metadata:speed_rpm / metadata:bpfo |
| Bearing1_5 | 1 | Bearing1_5 | inner race; outer race | 52 | 0.85 | 60 | 10 | 0.192 | 35.0 | metadata:speed_rpm / metadata:bpfo |
| Bearing2_1 | 1 | Bearing2_1 | inner race | 491 | 8.17 | 60 | 10 | 0.02 | 37.5 | metadata:speed_rpm / metadata:bpfo |
| Bearing2_2 | 1 | Bearing2_2 | outer race | 161 | 2.67 | 60 | 10 | 0.062 | 37.5 | metadata:speed_rpm / metadata:bpfo |
| Bearing2_3 | 1 | Bearing2_3 | cage | 533 | 8.87 | 60 | 10 | 0.019 | 37.5 | metadata:speed_rpm / metadata:bpfo |
| Bearing2_4 | 1 | Bearing2_4 | outer race | 42 | 0.68 | 60 | 10 | 0.238 | 37.5 | metadata:speed_rpm / metadata:bpfo |
| Bearing2_5 | 1 | Bearing2_5 | outer race | 339 | 5.63 | 60 | 10 | 0.029 | 37.5 | metadata:speed_rpm / metadata:bpfo |
| Bearing3_1 | 1 | Bearing3_1 | outer race | 2538 | 42.28 | 60 | 10 | 0.004 | 40.0 | metadata:speed_rpm / metadata:bpfo |
| Bearing3_2 | 1 | Bearing3_2 | inner race; rolling element; cage; outer race | 2496 | 41.58 | 60 | 10 | 0.004 | 40.0 | metadata:speed_rpm / metadata:bpfo |
| Bearing3_3 | 1 | Bearing3_3 | inner race | 371 | 6.17 | 60 | 10 | 0.027 | 40.0 | metadata:speed_rpm / metadata:bpfo |
| Bearing3_4 | 1 | Bearing3_4 | inner race | 1515 | 25.23 | 60 | 10 | 0.007 | 40.0 | metadata:speed_rpm / metadata:bpfo |
| Bearing3_5 | 1 | Bearing3_5 | outer race | 114 | 1.88 | 60 | 10 | 0.088 | 40.0 | metadata:speed_rpm / metadata:bpfo |

**Status: PASS**

---
Run: https://github.com/data2dev/bearing_shift/actions/runs/45075255105
Commit: 8a6dcb845efbf4096c43cfe3be010ce21c6077e4
Datasets: ims xjtu_sy
