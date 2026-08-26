# EDU Sentinel - Phase 1 Executive MVP

Prototype สำหรับระบบเตือนภัยและวิเคราะห์ข้อมูลเชิงนโยบายด้านสิทธิทางการศึกษาและความเหลื่อมล้ำ

## Modules
1. Authentication & Basic User
2. Data Import (CSV/Excel)
3. Executive Dashboard
4. Thailand Risk Map
5. Early Warning Engine
6. Alert Center
7. AI Executive Summary (offline explainable MVP)
8. Report Export (Excel/HTML)

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
- Username: `admin`
- Password: `admin1234`

> Change the demo password before production use.

## Input columns
- student_id
- province
- attendance_rate (0-100)
- gpa (0-4)
- income_per_month
- dropout_risk_flag (0/1)
- disability_flag (0/1)
- remote_area_flag (0/1)

The importer also recognizes selected Thai column aliases.

## Risk Model (MVP)
- Attendance gap: up to 35 points
- GPA gap: up to 25 points
- Household income below 8,000 THB: up to 20 points
- Dropout flag: +10
- Disability: +5
- Remote area: +5

Thresholds: Low <25, Medium <50, High <75, Critical >=75.

## Production next steps
- Replace SQLite with PostgreSQL
- Implement RBAC and organization/area scopes
- Add Thailand province/district GeoJSON choropleth
- Add audit log and PDPA controls
- Version risk rules and thresholds
- Connect approved LLM for grounded executive summaries
- Add PDF/DOCX exports and scheduled reports
- Add API ingestion and data validation pipeline
