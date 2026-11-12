# Power BI pack — two unconnected chapters

Power BI Desktop cannot run on the Linux machine that built this repository, so **there is no `.pbix` here**. A `.pbix` will be added only if it is later built on a Windows machine. The Python dashboards in `reports/` are rendered from the same model CSVs this pack loads.

## What to load

Set the `FolderPath` parameter (see `parameters.m`) to the `powerbi/model` folder, then run the queries in `queries/`. Each query is a `Csv.Document` load with explicit types.

**Chapter A (GASTAT LFS)** — relate these, and only these:

- `dim_quarter` (1) ← (*) `fct_employment_national`, `fct_employment_region`, `fct_unemployment`, `fct_youth`, `fct_wages` on `period_start`
- `dim_region` (1) ← (*) `fct_employment_region` (and the regional rows of `fct_wages`) on `region_name`
- `dim_nationality` (1) ← (*) `fct_unemployment`, `fct_youth`, `fct_wages` on `nationality`

Filter employment and wage visuals to a single quarter (or use the "Latest" DAX measures). Summing employed counts across quarters would double-count people.

**Chapter B (fictional IBM sample)** — relate these, and only these:

- `dim_department` (1) ← (*) `fct_employee` on `Department`
- `dim_job_role` (1) ← (*) `fct_employee` on `JobRole`

`fct_employee` is at employee grain (`EmployeeNumber`). Use the DAX measures in the "Chapter B" section of `measures.dax`. The file has **no nationality column**.

## Do not join the two halves

There is no valid key between a GASTAT region-quarter and an invented IBM employee. Creating a relationship, a "Saudization" measure on `fct_employee`, or a single "company" scorecard that mixes LFS headcount with IBM attrition would be a fabrication. `model/DO_NOT_JOIN.txt` and `model_diagram.png` repeat this.

## Measures

`measures.dax` is a text list of measures, not an executed model. Chapter A measures use the LFS facts and are named "LFS Saudi Share", never "Saudization" or "Nitaqat". Chapter B measures use `fct_employee` and are clearly labelled as the fictional sample.

## Incremental refresh

These are a small frozen snapshot (35 employment quarters, 1,470 employees). Incremental refresh is not configured and is not needed.
