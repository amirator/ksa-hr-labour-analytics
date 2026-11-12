#!/usr/bin/env python3
"""Build model CSVs, KPIs, two-page dashboards and the README.

Two chapters, never joined:
  A. GASTAT Labour Force Survey (official KSA statistics)
  B. IBM HR Attrition sample (fictional, 1,470 rows)
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from textwrap import fill

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.gridspec import GridSpec

ROOT = Path(__file__).resolve().parent
DATA_G = ROOT / "data" / "gastat"
DATA_I = ROOT / "data" / "ibm"
MODEL = ROOT / "powerbi" / "model"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"

NAVY = "#1F2A44"
BLUE = "#2E6B8A"
ORANGE = "#C56A1A"
GREY = "#5A5A5A"
PALE = "#E8F0F6"
WARN = "#F8E6D0"
IBM_SHA = "a5c31e38bd7fafc9bc333884eb181b06b41b8e5e488e8f7ccb27199fb3be7659"


def r2(x):
    return None if pd.isna(x) else round(float(x), 2)


def r1(x):
    return None if pd.isna(x) else round(float(x), 1)


def load():
    emp = pd.read_csv(DATA_G / "fct_employment_national.csv", parse_dates=["period_start"])
    reg = pd.read_csv(DATA_G / "fct_employment_region.csv", parse_dates=["period_start"])
    unemp = pd.read_csv(DATA_G / "fct_unemployment.csv", parse_dates=["period_start"])
    youth = pd.read_csv(DATA_G / "fct_youth.csv", parse_dates=["period_start"])
    wages = pd.read_csv(DATA_G / "fct_wages.csv", parse_dates=["period_start"])
    ibm = pd.read_csv(DATA_I / "emp_attrition.csv")
    digest = hashlib.sha256((DATA_I / "emp_attrition.csv").read_bytes()).hexdigest()
    if digest != IBM_SHA:
        raise SystemExit(f"IBM file checksum changed: {digest}")
    return emp, reg, unemp, youth, wages, ibm, digest


def build_model(emp, reg, unemp, youth, wages, ibm):
    """Star-schema CSVs for Power BI. Two unconnected model halves."""
    MODEL.mkdir(parents=True, exist_ok=True)

    quarters = pd.concat(
        [
            emp[["period_start", "quarter", "year"]],
            unemp[["period_start", "quarter", "year"]],
        ]
    ).drop_duplicates().sort_values("period_start")
    quarters["quarter_num"] = quarters["quarter"].str[-1].astype(int)
    quarters.to_csv(MODEL / "dim_quarter.csv", index=False)

    dim_region = (
        reg[["region_name"]]
        .drop_duplicates()
        .sort_values("region_name")
        .reset_index(drop=True)
    )
    dim_region.insert(0, "region_id", range(1, len(dim_region) + 1))
    dim_region.to_csv(MODEL / "dim_region.csv", index=False)

    pd.DataFrame(
        {
            "nationality": ["saudi", "non_saudi", "total"],
            "label": ["Saudi", "Non-Saudi", "Total"],
        }
    ).to_csv(MODEL / "dim_nationality.csv", index=False)

    emp.to_csv(MODEL / "fct_employment_national.csv", index=False)
    reg.to_csv(MODEL / "fct_employment_region.csv", index=False)
    unemp.to_csv(MODEL / "fct_unemployment.csv", index=False)
    youth.to_csv(MODEL / "fct_youth.csv", index=False)
    wages.to_csv(MODEL / "fct_wages.csv", index=False)

    # IBM employee grain, with analysis bands. No nationality column is added.
    out = ibm.copy()
    out["AttritionFlag"] = (out["Attrition"] == "Yes").astype(int)
    out["TenureBand"] = pd.cut(
        out["YearsAtCompany"],
        bins=[-0.1, 1, 3, 5, 10, 50],
        labels=["0-1 years", "2-3 years", "4-5 years", "6-10 years", "11+ years"],
    )
    out["IncomeQuartile"] = pd.qcut(
        out["MonthlyIncome"],
        4,
        labels=["Q1 lowest", "Q2", "Q3", "Q4 highest"],
    )
    out.to_csv(MODEL / "fct_employee.csv", index=False)

    dim_dept = (
        out[["Department"]].drop_duplicates().sort_values("Department").reset_index(drop=True)
    )
    dim_dept.insert(0, "department_id", range(1, len(dim_dept) + 1))
    dim_dept.to_csv(MODEL / "dim_department.csv", index=False)

    dim_role = (
        out[["JobRole"]].drop_duplicates().sort_values("JobRole").reset_index(drop=True)
    )
    dim_role.insert(0, "job_role_id", range(1, len(dim_role) + 1))
    dim_role.to_csv(MODEL / "dim_job_role.csv", index=False)

    # A one-row reminder that lives next to the model files.
    (MODEL / "DO_NOT_JOIN.txt").write_text(
        "The GASTAT facts (fct_employment_*, fct_unemployment, fct_youth, fct_wages) "
        "and the IBM fact (fct_employee) must not be related. They are two chapters "
        "in one repository, not one company. There is no nationality field on "
        "fct_employee, and no employee identifier on the GASTAT facts.\n"
    )


def kpis(emp, reg, unemp, youth, wages, ibm, digest) -> dict:
    first, last = emp.iloc[0], emp.iloc[-1]
    pre = emp[emp.quarter == "2020-Q4"].iloc[0]
    post = emp[emp.quarter == "2021-Q1"].iloc[0]
    last_reg = reg[reg.quarter == last.quarter].sort_values("saudi_share")
    sa = unemp[unemp.nationality == "saudi"].sort_values("period_start")
    sa_last = sa.iloc[-1]
    sa_first = sa.iloc[0]
    yt = youth[(youth.nationality == "saudi") & (youth.sex == "total")].sort_values("period_start")
    yt_last = yt.iloc[-1]
    wq = wages[(wages.is_national) & (wages.quarter == last.quarter)]

    def w(nat, sex):
        return float(wq[(wq.nationality == nat) & (wq.sex == sex)].wage.iloc[0])

    ibm = ibm.copy()
    ibm["left"] = ibm.Attrition.eq("Yes")
    n = len(ibm)
    leavers = int(ibm.left.sum())
    ot_yes = ibm[ibm.OverTime == "Yes"]
    ot_no = ibm[ibm.OverTime == "No"]
    ibm["TenureBand"] = pd.cut(
        ibm.YearsAtCompany,
        bins=[-0.1, 1, 3, 5, 10, 50],
        labels=["0-1 years", "2-3 years", "4-5 years", "6-10 years", "11+ years"],
    )
    ibm["IncomeQuartile"] = pd.qcut(
        ibm.MonthlyIncome, 4, labels=["Q1 lowest", "Q2", "Q3", "Q4 highest"]
    )
    t0 = ibm[ibm.TenureBand == "0-1 years"]
    q1 = ibm[ibm.IncomeQuartile == "Q1 lowest"]
    sales = ibm[ibm.JobRole == "Sales Representative"]
    single = ibm[ibm.MaritalStatus == "Single"]
    travel = ibm[ibm.BusinessTravel == "Travel_Frequently"]

    def rate(frame):
        return r2(100 * frame.left.mean()), int(frame.left.sum()), int(len(frame))

    dept_rates = []
    for dept, g in ibm.groupby("Department"):
        rt, lv, nn = rate(g)
        dept_rates.append({"department": dept, "rate_pct": rt, "leavers": lv, "n": nn})
    dept_rates.sort(key=lambda r: -r["rate_pct"])

    role_rates = []
    for role, g in ibm.groupby("JobRole"):
        rt, lv, nn = rate(g)
        role_rates.append({"job_role": role, "rate_pct": rt, "leavers": lv, "n": nn})
    role_rates.sort(key=lambda r: -r["rate_pct"])

    tenure_rates = []
    for band, g in ibm.groupby("TenureBand", observed=True):
        rt, lv, nn = rate(g)
        tenure_rates.append({"band": str(band), "rate_pct": rt, "leavers": lv, "n": nn})

    income_rates = []
    for band, g in ibm.groupby("IncomeQuartile", observed=True):
        rt, lv, nn = rate(g)
        income_rates.append(
            {
                "band": str(band),
                "rate_pct": rt,
                "leavers": lv,
                "n": nn,
                "min": int(g.MonthlyIncome.min()),
                "max": int(g.MonthlyIncome.max()),
                "median": int(g.MonthlyIncome.median()),
            }
        )

    k = {
        "first_quarter": first.quarter,
        "last_employment_quarter": last.quarter,
        "last_unemp_quarter": sa_last.quarter,
        "employed_first": int(first.total),
        "employed_last": int(last.total),
        "saudi_employed_first": int(first.saudi),
        "saudi_employed_last": int(last.saudi),
        "nonsaudi_employed_last": int(last.non_saudi),
        "saudi_share_first_pct": r2(first.saudi_share * 100),
        "saudi_share_last_pct": r2(last.saudi_share * 100),
        "saudi_share_change_pp": r2((last.saudi_share - first.saudi_share) * 100),
        "break_from": "2020-Q4",
        "break_to": "2021-Q1",
        "break_share_from_pct": r2(pre.saudi_share * 100),
        "break_share_to_pct": r2(post.saudi_share * 100),
        "break_share_pp": r2((post.saudi_share - pre.saudi_share) * 100),
        "break_saudi_change": int(post.saudi - pre.saudi),
        "break_nonsaudi_change": int(post.non_saudi - pre.non_saudi),
        "share_postbreak_change_pp": r2((last.saudi_share - post.saudi_share) * 100),
        "top_region": last_reg.iloc[-1].region_name,
        "top_region_share_pct": r2(last_reg.iloc[-1].saudi_share * 100),
        "bottom_region": last_reg.iloc[0].region_name,
        "bottom_region_share_pct": r2(last_reg.iloc[0].saudi_share * 100),
        "saudi_unemp_pct": r2(sa_last.unemp_total),
        "saudi_unemp_female_pct": r2(sa_last.unemp_female),
        "saudi_unemp_male_pct": r2(sa_last.unemp_male),
        "saudi_unemp_gap_pp": r2(sa_last.unemp_gender_gap_pp),
        "saudi_unemp_yoy_pp": r2(sa_last.unemp_yoy_pp),
        "saudi_unemp_first_pct": r2(sa_first.unemp_total),
        "saudi_female_part_pct": r2(sa_last.part_female),
        "wage_quarter": last.quarter,
        "wage_saudi": r1(w("saudi", "total")),
        "wage_nonsaudi": r1(w("non_saudi", "total")),
        "wage_ratio": r2(w("saudi", "total") / w("non_saudi", "total")),
        "wage_saudi_male": r1(w("saudi", "male")),
        "wage_saudi_female": r1(w("saudi", "female")),
        "youth_saudi_pct": r2(yt_last.unemp_youth),
        "youth_saudi_female_pct": r2(youth[(youth.nationality == "saudi") & (youth.sex == "female")].iloc[-1].unemp_youth),
        "youth_gap_pp": r2(yt_last.youth_gap_pp),
        "youth_vs_first_pp": r2(yt_last.youth_vs_first_pp),
        "ibm_sha256": digest,
        "ibm_n": n,
        "ibm_leavers": leavers,
        "ibm_stayers": n - leavers,
        "ibm_attrition_pct": r2(100 * leavers / n),
        "ibm_ot_yes_pct": rate(ot_yes)[0],
        "ibm_ot_yes_leavers": rate(ot_yes)[1],
        "ibm_ot_yes_n": rate(ot_yes)[2],
        "ibm_ot_no_pct": rate(ot_no)[0],
        "ibm_ot_no_leavers": rate(ot_no)[1],
        "ibm_ot_no_n": rate(ot_no)[2],
        "ibm_ot_lift": r2(ot_yes.left.mean() / ot_no.left.mean()),
        "ibm_ot_share_of_leavers_pct": r2(100 * ot_yes.left.sum() / leavers),
        "ibm_tenure0_pct": rate(t0)[0],
        "ibm_tenure0_n": rate(t0)[2],
        "ibm_income_q1_pct": rate(q1)[0],
        "ibm_income_q1_n": rate(q1)[2],
        "ibm_income_q1_max": int(q1.MonthlyIncome.max()),
        "ibm_sales_rep_pct": rate(sales)[0],
        "ibm_sales_rep_n": rate(sales)[2],
        "ibm_single_pct": rate(single)[0],
        "ibm_single_n": rate(single)[2],
        "ibm_travel_pct": rate(travel)[0],
        "ibm_travel_n": rate(travel)[2],
        "ibm_leaver_income_median": int(ibm.loc[ibm.left, "MonthlyIncome"].median()),
        "ibm_stayer_income_median": int(ibm.loc[~ibm.left, "MonthlyIncome"].median()),
        "ibm_leaver_income_mean": r1(ibm.loc[ibm.left, "MonthlyIncome"].mean()),
        "ibm_stayer_income_mean": r1(ibm.loc[~ibm.left, "MonthlyIncome"].mean()),
        "ibm_leaver_tenure_median": r1(ibm.loc[ibm.left, "YearsAtCompany"].median()),
        "ibm_stayer_tenure_median": r1(ibm.loc[~ibm.left, "YearsAtCompany"].median()),
        "ibm_leaver_age_median": r1(ibm.loc[ibm.left, "Age"].median()),
        "ibm_stayer_age_median": r1(ibm.loc[~ibm.left, "Age"].median()),
        "ibm_has_nationality": "Nationality" in ibm.columns or "nationality" in ibm.columns,
        "dept_rates": dept_rates,
        "role_rates": role_rates,
        "tenure_rates": tenure_rates,
        "income_rates": income_rates,
        "honesty": [
            "Portfolio project on public data, not a client engagement and not employment.",
            "Chapter A is GASTAT Labour Force Survey household-survey estimates, not GOSI and not Nitaqat.",
            "Chapter B is a fictional IBM sample of 1,470 invented employees, not a Saudi workforce.",
            "The two chapters must not be joined. A Saudization ratio is not computed from either file.",
            "No .pbix is in this repository: Power BI Desktop is not available on Linux. The pack ships Power Query M, DAX, a star-schema diagram and Python-rendered dashboards from the same model.",
        ],
    }
    return k


def _cards(cax, cards):
    cax.set_xlim(0, len(cards))
    cax.set_ylim(0, 1)
    cax.axis("off")
    for i, (lab, val, sub) in enumerate(cards):
        cax.add_patch(
            plt.Rectangle(
                (i + 0.05, 0.06), 0.90, 0.88,
                facecolor=PALE, edgecolor=NAVY, lw=0.8, clip_on=False,
            )
        )
        cax.text(i + 0.5, 0.82, lab, ha="center", va="top", fontsize=6.6, color=GREY)
        cax.text(i + 0.5, 0.46, val, ha="center", va="center", fontsize=14,
                 fontweight="bold", color=NAVY)
        cax.text(i + 0.5, 0.16, sub, ha="center", va="center", fontsize=6.2, color="#1a1a1a")


def _style(ax, title):
    ax.set_title(title, loc="left", fontsize=9.2, color=NAVY, pad=6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="#EEE", lw=0.6)


def chart_lfs(emp, reg, unemp, youth, k) -> plt.Figure:
    fig = plt.figure(figsize=(14.2, 10.0), facecolor="white")
    fig.text(
        0.07, 0.975,
        "Chapter A  ·  KSA labour market headcount and LFS Saudi share (GASTAT)",
        fontsize=15.5, fontweight="bold", color=NAVY, va="top",
    )
    finding = (
        f"A 2020-Q4 to 2021-Q1 break cuts the LFS Saudi share from "
        f"{k['break_share_from_pct']:.1f}% to {k['break_share_to_pct']:.1f}% "
        f"({k['break_share_pp']:+.1f} pp; Saudi employed {k['break_saudi_change']/1e6:+.2f} m, "
        f"non-Saudi {k['break_nonsaudi_change']/1e6:+.2f} m). That is treated as a methodology "
        f"or source change, not a one-quarter result. After the break the share is in a 34-38% "
        f"band and is {k['saudi_share_last_pct']:.1f}% in {k['last_employment_quarter']} "
        f"({k['share_postbreak_change_pp']:+.1f} pp from 2021-Q1). This is the LFS share of all "
        f"employment, not a Nitaqat or Saudization score."
    )
    rec = (
        f"Recommendation: Keep the LFS Saudi share on a separate scorecard from private-sector "
        f"Nitaqat. In {k['last_employment_quarter']} the regional share ranged from "
        f"{k['bottom_region']} {k['bottom_region_share_pct']:.1f}% to {k['top_region']} "
        f"{k['top_region_share_pct']:.1f}%. In {k['last_unemp_quarter']} Saudi unemployment "
        f"was {k['saudi_unemp_pct']:.2f}% (women {k['saudi_unemp_female_pct']:.2f}%, "
        f"youth 15-24 {k['youth_saudi_pct']:.2f}%) — those rates are the operational gaps "
        f"an HR-GR briefing should watch. Do not combine these figures with the IBM sample "
        f"on the next page."
    )
    fig.text(0.07, 0.935, fill(finding, 155), fontsize=8.3, color="#1a1a1a", va="top")
    fig.text(0.07, 0.872, fill(rec, 155), fontsize=8.1, color="#1a1a1a", va="top", style="italic")

    gs = GridSpec(
        3, 2, figure=fig,
        left=0.11, right=0.97, top=0.82, bottom=0.065,
        hspace=0.42, wspace=0.28,
        height_ratios=[0.52, 1.15, 1.15],
    )
    cards = [
        (f"LFS Saudi share  {k['last_employment_quarter']}",
         f"{k['saudi_share_last_pct']:.1f}%",
         f"{k['share_postbreak_change_pp']:+.1f} pp after the 2021-Q1 break"),
        ("Employed (LFS)",
         f"{k['employed_last']/1e6:.2f} m",
         f"Saudi {k['saudi_employed_last']/1e6:.2f} m"),
        (f"Saudi unemployment  {k['last_unemp_quarter']}",
         f"{k['saudi_unemp_pct']:.2f}%",
         f"Women {k['saudi_unemp_female_pct']:.2f}%"),
        ("Saudi youth (15-24)",
         f"{k['youth_saudi_pct']:.1f}%",
         f"{k['youth_vs_first_pp']:+.1f} pp vs first quarter"),
        (f"Avg monthly wage  {k['wage_quarter']}",
         f"{k['wage_saudi']:,.0f}",
         f"Saudi SAR; non-Saudi {k['wage_nonsaudi']:,.0f}"),
    ]
    _cards(fig.add_subplot(gs[0, :]), cards)

    ax = fig.add_subplot(gs[1, 0])
    ax.plot(emp.period_start, emp.saudi_share * 100, color=NAVY, lw=2.2)
    br = emp[emp.quarter == "2021-Q1"].period_start.iloc[0]
    ax.axvline(br, color=ORANGE, ls="--", lw=1.1, zorder=0)
    ax.text(br, 48.6, "  2021-Q1 break", color=ORANGE, fontsize=7.4,
            ha="left", va="top", fontstyle="italic")
    ax.set_ylim(30, 50)
    ax.set_ylabel("%")
    _style(ax, "National LFS Saudi share of employment (%)")

    last_q = k["last_employment_quarter"]
    ranks = reg[reg.quarter == last_q].sort_values("saudi_share")
    ax2 = fig.add_subplot(gs[1, 1])
    ax2.barh(ranks.region_name, ranks.saudi_share * 100, color=BLUE)
    ax2.set_xlim(0, 55)
    ax2.tick_params(axis="y", labelsize=7.4)
    ax2.grid(axis="x", color="#EEE", lw=0.6)
    ax2.grid(axis="y", visible=False)
    _style(ax2, f"Regional Saudi share, {last_q} (%)")

    ax3 = fig.add_subplot(gs[2, 0])
    sa = unemp[unemp.nationality == "saudi"]
    ax3.plot(sa.period_start, sa.unemp_total, color=NAVY, lw=2, label="Saudi, total")
    ax3.plot(sa.period_start, sa.unemp_female, color=ORANGE, lw=1.6, label="Saudi, female")
    ax3.plot(sa.period_start, sa.unemp_male, color=BLUE, lw=1.6, label="Saudi, male")
    ax3.legend(fontsize=7, frameon=False, loc="upper right")
    _style(ax3, "Saudi unemployment rate (%)")

    ax4 = fig.add_subplot(gs[2, 1])
    yt = youth[(youth.nationality == "saudi") & (youth.sex == "total")]
    ax4.plot(yt.period_start, yt.unemp_youth, color=ORANGE, lw=2, label="Saudi youth 15-24")
    ax4.plot(yt.period_start, yt.unemp_all, color=NAVY, lw=2, label="Saudi, all ages")
    ax4.legend(fontsize=7, frameon=False, loc="upper right")
    _style(ax4, "Saudi youth vs overall unemployment (%)")

    source = (
        "Source: GASTAT Labour Force Survey, tidy reprint by DataPulse (not an official GASTAT file), "
        "via the analytical tables in github.com/amirator/ksa-labour-market-sql. "
        "LFS household-survey estimates of all employment, not GOSI and not Nitaqat. "
        "Wages are nominal SAR. Portfolio project, not a client engagement. "
        "github.com/amirator/ksa-hr-labour-analytics"
    )
    fig.text(0.07, 0.012, fill(source, 200), fontsize=6.4, color="#555", va="bottom")
    return fig


def chart_ibm(ibm, k) -> plt.Figure:
    ibm = ibm.copy()
    ibm["left"] = ibm.Attrition.eq("Yes")
    ibm["TenureBand"] = pd.cut(
        ibm.YearsAtCompany,
        bins=[-0.1, 1, 3, 5, 10, 50],
        labels=["0-1 years", "2-3 years", "4-5 years", "6-10 years", "11+ years"],
    )
    ibm["IncomeQuartile"] = pd.qcut(
        ibm.MonthlyIncome, 4, labels=["Q1 lowest", "Q2", "Q3", "Q4 highest"]
    )

    fig = plt.figure(figsize=(14.2, 10.0), facecolor="white")

    # Unmissable honesty banner
    banner = fig.add_axes([0.05, 0.935, 0.90, 0.045])
    banner.set_xlim(0, 1)
    banner.set_ylim(0, 1)
    banner.axis("off")
    banner.add_patch(plt.Rectangle((0, 0), 1, 1, facecolor=WARN, edgecolor=ORANGE, lw=1.2, transform=banner.transAxes, clip_on=False))
    banner.text(
        0.5, 0.5,
        "FICTIONAL IBM SAMPLE  ·  1,470 invented employees  ·  not a KSA workforce  ·  "
        "no nationality field, so a Saudization ratio cannot be computed  ·  do not join to chapter A",
        ha="center", va="center", fontsize=7.6, color=NAVY, fontweight="bold",
    )

    fig.text(
        0.07, 0.915,
        "Chapter B  ·  IBM HR Attrition sample — method demo only",
        fontsize=15.5, fontweight="bold", color=NAVY, va="top",
    )
    finding = (
        f"Attrition is {k['ibm_attrition_pct']:.1f}% ({k['ibm_leavers']:,} of {k['ibm_n']:,}). "
        f"Employees recorded as working overtime left at {k['ibm_ot_yes_pct']:.1f}% "
        f"({k['ibm_ot_yes_leavers']} of {k['ibm_ot_yes_n']}), {k['ibm_ot_lift']:.1f} times the "
        f"{k['ibm_ot_no_pct']:.1f}% rate of those who did not; they make up "
        f"{k['ibm_ot_share_of_leavers_pct']:.1f}% of all leavers. The first year of tenure "
        f"({k['ibm_tenure0_pct']:.1f}%) and the lowest pay quartile ({k['ibm_income_q1_pct']:.1f}%, "
        f"income up to USD {k['ibm_income_q1_max']:,}) are the next sharpest splits; "
        f"Sales Representatives left at {k['ibm_sales_rep_pct']:.1f}%. "
        f"Leavers' median income was USD {k['ibm_leaver_income_median']:,} against "
        f"USD {k['ibm_stayer_income_median']:,}, median tenure {k['ibm_leaver_tenure_median']:.0f} years "
        f"against {k['ibm_stayer_tenure_median']:.0f}."
    )
    rec = (
        "Recommendation: Use this file to practise attrition analysis (rates, slices, a Power BI "
        "model). If it were a real workforce, overtime, the first year and the lowest pay quartile "
        "would be the first slices to brief. It is not a real workforce: keep these rates off any "
        "Saudi employer scorecard and off any Nitaqat or LFS briefing."
    )
    fig.text(0.07, 0.875, fill(finding, 155), fontsize=8.2, color="#1a1a1a", va="top")
    fig.text(0.07, 0.805, fill(rec, 155), fontsize=8.1, color="#1a1a1a", va="top", style="italic")

    gs = GridSpec(
        3, 2, figure=fig,
        left=0.11, right=0.97, top=0.755, bottom=0.065,
        hspace=0.48, wspace=0.32,
        height_ratios=[0.52, 1.15, 1.15],
    )
    cards = [
        ("Headcount (fictional)", f"{k['ibm_n']:,}", "IBM sample employees"),
        ("Leavers", f"{k['ibm_leavers']:,}", f"Stayers {k['ibm_stayers']:,}"),
        ("Attrition rate", f"{k['ibm_attrition_pct']:.1f}%", f"{k['ibm_leavers']} of {k['ibm_n']:,}"),
        ("Overtime, Yes", f"{k['ibm_ot_yes_pct']:.1f}%",
         f"{k['ibm_ot_lift']:.1f}× the No-overtime rate"),
        ("First year of tenure", f"{k['ibm_tenure0_pct']:.1f}%",
         f"n = {k['ibm_tenure0_n']:,}"),
    ]
    _cards(fig.add_subplot(gs[0, :]), cards)

    # Overtime and department
    ax = fig.add_subplot(gs[1, 0])
    ot = pd.DataFrame(k["dept_rates"])
    # two-panel-in-one: overtime as two thick bars plus dept
    # Simpler: just overtime two bars on this axis? We have 4 axes.
    # Axis 1: OverTime
    ot_vals = [
        ("No overtime", k["ibm_ot_no_pct"], k["ibm_ot_no_n"]),
        ("Overtime", k["ibm_ot_yes_pct"], k["ibm_ot_yes_n"]),
    ]
    colors = [BLUE, ORANGE]
    bars = ax.bar([v[0] for v in ot_vals], [v[1] for v in ot_vals], color=colors, width=0.55)
    for b, v in zip(bars, ot_vals):
        ax.text(b.get_x() + b.get_width() / 2, v[1] + 0.8, f"{v[1]:.1f}%\nn={v[2]:,}",
                ha="center", va="bottom", fontsize=8, color=NAVY)
    ax.set_ylim(0, 42)
    ax.set_ylabel("%")
    _style(ax, "Attrition rate by overtime (fictional sample)")

    ax2 = fig.add_subplot(gs[1, 1])
    roles = pd.DataFrame(k["role_rates"]).sort_values("rate_pct")
    ax2.barh(roles.job_role, roles.rate_pct, color=BLUE)
    for y, (rate, n) in enumerate(zip(roles.rate_pct, roles.n)):
        ax2.text(rate + 0.6, y, f"{rate:.1f}%  n={n}", va="center", fontsize=6.6, color=NAVY)
    ax2.set_xlim(0, 55)
    ax2.tick_params(axis="y", labelsize=7.4)
    ax2.grid(axis="x", color="#EEE", lw=0.6)
    ax2.grid(axis="y", visible=False)
    _style(ax2, "Attrition rate by job role (fictional sample)")

    ax3 = fig.add_subplot(gs[2, 0])
    ten = pd.DataFrame(k["tenure_rates"])
    bars = ax3.bar(ten.band, ten.rate_pct, color=BLUE, width=0.7)
    for b, row in zip(bars, ten.itertuples()):
        ax3.text(b.get_x() + b.get_width() / 2, row.rate_pct + 0.7,
                 f"{row.rate_pct:.1f}%", ha="center", va="bottom", fontsize=7.5, color=NAVY)
    ax3.set_ylim(0, 46)
    ax3.set_ylabel("%")
    ax3.tick_params(axis="x", labelsize=7.5)
    _style(ax3, "Attrition rate by years at the company (fictional sample)")

    ax4 = fig.add_subplot(gs[2, 1])
    inc = pd.DataFrame(k["income_rates"])
    bars = ax4.bar(inc.band, inc.rate_pct, color=BLUE, width=0.7)
    for b, row in zip(bars, inc.itertuples()):
        ax4.text(b.get_x() + b.get_width() / 2, row.rate_pct + 0.7,
                 f"{row.rate_pct:.1f}%", ha="center", va="bottom", fontsize=7.5, color=NAVY)
    ax4.set_ylim(0, 42)
    ax4.set_ylabel("%")
    ax4.tick_params(axis="x", labelsize=7.5)
    _style(ax4, "Attrition rate by monthly-income quartile (fictional sample)")

    source = (
        "Source: fictional IBM HR Attrition sample, IBM/employee-attrition-aif360 "
        "(Apache-2.0), 1,470 × 35, SHA-256 a5c31e38…7659. "
        "Invented employees, not a real workforce and not a Saudi employer. "
        "There is no nationality field. Portfolio project, not a client engagement. "
        "github.com/amirator/ksa-hr-labour-analytics"
    )
    fig.text(0.07, 0.012, fill(source, 200), fontsize=6.4, color="#555", va="bottom")
    return fig


def save_figures(fig_a, fig_b):
    FIGURES.mkdir(parents=True, exist_ok=True)
    pa = REPORTS / "dashboard_lfs.png"
    pb = REPORTS / "dashboard_ibm.png"
    fig_a.savefig(pa, dpi=150)
    fig_a.savefig(FIGURES / "dashboard_lfs.png", dpi=150)
    fig_b.savefig(pb, dpi=150)
    fig_b.savefig(FIGURES / "dashboard_ibm.png", dpi=150)
    pdf_path = REPORTS / "hr_analytics_dashboard.pdf"
    with PdfPages(pdf_path) as pdf:
        pdf.savefig(fig_a)
        pdf.savefig(fig_b)
        for fig in (fig_a, fig_b):
            d = pdf.infodict()
        pdf.infodict()["Title"] = "KSA labour market and IBM HR attrition — two chapters"
        pdf.infodict()["Author"] = "Mohammad Amir Khan"
        pdf.infodict()["Subject"] = (
            "Portfolio project. Chapter A is GASTAT LFS. "
            "Chapter B is a fictional IBM sample. The two are not joined. No .pbix."
        )
    plt.close(fig_a)
    plt.close(fig_b)
    return pa, pb, pdf_path


def write_readme(k):
    dept_rows = "\n".join(
        f"| {r['department']} | {r['n']:,} | {r['leavers']:,} | {r['rate_pct']:.1f}% |"
        for r in k["dept_rates"]
    )
    role_rows = "\n".join(
        f"| {r['job_role']} | {r['n']:,} | {r['leavers']:,} | {r['rate_pct']:.1f}% |"
        for r in k["role_rates"]
    )
    ten_rows = "\n".join(
        f"| {r['band']} | {r['n']:,} | {r['leavers']:,} | {r['rate_pct']:.1f}% |"
        for r in k["tenure_rates"]
    )
    inc_rows = "\n".join(
        f"| {r['band']} (${r['min']:,}–${r['max']:,}) | {r['n']:,} | {r['leavers']:,} | {r['rate_pct']:.1f}% |"
        for r in k["income_rates"]
    )
    text = f"""# KSA labour market and IBM HR attrition: a two-chapter analytics pack

