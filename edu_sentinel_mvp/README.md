# EDU Sentinel - Phase 1 Executive MVP

Prototype สำหรับระบบเตือนภัยและวิเคราะห์ข้อมูลเชิงนโยบายด้านสิทธิทางการศึกษาและความเหลื่อมล้ำ

## Modules
1. Authentication, roles and route protection
2. Data Import (CSV/Excel) with schema validation and data quality metadata
3. Executive Command Center with KPI, trend, top alerts, coverage gap and lineage
4. Thailand Risk Map with province > district > school drill-down
5. Early Warning Engine with rule version, severity, confidence and drivers
6. Alert Center & Detail with evidence, SLA, source, status and data quality
7. Case / Action Tracking for owner, due date, status, outcome and learning notes
8. What-if Scenario and Policy Impact Simulation for non-persistent policy planning
9. AI Executive Summary (offline explainable MVP) with Answer/Evidence/Why/Limitations/Next Action
10. Report Export (Excel/HTML print view)
11. Admin & Governance view for RBAC and data health

## Run
```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the URL shown by Streamlit, normally http://localhost:8501

## Demo login
- Admin: `admin` / `admin1234`
- Analyst: `analyst` / `analyst1234`
- Executive: `executive` / `exec1234`

> Change the demo password before production use.

## Input columns
- student_id
- province
- district
- school_name
- period
- attendance_rate (0-100)
- gpa (0-4)
- income_per_month
- dropout_risk_flag (0/1)
- disability_flag (0/1)
- remote_area_flag (0/1)
- program_coverage_flag (0/1)

The importer also recognizes selected Thai column aliases.

## Risk Model (MVP)
- Attendance gap: up to 35 points
- GPA gap: up to 25 points
- Household income below 8,000 THB: up to 20 points
- Dropout flag: +10
- Disability: +5
- Remote area: +5

Thresholds: Low <25, Medium <50, High <75, Critical >=75.

Alerts include severity, priority score, trigger, drivers, evidence references,
data quality flag, SLA due date, rule version and model version.

## Production next steps
- Replace SQLite with PostgreSQL
- Implement RBAC and organization/area scopes
- Add Thailand province/district GeoJSON choropleth
- Add audit log and PDPA controls
- Version risk rules and thresholds
- Connect approved LLM for grounded executive summaries
- Add PDF/DOCX exports and scheduled reports
- Add API ingestion and data validation pipeline
