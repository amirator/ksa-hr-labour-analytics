"""Quality bar for the two-chapter HR analytics pack."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
IBM = ROOT / "data" / "ibm" / "emp_attrition.csv"
MODEL = ROOT / "powerbi" / "model"
KPIS = json.loads((REPORTS / "kpis.json").read_text())
README = (ROOT / "README.md").read_text()
IBM_SHA = "a5c31e38bd7fafc9bc333884eb181b06b41b8e5e488e8f7ccb27199fb3be7659"


def test_ibm_file_is_the_known_public_sample():
    digest = hashlib.sha256(IBM.read_bytes()).hexdigest()
    assert digest == IBM_SHA
    assert digest == KPIS["ibm_sha256"]
    df = pd.read_csv(IBM)
    assert df.shape == (1470, 35)
    assert (df.Attrition == "Yes").sum() == 237
    assert (df.Attrition == "No").sum() == 1233
    assert KPIS["ibm_n"] == 1470
    assert KPIS["ibm_leavers"] == 237
    assert KPIS["ibm_attrition_pct"] == pytest.approx(16.12, abs=0.005)


def test_ibm_has_no_nationality_and_no_saudization():
    df = pd.read_csv(IBM)
    cols = {c.lower() for c in df.columns}
    assert "nationality" not in cols
    assert "saudi" not in cols
    assert "saudization" not in cols
    assert "nitaqat" not in cols
    assert KPIS["ibm_has_nationality"] is False
    model = pd.read_csv(MODEL / "fct_employee.csv")
    mcols = {c.lower() for c in model.columns}
    assert "nationality" not in mcols
    assert "saudization" not in mcols
    # Analysis bands are added only in the model copy, source file is untouched.
    assert "AttritionFlag" in model.columns
    assert "TenureBand" in model.columns
    assert "IncomeQuartile" in model.columns
    assert "AttritionFlag" not in df.columns
    assert len(model) == 1470


def test_overtime_is_the_sharpest_reported_split():
    assert KPIS["ibm_ot_yes_pct"] == pytest.approx(30.53, abs=0.02)
    assert KPIS["ibm_ot_no_pct"] == pytest.approx(10.44, abs=0.02)
    assert KPIS["ibm_ot_lift"] == pytest.approx(2.93, abs=0.02)
    assert KPIS["ibm_ot_yes_leavers"] == 127
    assert KPIS["ibm_ot_yes_n"] == 416
    assert KPIS["ibm_tenure0_pct"] == pytest.approx(34.88, abs=0.02)
    assert KPIS["ibm_income_q1_pct"] == pytest.approx(29.27, abs=0.02)


def test_lfs_share_and_break_match_sister_project():
    assert KPIS["saudi_share_last_pct"] == pytest.approx(34.79, abs=0.015)
    assert KPIS["last_employment_quarter"] == "2024-Q4"
    assert KPIS["break_from"] == "2020-Q4"
    assert KPIS["break_to"] == "2021-Q1"
    assert KPIS["break_share_pp"] == pytest.approx(-10.48, abs=0.02)
    assert KPIS["break_saudi_change"] == -1730601
    assert KPIS["share_postbreak_change_pp"] == pytest.approx(-0.62, abs=0.02)
    assert KPIS["saudi_unemp_pct"] == pytest.approx(6.48, abs=0.015)
    assert KPIS["youth_saudi_pct"] == pytest.approx(15.16, abs=0.015)
    assert KPIS["top_region"] == "Jazan"
    assert KPIS["bottom_region"] == "Riyadh"


def test_readme_tracks_kpis_and_honesty():
    md = README
    k = KPIS
    assert "Business question:" in md
    assert "Finding (chapter A" in md
    assert "Finding (chapter B" in md
    assert "Recommendation:" in md
    assert "Limitations" in md
    assert f"{k['saudi_share_last_pct']:.1f}%" in md
    assert f"{k['break_share_from_pct']:.1f}%" in md
    assert f"{k['saudi_unemp_pct']:.2f}%" in md
    assert f"{k['ibm_attrition_pct']:.2f}%" in md
    assert f"{k['ibm_ot_yes_pct']:.1f}%" in md
    assert f"{k['ibm_ot_lift']:.2f}" in md
    assert f"{k['break_saudi_change']:+,}" in md
    assert "fictional" in md.lower()
    assert "not" in md.lower() and "nitaqat" in md.lower()
    assert "no nationality field" in md.lower()
    assert "must not be joined" in md.lower() or "do not join" in md.lower()
    assert "no `.pbix`" in md.lower() or "no `.pbix`" in md or "no `.pbix`" in md.replace("**", "")
    assert "not a client engagement" in md.lower()
    # Must not sell LFS share as Nitaqat.
    assert "not** a Nitaqat" in md or "not a Nitaqat" in md or "not** a Nitaqat or Saudization" in md


def test_no_pbix_is_shipped():
    pbix = list(ROOT.rglob("*.pbix"))
    assert pbix == [], pbix
    powerbi_readme = (ROOT / "powerbi" / "README.md").read_text().lower()
    assert "no `.pbix`" in powerbi_readme or "no .pbix" in powerbi_readme or "there is no `.pbix`" in powerbi_readme


def test_dashboards_and_pdf():
    for name in ("dashboard_lfs.png", "dashboard_ibm.png"):
        p = REPORTS / name
        assert p.is_file(), name
        assert p.stat().st_size > 80_000, name
    pdf = REPORTS / "hr_analytics_dashboard.pdf"
    assert pdf.is_file()
    raw = pdf.read_bytes()
    assert raw.startswith(b"%PDF")
    # Matplotlib PdfPages writes one /Type /Page per page (and a /Type /Pages tree).
    n_pages = len(re.findall(rb"/Type\s*/Page(?!s)", raw))
    assert n_pages == 2, n_pages


def test_model_csvs_and_do_not_join():
    for name, n in {
        "fct_employment_national.csv": 35,
        "fct_employment_region.csv": 455,
        "fct_employee.csv": 1470,
        "dim_quarter.csv": None,
        "dim_region.csv": 13,
        "dim_department.csv": 3,
        "dim_job_role.csv": 9,
        "fct_unemployment.csv": 66,
        "fct_youth.csv": 198,
    }.items():
        p = MODEL / name
        assert p.is_file(), name
        if n is not None:
            assert len(pd.read_csv(p)) == n, name
    note = (MODEL / "DO_NOT_JOIN.txt").read_text().lower()
    assert "must not be related" in note or "must not" in note
    assert "no nationality" in note


def test_dax_is_sectioned_and_has_no_saudization_measure():
    dax = (ROOT / "powerbi" / "measures.dax").read_text()
    assert "Chapter A" in dax
    assert "Chapter B" in dax
    assert "LFS Saudi Share" in dax
    assert "Attrition Rate (IBM sample)" in dax
    assert "Headcount (IBM sample)" in dax
    # No measure is *named* Saudization or Nitaqat (comments may warn against it).
    for raw in dax.splitlines():
        line = raw.strip()
        if not line or line.startswith("//") or line.startswith("VAR") or line.startswith("RETURN"):
            continue
        if "=" in line:
            name = line.split("=")[0]
            assert re.search(r"saudization|nitaqat", name, re.I) is None, raw
    # The warning belongs in a comment.
    assert "Saudization" in dax or "Nitaqat" in dax


def test_power_query_m_and_diagram():
    queries = list((ROOT / "powerbi" / "queries").glob("*.m"))
    names = {p.stem for p in queries}
    assert "fct_employee" in names
    assert "fct_employment_national" in names
    assert "dim_quarter" in names
    assert len(queries) >= 10
    for p in queries:
        text = p.read_text()
        assert "Csv.Document" in text
        assert "FolderPath" in text
        assert "No .pbix" in text or "no .pbix" in text.lower()
    png = ROOT / "powerbi" / "model_diagram.png"
    mmd = ROOT / "powerbi" / "model_diagram.mmd"
    assert png.is_file() and png.stat().st_size > 10_000
    assert "NO RELATIONSHIP" in mmd.read_text()


def test_gastat_extracts_present():
    g = ROOT / "data" / "gastat"
    assert (g / "SOURCES.md").is_file()
    assert "not Nitaqat" in (g / "SOURCES.md").read_text() or "not Nitaqat" in (g / "SOURCES.md").read_text()
    assert len(pd.read_csv(g / "fct_employment_national.csv")) == 35
    assert "GASTAT" in (g / "SOURCES.md").read_text()


def test_honesty_block_in_kpis():
    honesty = " ".join(KPIS["honesty"]).lower()
    assert "portfolio" in honesty
    assert "not a client" in honesty
    assert "fictional" in honesty
    assert "must not be joined" in honesty
    assert "no .pbix" in honesty or "no `.pbix`" in honesty
