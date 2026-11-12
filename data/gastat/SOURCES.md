# GASTAT Labour Force Survey (chapter A)

The analytical tables in this folder are **slim outputs** of the sister project [ksa-labour-market-sql](https://github.com/amirator/ksa-labour-market-sql), which runs the DuckDB SQL (CTEs and window functions) and the reconciliation checks.

| File | What it is | Period |
|---|---|---|
| `fct_employment_national.csv` | National LFS employed counts and Saudi share, with the 2020-Q4 to 2021-Q1 break visible | 2016-Q2 – 2024-Q4 |
| `fct_employment_region.csv` | Regional Saudi share and ranks (13 regions) | 2016-Q2 – 2024-Q4 |
| `fct_unemployment.csv` | Unemployment and participation by nationality and sex | 2021-Q1 – 2026-Q2 |
| `fct_youth.csv` | Saudi (and other) youth 15-24 unemployment vs all-ages | 2021-Q1 – 2026-Q2 |
| `fct_wages.csv` | Average monthly wage, nominal SAR: all national quarters, plus the latest regional quarter | employment window to 2024-Q4 |

- Official source: General Authority for Statistics (GASTAT), Labour Force Survey. [stats.gov.sa](https://www.stats.gov.sa/).
- The tidy reprints used upstream were published by [DataPulse](https://datapulseactive.com/en/data/open/) (versions 2026-09-30 and 2026-10-01). They are **not** official GASTAT files and not an endorsement by GASTAT.
- Reuse: [GASTAT data use policy](https://www.stats.gov.sa/en/use-policy) (the Arabic text governs). This project does not use the GASTAT logo.
- These are **household-survey estimates of all employment**, not GOSI contribution counts and **not Nitaqat** (private-sector Saudization) scores. This project reports an "LFS Saudi share" and never calls it a Saudization or Nitaqat ratio.
- A single-quarter **break from 2020-Q4 to 2021-Q1** cuts the national Saudi share by about 10.5 percentage points (Saudi employed −1.73 million, non-Saudi +1.19 million). That is treated as a methodology or source change, not as a one-quarter labour-market result. See the sister SQL project for the full discussion and the quality-check gaps (nationality and region totals reconcile exactly; the two unemployment files differ by at most 0.05 pp of rounding).