**Business question:** What should an HR or HR-GR briefing take from official Saudi labour-market statistics, and what does a well-known public attrition sample show about drivers of leaving — without mixing the two into a fake company scorecard?

**Finding (chapter A, GASTAT LFS):** A single-quarter **break from {k['break_from']} to {k['break_to']}** cuts the LFS Saudi share of all employment from **{k['break_share_from_pct']:.1f}%** to **{k['break_share_to_pct']:.1f}%** ({k['break_share_pp']:+.1f} pp): Saudi employed changes by {k['break_saudi_change']:+,} and non-Saudi employed by {k['break_nonsaudi_change']:+,}. That jump is treated as a methodology or source change, not as a result. After the break the share sits in a 34-38% band and is **{k['saudi_share_last_pct']:.1f}%** in {k['last_employment_quarter']} ({k['share_postbreak_change_pp']:+.1f} pp from {k['break_to']}). In {k['last_unemp_quarter']} Saudi unemployment was **{k['saudi_unemp_pct']:.2f}%** (women {k['saudi_unemp_female_pct']:.2f}%, youth 15-24 {k['youth_saudi_pct']:.2f}%). This is the Labour Force Survey share of **all** employment. It is **not** a Nitaqat or Saudization score.

**Finding (chapter B, fictional IBM sample):** Attrition is **{k['ibm_attrition_pct']:.2f}%** ({k['ibm_leavers']:,} of {k['ibm_n']:,}). Employees recorded as working overtime left at **{k['ibm_ot_yes_pct']:.1f}%** ({k['ibm_ot_yes_leavers']} of {k['ibm_ot_yes_n']}), **{k['ibm_ot_lift']:.2f} times** the {k['ibm_ot_no_pct']:.1f}% rate of those who did not, and they make up {k['ibm_ot_share_of_leavers_pct']:.1f}% of leavers. The first year of tenure ({k['ibm_tenure0_pct']:.1f}%, n={k['ibm_tenure0_n']:,}) and the lowest monthly-income quartile ({k['ibm_income_q1_pct']:.1f}%, income up to ${k['ibm_income_q1_max']:,}) are the next sharpest splits. Sales Representatives left at {k['ibm_sales_rep_pct']:.1f}%. This is a **fictional IBM sample**, not a Saudi workforce, and it has **no nationality field**.

**Recommendation:** Keep three things on separate scorecards: the LFS Saudi share, private-sector Nitaqat, and any company attrition analysis. Use the IBM file only as a method demo for attrition rates and a Power BI model. Do not compute a Saudization ratio from either chapter, and do not join the two tables.

![Chapter A: GASTAT LFS](reports/dashboard_lfs.png)

![Chapter B: IBM HR Attrition (fictional)](reports/dashboard_ibm.png)

A two-page PDF of the same figures is in [`reports/hr_analytics_dashboard.pdf`](reports/hr_analytics_dashboard.pdf). Both pages are rendered in Python from the same model CSVs that the Power BI pack loads. There is **no `.pbix`** in this repository (Power BI Desktop is not available on Linux).

## The two chapters must stay apart

| Chapter | Data | What it can answer | What it cannot |
|---|---|---|---|
| A | GASTAT Labour Force Survey, via the analytical tables in [ksa-labour-market-sql](https://github.com/amirator/ksa-labour-market-sql) | National and regional **headcount**, the **LFS Saudi share of all employment**, unemployment, youth unemployment, nominal wages | A Nitaqat (private-sector Saudization) score; company-level attrition; anything about a named employer |
| B | IBM HR Attrition sample, 1,470 **fictional** employees, SHA-256 `{k['ibm_sha256'][:16]}…` | Attrition rates and slices (overtime, tenure, pay, role) as a **method demo** | Anything about a Saudi employer; a Saudization ratio (there is **no nationality field**); a join to chapter A |

The Power BI model ships as two unconnected halves. `powerbi/model/DO_NOT_JOIN.txt` and the model diagram say the same thing.

## Chapter A — GASTAT LFS (official statistics)

The headline LFS Saudi share in {k['last_employment_quarter']} is **{k['saudi_share_last_pct']:.2f}%**, on {k['employed_last']:,} employed of whom {k['saudi_employed_last']:,} are Saudi. A naive comparison with {k['first_quarter']} ({k['saudi_share_first_pct']:.2f}%, {k['saudi_share_change_pp']:+.2f} pp) **crosses a break**: between {k['break_from']} and {k['break_to']} the share falls {k['break_share_pp']:+.2f} pp. After {k['break_to']} it changes by only {k['share_postbreak_change_pp']:+.2f} pp. The 2021-Q1 step is reported as a data issue.

In {k['last_employment_quarter']} the regional share ran from **{k['bottom_region']} {k['bottom_region_share_pct']:.2f}%** to **{k['top_region']} {k['top_region_share_pct']:.2f}%**. In {k['last_unemp_quarter']} Saudi unemployment was **{k['saudi_unemp_pct']:.2f}%** (women **{k['saudi_unemp_female_pct']:.2f}%**, men {k['saudi_unemp_male_pct']:.2f}%, gap {k['saudi_unemp_gap_pp']:.2f} pp) and Saudi youth (15-24) unemployment was **{k['youth_saudi_pct']:.2f}%** ({k['youth_gap_pp']:.2f} pp above the all-ages rate, {k['youth_vs_first_pp']:+.2f} pp from the first quarter of that series). Saudi paid employees averaged **SAR {k['wage_saudi']:,.0f}** a month against **SAR {k['wage_nonsaudi']:,.0f}** for non-Saudis (ratio {k['wage_ratio']:.2f}), in nominal riyals.

The sister SQL project documents that nationality and region totals reconcile exactly, and that the two unemployment files differ by at most 0.05 pp of rounding.

## Chapter B — IBM HR Attrition (fictional sample)

Overall attrition is **{k['ibm_attrition_pct']:.2f}%** ({k['ibm_leavers']:,} Yes, {k['ibm_stayers']:,} No).

### Overtime (the sharpest split)

| Overtime | Employees | Leavers | Attrition |
|---|---:|---:|---:|
| Yes | {k['ibm_ot_yes_n']:,} | {k['ibm_ot_yes_leavers']:,} | {k['ibm_ot_yes_pct']:.2f}% |
| No | {k['ibm_ot_no_n']:,} | {k['ibm_ot_no_leavers']:,} | {k['ibm_ot_no_pct']:.2f}% |

The Yes rate is **{k['ibm_ot_lift']:.2f}×** the No rate. Overtime employees are {k['ibm_ot_share_of_leavers_pct']:.1f}% of leavers.

### Department

| Department | Employees | Leavers | Attrition |
|---|---:|---:|---:|
{dept_rows}

### Job role

| Job role | Employees | Leavers | Attrition |
|---|---:|---:|---:|
{role_rows}

### Years at the company

| Tenure | Employees | Leavers | Attrition |
|---|---:|---:|---:|
{ten_rows}

### Monthly income quartile

| Quartile | Employees | Leavers | Attrition |
|---|---:|---:|---:|
{inc_rows}

Leavers had a median monthly income of ${k['ibm_leaver_income_median']:,} (mean ${k['ibm_leaver_income_mean']:,.0f}) against ${k['ibm_stayer_income_median']:,} (mean ${k['ibm_stayer_income_mean']:,.0f}) for stayers; a median tenure of {k['ibm_leaver_tenure_median']:.0f} years against {k['ibm_stayer_tenure_median']:.0f}; and a median age of {k['ibm_leaver_age_median']:.0f} against {k['ibm_stayer_age_median']:.0f}. Single employees left at {k['ibm_single_pct']:.1f}% (n={k['ibm_single_n']:,}); frequent travellers at {k['ibm_travel_pct']:.1f}% (n={k['ibm_travel_n']:,}).

These are slices of a **fictional** file. They are not evidence about any Saudi employer.

## Power BI pack

Power BI Desktop cannot run on this Linux build machine, so this repository does **not** contain a `.pbix`. The pack is ready to load on a Windows machine:

| Artefact | Path |
|---|---|
| Star-schema model CSVs (two unconnected halves) | [`powerbi/model/`](powerbi/model/) |
| Power Query M (one query per table) | [`powerbi/queries/`](powerbi/queries/) |
| DAX measures (chapter A and chapter B, clearly sectioned) | [`powerbi/measures.dax`](powerbi/measures.dax) |
| Model diagram (mermaid + PNG) | [`powerbi/model_diagram.png`](powerbi/model_diagram.png) |
| How to load, and the no-`.pbix` note | [`powerbi/README.md`](powerbi/README.md) |
| Python-rendered dashboards from the same model | `reports/dashboard_lfs.png`, `reports/dashboard_ibm.png`, `reports/hr_analytics_dashboard.pdf` |

A `.pbix` will be added if it is built later on a Windows machine. Until then, any claim that a `.pbix` already exists would be false.

## Data, licence and period

| Chapter | Official / origin | What is in this repo | Rows | Period / grain | Licence |
|---|---|---|---:|---|---|
| A | GASTAT Labour Force Survey, tidy reprint by [DataPulse](https://datapulseactive.com/en/data/open/) | Slim analytical tables in [`data/gastat/`](data/gastat/), produced by [ksa-labour-market-sql](https://github.com/amirator/ksa-labour-market-sql) | employment 35 national quarters, 455 region-quarters; unemployment to 2026-Q2 | Employment 2016-Q2–2024-Q4; unemployment 2021-Q1–2026-Q2 | [GASTAT use policy](https://www.stats.gov.sa/en/use-policy) (Arabic text governs) |
| B | IBM, via [IBM/employee-attrition-aif360](https://github.com/IBM/employee-attrition-aif360) | Frozen [`data/ibm/emp_attrition.csv`](data/ibm/emp_attrition.csv) | 1,470 × 35 | Cross-section, no calendar date | Apache-2.0 on that repository; the file is a fictional sample |

SHA-256 of the IBM file: `{k['ibm_sha256']}`. Details and the DataPulse / GASTAT citation are in [`data/ibm/SOURCE.md`](data/ibm/SOURCE.md) and [`data/gastat/SOURCES.md`](data/gastat/SOURCES.md). No rows were dropped from either source. The IBM file is used as published; analysis bands (`TenureBand`, `IncomeQuartile`, `AttritionFlag`) are added only in the model copy.

## How to run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py      # model CSVs, kpis.json, dashboards, README
python -m pytest -q
```

CI (GitHub Actions) runs the same two commands on every push.

## Limitations

- **Chapter A is a household survey**, with sampling error. It is not a GOSI register and it is not Nitaqat. A falling LFS Saudi *share* can sit alongside a rising private-sector Saudization *score*, because coverage and the denominator differ (this series includes domestic workers, the self-employed, and the public sector).
- **2020-Q4 to 2021-Q1 is a break** in the LFS employment series ({k['break_share_pp']:+.2f} pp in one quarter). Comparisons that cross 2021-Q1 should be made only with that caveat. The full discussion and the reconciliation checks live in the sister SQL project.
- Employment and wages end in **{k['last_employment_quarter']}**; unemployment runs to **{k['last_unemp_quarter']}**. The two windows are stated next to every figure.
- Wages are **nominal** SAR, not adjusted for hours, occupation or inflation.
- **Chapter B is fictional.** The attrition rates describe invented IBM employees. They are not KSA rates and they are not used to estimate a Saudi company's attrition or Saudization.
- The two chapters **must not be joined**. This repository never computes a "company Saudization" figure.
- The tidy GASTAT CSVs used upstream are a **third-party reprint**, not an official GASTAT file.
- There is **no `.pbix`**. Dashboards are Python renders of the same model.
- This is an independent portfolio project. It is not a client engagement, not employment, and not affiliated with GASTAT, DataPulse or IBM.

## Author

Mohammad Amir Khan, Jeddah · [GitHub](https://github.com/amirator) · [LinkedIn](https://www.linkedin.com/in/amir-khan-a31363235/)

MIT licence (code). Data: GASTAT (via the policy above) and the fictional IBM sample (Apache-2.0 on the upstream repository).
"""
    (ROOT / "README.md").write_text(text)
    return ROOT / "README.md"


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    emp, reg, unemp, youth, wages, ibm, digest = load()
    build_model(emp, reg, unemp, youth, wages, ibm)
    k = kpis(emp, reg, unemp, youth, wages, ibm, digest)
    (REPORTS / "kpis.json").write_text(json.dumps(k, indent=2, default=str))
    fig_a = chart_lfs(emp, reg, unemp, youth, k)
    fig_b = chart_ibm(ibm, k)
    pa, pb, pdf = save_figures(fig_a, fig_b)
    write_readme(k)
    print(
        f"[done] LFS share {k['saudi_share_last_pct']}%  "
        f"IBM attrition {k['ibm_attrition_pct']}%  "
        f"OT {k['ibm_ot_yes_pct']}%  "
        f"{pa} {pb} {pdf}"
    )


if __name__ == "__main__":
    main()
