import hashlib
import hmac
import io
import os
import random
import secrets
import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st


DB_PATH = os.path.join(os.path.dirname(__file__), "edu_sentinel.db")
RULE_VERSION = "edu-risk-ruleset-v0.1.0"
MODEL_VERSION = "offline-executive-summary-v0.1.0"
PROMPT_VERSION = "exec-brief-template-v0.1.0"
UP_PRIMARY = "#8D38C9"
UP_PRIMARY_DARK = "#5E2389"
UP_ACCENT = "#C4996C"
UP_BG = "#F7F7FA"
UP_TEXT = "#20232A"
RISK_COLORS = {
    "Low": "#1F9D55",
    "Medium": "#D6A21E",
    "High": "#E66A2C",
    "Critical": "#D92D20",
}

PAGES = [
    "Executive Command Center",
    "Operations Dashboard",
    "Data Import",
    "Thailand Risk Map",
    "Early Warning Engine",
    "Alert Center & Detail",
    "Case / Action Tracking",
    "Policy Intelligence",
    "AI Executive Summary",
    "Executive Report Export",
    "Admin & Governance",
]

PAGE_METADATA = {
    "Executive Command Center": {
        "label": "ภาพรวมผู้บริหาร",
        "group": "มุมมองเชิงนโยบาย",
        "description": "สัญญาณสำคัญ ความเสี่ยง และช่องว่างมาตรการ",
    },
    "Operations Dashboard": {
        "label": "ติดตามสถานการณ์",
        "group": "มุมมองเชิงนโยบาย",
        "description": "แนวโน้มรายเดือน พื้นที่เสี่ยง และภาระงาน",
    },
    "Policy Intelligence": {
        "label": "วิเคราะห์นโยบาย",
        "group": "มุมมองเชิงนโยบาย",
        "description": "ช่องว่างมาตรการและผลจำลองเชิงนโยบาย",
    },
    "AI Executive Summary": {
        "label": "สรุปสำหรับผู้บริหาร",
        "group": "มุมมองเชิงนโยบาย",
        "description": "สรุปพร้อมหลักฐาน ข้อจำกัด และสิ่งที่ควรทำต่อ",
    },
    "Thailand Risk Map": {
        "label": "แผนที่ความเสี่ยง",
        "group": "พื้นที่และสัญญาณเตือน",
        "description": "ดูระดับจังหวัด อำเภอ และโรงเรียน",
    },
    "Early Warning Engine": {
        "label": "กติกาเตือนภัย",
        "group": "พื้นที่และสัญญาณเตือน",
        "description": "ตรวจสูตรคะแนน เหตุผล และความเชื่อมั่น",
    },
    "Alert Center & Detail": {
        "label": "ศูนย์แจ้งเตือน",
        "group": "พื้นที่และสัญญาณเตือน",
        "description": "จัดลำดับ alert หลักฐาน SLA และสถานะ",
    },
    "Case / Action Tracking": {
        "label": "ติดตามการดำเนินงาน",
        "group": "การปฏิบัติและกำกับดูแล",
        "description": "มอบหมายผู้รับผิดชอบ วันครบกำหนด และผลลัพธ์",
    },
    "Data Import": {
        "label": "นำเข้าข้อมูล",
        "group": "การปฏิบัติและกำกับดูแล",
        "description": "ตรวจ schema คุณภาพข้อมูล และ source",
    },
    "Executive Report Export": {
        "label": "ออกรายงาน",
        "group": "การปฏิบัติและกำกับดูแล",
        "description": "รายงานสำหรับประชุมและ export workbook",
    },
    "Admin & Governance": {
        "label": "ธรรมาภิบาลระบบ",
        "group": "การปฏิบัติและกำกับดูแล",
        "description": "สิทธิ์ผู้ใช้ สุขภาพข้อมูล lineage และ audit",
    },
}

MENU_GROUPS = [
    "มุมมองเชิงนโยบาย",
    "พื้นที่และสัญญาณเตือน",
    "การปฏิบัติและกำกับดูแล",
]

DISPLAY_COLUMN_LABELS = {
    "id": "รหัส Alert",
    "case_id": "รหัส Case",
    "alert_id": "รหัส Alert",
    "student_id": "รหัสผู้เรียน",
    "period": "รอบข้อมูล",
    "province": "จังหวัด",
    "district": "อำเภอ",
    "school_name": "สถานศึกษา",
    "risk_score": "คะแนนเสี่ยง",
    "score": "คะแนน",
    "avg_risk": "คะแนนเสี่ยงเฉลี่ย",
    "before_avg_risk": "ก่อนจำลอง",
    "after_avg_risk": "หลังจำลอง",
    "risk_level": "ระดับความเสี่ยง",
    "severity": "ความรุนแรง",
    "priority_score": "ลำดับความสำคัญ",
    "status": "สถานะ",
    "sla_due_at": "ครบกำหนด SLA",
    "created_at": "วันที่สร้าง",
    "due_at": "วันครบกำหนด",
    "resolved_at": "วันที่ปิดงาน",
    "owner": "ผู้รับผิดชอบ",
    "action_note": "แนวทางดำเนินงาน",
    "outcome": "ผลลัพธ์/บทเรียน",
    "learners": "จำนวนผู้เรียน",
    "people": "จำนวนคน",
    "risk_people": "กลุ่มเสี่ยง",
    "covered": "ครอบคลุมแล้ว",
    "coverage_gap": "ช่องว่างมาตรการ",
    "gap_rate": "อัตราช่องว่าง",
    "critical": "วิกฤต",
    "high": "สูง",
    "risk_load": "ภาระความเสี่ยง",
    "uncovered": "ยังไม่ครอบคลุม",
    "attendance_rate": "อัตราเข้าเรียน",
    "gpa": "GPA",
    "income_per_month": "รายได้/เดือน",
    "dropout_risk_flag": "เสี่ยงหลุดระบบ",
    "disability_flag": "พิการ",
    "remote_area_flag": "พื้นที่ห่างไกล",
    "program_coverage_flag": "มีมาตรการ",
    "confidence": "ความเชื่อมั่น",
    "drivers": "ปัจจัยเสี่ยง",
    "trigger": "เงื่อนไขเตือน",
    "message": "ข้อความแจ้งเตือน",
    "evidence_refs": "หลักฐานอ้างอิง",
    "data_quality_flag": "คุณภาพข้อมูล",
    "rule_version": "เวอร์ชันกติกา",
    "model_version": "เวอร์ชันโมเดล",
    "source_id": "แหล่งข้อมูล",
    "run_id": "รอบนำเข้า",
    "source_name": "ชื่อแหล่งข้อมูล",
    "imported_at": "เวลานำเข้า",
    "row_count": "จำนวนแถว",
    "completeness": "ความครบถ้วน",
    "freshness_days": "อายุข้อมูล",
    "schema_status": "สถานะโครงสร้างข้อมูล",
    "name": "ชื่อ",
    "definition": "นิยาม",
    "formula": "สูตร",
    "denominator": "ฐานคำนวณ",
    "aggregation_level": "ระดับสรุปผล",
    "source_fields": "ฟิลด์ต้นทาง",
    "updated_at": "ปรับปรุงล่าสุด",
    "program_id": "รหัสมาตรการ",
    "target_group": "กลุ่มเป้าหมาย",
    "area_scope": "ขอบเขตพื้นที่",
    "coverage_count": "จำนวนครอบคลุม",
    "before_score": "คะแนนก่อน",
    "after_score": "คะแนนหลัง",
    "risk_delta": "ผลต่างคะแนน",
    "before_level": "ระดับก่อน",
    "after_level": "ระดับหลัง",
    "before_covered": "ก่อนมีมาตรการ",
    "after_covered": "หลังมีมาตรการ",
    "targeted": "อยู่ในกลุ่มเป้าหมาย",
}

ROLE_PERMISSIONS = {
    "executive": {
        "Executive Command Center",
        "Thailand Risk Map",
        "Alert Center & Detail",
        "Policy Intelligence",
        "AI Executive Summary",
        "Executive Report Export",
    },
    "analyst": set(PAGES) - {"Admin & Governance"},
    "admin": set(PAGES),
}

REQUIRED_COLUMNS = [
    "student_id",
    "province",
    "district",
    "school_name",
    "period",
    "attendance_rate",
    "gpa",
    "income_per_month",
    "dropout_risk_flag",
    "disability_flag",
    "remote_area_flag",
    "program_coverage_flag",
]

PROVINCE_COORDS = {
    "Bangkok": (13.7563, 100.5018),
    "Chiang Mai": (18.7883, 98.9853),
    "Chiang Rai": (19.9105, 99.8406),
    "Khon Kaen": (16.4322, 102.8236),
    "Ubon Ratchathani": (15.2447, 104.8473),
    "Chonburi": (13.3611, 100.9847),
    "Pattani": (6.8695, 101.2505),
    "Songkhla": (7.1898, 100.5954),
    "Tak": (16.8839, 99.1258),
    "Mae Hong Son": (19.3020, 97.9654),
    "Narathiwat": (6.4255, 101.8253),
}

DEMO_PERIODS = ["2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08"]
DEMO_STUDENTS_PER_PROVINCE = {
    "Bangkok": 14,
    "Chiang Mai": 11,
    "Chiang Rai": 9,
    "Khon Kaen": 9,
    "Ubon Ratchathani": 8,
    "Chonburi": 10,
    "Pattani": 10,
    "Songkhla": 9,
    "Tak": 11,
    "Mae Hong Son": 9,
    "Narathiwat": 10,
}
DEMO_PROVINCE_PROFILES = {
    "Bangkok": {
        "story": "large city baseline with a few urban poverty pockets",
        "districts": {
            "Phaya Thai": ["Bangkok Equity School", "Riverside Learning Hub"],
            "Khlong Toei": ["Khlong Toei Opportunity School", "Metro Bridge School"],
            "Bang Kapi": ["Bang Kapi City School", "Urban Access Academy"],
        },
        "risk_shift": -0.22,
        "remote_bias": 0.01,
        "dropout_bias": 0.04,
        "coverage_base": 0.78,
        "latest_coverage_lift": 0.04,
    },
    "Chonburi": {
        "story": "industrial city with mostly low risk and some migrant-worker pockets",
        "districts": {
            "Mueang": ["Chonburi City School", "Coastal Demonstration School"],
            "Si Racha": ["Si Racha Learning Center", "Harbor Opportunity School"],
            "Bang Lamung": ["Bang Lamung Municipal School", "Eastern Bridge School"],
        },
        "risk_shift": -0.16,
        "remote_bias": 0.02,
        "dropout_bias": 0.06,
        "coverage_base": 0.72,
        "latest_coverage_lift": 0.05,
    },
    "Khon Kaen": {
        "story": "regional hub with improving coverage in the latest period",
        "districts": {
            "Mueang": ["Khon Kaen Inclusive School", "Northeast Demonstration School"],
            "Chum Phae": ["Chum Phae Opportunity School", "Plateau Learning Center"],
            "Ban Phai": ["Ban Phai Community School", "Mittraphap Bridge School"],
        },
        "risk_shift": -0.05,
        "remote_bias": 0.09,
        "dropout_bias": 0.08,
        "coverage_base": 0.63,
        "latest_coverage_lift": 0.12,
    },
    "Songkhla": {
        "story": "southern urban corridor with moderate attendance pressure",
        "districts": {
            "Hat Yai": ["Songkhla Demonstration School", "Hat Yai Equity School"],
            "Saba Yoi": ["Saba Yoi Care School", "Southern Access School"],
            "Mueang": ["Songkhla Municipal School", "Lake Bridge Academy"],
        },
        "risk_shift": 0.03,
        "remote_bias": 0.06,
        "dropout_bias": 0.13,
        "coverage_base": 0.58,
        "latest_coverage_lift": 0.06,
    },
    "Ubon Ratchathani": {
        "story": "Mekong border districts with remote access pressure",
        "districts": {
            "Khong Chiam": ["Mekong Border School", "River Access Learning Center"],
            "Nam Yuen": ["Nam Yuen Opportunity School", "Emerald Triangle School"],
            "Mueang": ["Ubon Municipal School", "Northeast Care Academy"],
        },
        "risk_shift": 0.04,
        "remote_bias": 0.18,
        "dropout_bias": 0.10,
        "coverage_base": 0.54,
        "latest_coverage_lift": 0.08,
    },
    "Chiang Mai": {
        "story": "northern highland access risk with targeted coverage expansion",
        "districts": {
            "Mae Rim": ["North Valley School", "Mae Rim Learning Center"],
            "Omkoi": ["Omkoi Highland School", "Mountain Path Academy"],
            "Fang": ["Fang Border School", "Northern Care School"],
        },
        "risk_shift": 0.10,
        "remote_bias": 0.28,
        "dropout_bias": 0.11,
        "coverage_base": 0.50,
        "latest_coverage_lift": 0.11,
    },
    "Chiang Rai": {
        "story": "border mobility and remote-area pressure in the north",
        "districts": {
            "Mae Sai": ["Northern Bridge School", "Mae Sai Border Academy"],
            "Mae Fah Luang": ["Doi Access School", "Highland Care School"],
            "Chiang Khong": ["Chiang Khong Learning Center", "Mekong North School"],
        },
        "risk_shift": 0.11,
        "remote_bias": 0.31,
        "dropout_bias": 0.12,
        "coverage_base": 0.49,
        "latest_coverage_lift": 0.07,
    },
    "Tak": {
        "story": "remote border learning centers with persistent access gaps",
        "districts": {
            "Mae Sot": ["Border Learning Center", "Mae Sot Bridge School"],
            "Umphang": ["Mountain Access School", "Umphang Highland Academy"],
            "Tha Song Yang": ["Salween Care School", "Northern Border School"],
        },
        "risk_shift": 0.18,
        "remote_bias": 0.40,
        "dropout_bias": 0.15,
        "coverage_base": 0.43,
        "latest_coverage_lift": 0.06,
    },
    "Mae Hong Son": {
        "story": "highest remote-area pressure with several critical trajectories",
        "districts": {
            "Pai": ["Highland Opportunity School", "Pai Valley School"],
            "Mae Sariang": ["Mae Sariang Care School", "Mountain Bridge School"],
            "Sop Moei": ["Sop Moei Access School", "Ridge Learning Center"],
        },
        "risk_shift": 0.20,
        "remote_bias": 0.46,
        "dropout_bias": 0.15,
        "coverage_base": 0.40,
        "latest_coverage_lift": 0.09,
    },
    "Pattani": {
        "story": "deep south attendance and dropout pressure",
        "districts": {
            "Mueang": ["Pattani Municipal School", "Pattani Care Academy"],
            "Sai Buri": ["Sai Buri Recovery School", "Coastal Care School"],
            "Yaring": ["Yaring Learning Center", "Southern Bridge School"],
        },
        "risk_shift": 0.17,
        "remote_bias": 0.08,
        "dropout_bias": 0.25,
        "coverage_base": 0.45,
        "latest_coverage_lift": 0.05,
    },
    "Narathiwat": {
        "story": "deep south dropout risk with attendance recovery starting late",
        "districts": {
            "Tak Bai": ["Narathiwat Care School", "Tak Bai Recovery School"],
            "Sungai Kolok": ["Kolok Bridge Academy", "Border Care School"],
            "Rueso": ["Rueso Opportunity School", "Southern Access Academy"],
        },
        "risk_shift": 0.19,
        "remote_bias": 0.10,
        "dropout_bias": 0.27,
        "coverage_base": 0.42,
        "latest_coverage_lift": 0.07,
    },
}

RISK_LABELS_TH = {"Low": "ต่ำ", "Medium": "ปานกลาง", "High": "สูง", "Critical": "วิกฤต"}
SEVERITY_ORDER = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}

KPI_DEFINITIONS = [
    (
        "risk_pulse",
        "Risk Pulse",
        "Average risk_score across filtered learners.",
        "AVG(risk_score)",
        "student_id count",
        "student",
        "risk_score, period, area filters",
    ),
    (
        "critical_alerts",
        "Critical Alerts",
        "Open or in-progress alerts with Critical severity.",
        "COUNT(alert_id WHERE severity='Critical' AND status!='Closed')",
        "alerts in current filter",
        "alert",
        "alerts.severity, alerts.status, alerts.period, alerts.province",
    ),
    (
        "coverage_gap",
        "Coverage Gap",
        "High/Critical learners not covered by a policy/program flag.",
        "COUNT(risk_score>=50) - SUM(program_coverage_flag)",
        "learners with risk_score >= 50",
        "province",
        "program_coverage_flag, risk_score",
    ),
    (
        "sla_open",
        "Open SLA",
        "Alerts that still require action before or after SLA due date.",
        "COUNT(alert_id WHERE status!='Closed')",
        "open alerts",
        "alert",
        "alerts.status, alerts.sla_due_at",
    ),
]

POLICY_PROGRAMS = [
    ("PRG-001", "ทุนเสมอภาค", "low_income; dropout risk", "nationwide", 7, "Active"),
    ("PRG-002", "Highland School Access", "remote area; disability", "North/Border provinces", 4, "Active"),
    ("PRG-003", "Attendance Recovery Team", "attendance below 80%", "priority districts", 5, "Pilot"),
]

DATA_SOURCES = [
    (
        "seed/demo",
        "Phase 1 seed dataset",
        "Demo CSV generated from sample_data()",
        "2026-08",
        1.0,
        0,
        "sample_data > normalize_columns > score_risk > generate_alerts",
        "demo-owner",
    )
]


def get_connection():
    return sqlite3.connect(DB_PATH)


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 120000).hex()


def add_column_if_missing(con, table: str, column: str, definition: str):
    existing = {row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    con = get_connection()
    con.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'executive'
        )"""
    )
    con.execute(
        """CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            student_id TEXT,
            province TEXT,
            risk_level TEXT,
            score REAL,
            message TEXT,
            status TEXT DEFAULT 'Open'
        )"""
    )
    for column, definition in {
        "district": "TEXT",
        "school_name": "TEXT",
        "period": "TEXT",
        "severity": "TEXT",
        "confidence": "REAL",
        "priority_score": "REAL",
        "trigger": "TEXT",
        "drivers": "TEXT",
        "evidence_refs": "TEXT",
        "source_id": "TEXT",
        "data_quality_flag": "TEXT",
        "rule_version": "TEXT",
        "model_version": "TEXT",
        "sla_due_at": "TEXT",
    }.items():
        add_column_if_missing(con, "alerts", column, definition)
    con.execute(
        """CREATE TABLE IF NOT EXISTS cases (
            case_id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id INTEGER NOT NULL,
            owner TEXT NOT NULL,
            status TEXT NOT NULL,
            action_note TEXT,
            due_at TEXT,
            resolved_at TEXT,
            outcome TEXT,
            created_at TEXT NOT NULL
        )"""
    )
    con.execute(
        """CREATE TABLE IF NOT EXISTS import_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL,
            period TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            row_count INTEGER NOT NULL,
            completeness REAL NOT NULL,
            freshness_days INTEGER NOT NULL,
            schema_status TEXT NOT NULL,
            data_quality_flag TEXT NOT NULL
        )"""
    )
    con.execute(
        """CREATE TABLE IF NOT EXISTS audit_logs (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_at TEXT NOT NULL,
            username TEXT,
            role TEXT,
            action TEXT NOT NULL,
            entity_type TEXT,
            entity_id TEXT,
            detail TEXT
        )"""
    )
    con.execute(
        """CREATE TABLE IF NOT EXISTS kpi_definitions (
            kpi_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            definition TEXT NOT NULL,
            formula TEXT NOT NULL,
            denominator TEXT NOT NULL,
            aggregation_level TEXT NOT NULL,
            source_fields TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    con.execute(
        """CREATE TABLE IF NOT EXISTS policy_programs (
            program_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            target_group TEXT NOT NULL,
            area_scope TEXT NOT NULL,
            coverage_count INTEGER NOT NULL,
            status TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    con.execute(
        """CREATE TABLE IF NOT EXISTS data_sources (
            source_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            refreshed_period TEXT NOT NULL,
            completeness REAL NOT NULL,
            freshness_days INTEGER NOT NULL,
            lineage TEXT NOT NULL,
            owner TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    seed_users(con)
    seed_reference_data(con)
    con.commit()
    con.close()


def seed_users(con):
    for username, password, role in [
        ("admin", "admin1234", "admin"),
        ("analyst", "analyst1234", "analyst"),
        ("executive", "exec1234", "executive"),
    ]:
        exists = con.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone()
        if not exists:
            salt = secrets.token_hex(16)
            con.execute(
                "INSERT INTO users(username,password_hash,salt,role) VALUES(?,?,?,?)",
                (username, hash_password(password, salt), salt, role),
            )


def seed_reference_data(con):
    now = datetime.now().isoformat(timespec="seconds")
    for row in KPI_DEFINITIONS:
        con.execute(
            """INSERT OR REPLACE INTO kpi_definitions(
                kpi_id,name,definition,formula,denominator,aggregation_level,source_fields,updated_at
            ) VALUES(?,?,?,?,?,?,?,?)""",
            (*row, now),
        )
    for row in POLICY_PROGRAMS:
        con.execute(
            """INSERT OR REPLACE INTO policy_programs(
                program_id,name,target_group,area_scope,coverage_count,status,updated_at
            ) VALUES(?,?,?,?,?,?,?)""",
            (*row, now),
        )
    for row in DATA_SOURCES:
        con.execute(
            """INSERT OR REPLACE INTO data_sources(
                source_id,name,description,refreshed_period,completeness,freshness_days,lineage,owner,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (*row, now),
        )


def current_user_context():
    user = st.session_state.get("user", {})
    return user.get("username"), user.get("role")


def log_event(action: str, entity_type: str = None, entity_id: str = None, detail: str = None, user: dict = None):
    username = user.get("username") if user else current_user_context()[0]
    role = user.get("role") if user else current_user_context()[1]
    con = get_connection()
    con.execute(
        """INSERT INTO audit_logs(event_at,username,role,action,entity_type,entity_id,detail)
           VALUES(?,?,?,?,?,?,?)""",
        (
            datetime.now().isoformat(timespec="seconds"),
            username,
            role,
            action,
            entity_type,
            str(entity_id) if entity_id is not None else None,
            detail,
        ),
    )
    con.commit()
    con.close()


def authenticate(username: str, password: str):
    con = get_connection()
    row = con.execute(
        "SELECT username,password_hash,salt,role FROM users WHERE username=?",
        (username,),
    ).fetchone()
    con.close()
    if not row:
        return None
    if hmac.compare_digest(hash_password(password, row[2]), row[1]):
        user = {"username": row[0], "role": row[3]}
        log_event("login_success", "user", row[0], "User authenticated", user=user)
        return user
    return None


def can_access(page: str) -> bool:
    return page in ROLE_PERMISSIONS.get(st.session_state.user["role"], set())


def mask_identifier(value) -> str:
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:8].upper()
    return f"MASKED-{digest}"


def should_mask_sensitive() -> bool:
    return st.session_state.get("user", {}).get("role") == "executive"


def mask_sensitive_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or not should_mask_sensitive():
        return df
    out = df.copy()
    if "student_id" in out.columns:
        out["student_id"] = out["student_id"].apply(mask_identifier)
    if "evidence_refs" in out.columns:
        out["evidence_refs"] = out["evidence_refs"].astype(str).str.replace(r"student:[^;]+; ?", "student:MASKED; ", regex=True)
    return out


def apply_up_theme():
    st.markdown(
        f"""
<style>
    :root {{
        --up-primary: {UP_PRIMARY};
        --up-primary-dark: {UP_PRIMARY_DARK};
        --up-accent: {UP_ACCENT};
        --up-bg: {UP_BG};
        --up-text: {UP_TEXT};
        --risk-low: {RISK_COLORS["Low"]};
        --risk-medium: {RISK_COLORS["Medium"]};
        --risk-high: {RISK_COLORS["High"]};
        --risk-critical: {RISK_COLORS["Critical"]};
    }}

    .stApp {{
        color: var(--up-text);
        background:
            linear-gradient(180deg, rgba(141, 56, 201, 0.08), rgba(255, 255, 255, 0) 220px),
            var(--up-bg);
        font-size: 16px;
    }}

    .block-container {{
        max-width: 1480px;
        padding-top: 2rem;
    }}

    .stApp::before {{
        content: "";
        position: fixed;
        inset: 0 0 auto 0;
        height: 6px;
        z-index: 999;
        background: linear-gradient(90deg, var(--up-primary) 0%, var(--up-primary) 70%, var(--up-accent) 70%, var(--up-accent) 100%);
    }}

    section[data-testid="stSidebar"] {{
        border-right: 1px solid rgba(141, 56, 201, 0.16);
        background: linear-gradient(180deg, #FFFFFF 0%, #F8F5FB 100%);
    }}

    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {{
        color: var(--up-primary-dark);
    }}

    .up-brand-lockup {{
        padding: 0.9rem 0.85rem 0.95rem;
        margin: 0.2rem 0 1rem;
        border-left: 5px solid var(--up-accent);
        border-radius: 8px;
        background: #FFFFFF;
        box-shadow: 0 10px 28px rgba(94, 35, 137, 0.08);
    }}

    .up-brand-lockup .product {{
        font-size: 1.24rem;
        line-height: 1.15;
        font-weight: 800;
        color: var(--up-primary-dark);
    }}

    .up-brand-lockup .institution {{
        margin-top: 0.2rem;
        font-size: 0.94rem;
        font-weight: 700;
        color: var(--up-primary);
    }}

    .up-brand-lockup .mission {{
        margin-top: 0.22rem;
        color: #5E6673;
        font-size: 0.86rem;
    }}

    .up-page-banner {{
        padding: 1.1rem 1.25rem 1rem;
        margin: 0 0 1.15rem;
        border-top: 4px solid var(--up-primary);
        border-bottom: 1px solid rgba(196, 153, 108, 0.38);
        border-radius: 8px;
        background: #FFFFFF;
        box-shadow: 0 14px 36px rgba(32, 35, 42, 0.06);
    }}

    .up-page-banner .eyebrow {{
        color: var(--up-accent);
        font-size: 0.75rem;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
    }}

    .up-page-banner h1 {{
        margin: 0.22rem 0 0;
        padding: 0;
        color: var(--up-primary-dark);
        font-size: 2.08rem;
        line-height: 1.18;
    }}

    .up-page-banner .subtitle {{
        margin-top: 0.35rem;
        color: #596171;
        font-size: 1.08rem;
        line-height: 1.45;
    }}

    .up-scope-strip {{
        display: grid;
        grid-template-columns: repeat(4, minmax(150px, 1fr));
        gap: 0.65rem;
        margin: -0.35rem 0 1.15rem;
    }}

    .up-scope-item {{
        padding: 0.8rem 0.95rem;
        border: 1px solid rgba(141, 56, 201, 0.14);
        border-left: 4px solid var(--up-accent);
        border-radius: 8px;
        background: #FFFFFF;
    }}

    .up-scope-item .label {{
        color: #5E6673;
        font-size: 0.82rem;
        font-weight: 800;
    }}

    .up-scope-item .value {{
        margin-top: 0.2rem;
        color: var(--up-primary-dark);
        font-size: 1.08rem;
        font-weight: 800;
    }}

    h1, h2, h3 {{
        color: var(--up-primary-dark);
        letter-spacing: 0;
    }}

    div[data-testid="stMetric"] {{
        padding: 0.9rem 1rem;
        border: 1px solid rgba(141, 56, 201, 0.13);
        border-top: 3px solid var(--up-accent);
        border-radius: 8px;
        background: #FFFFFF;
        box-shadow: 0 10px 24px rgba(32, 35, 42, 0.05);
    }}

    div[data-testid="stMetricLabel"] p {{
        color: #606875;
        font-weight: 700;
        font-size: 0.98rem;
    }}

    div[data-testid="stMetricValue"] {{
        color: var(--up-primary-dark);
        font-size: 2rem;
    }}

    .stButton > button,
    .stDownloadButton > button,
    button[kind="primary"] {{
        border-color: var(--up-primary);
        border-radius: 8px;
        font-weight: 700;
    }}

    button[kind="primary"],
    .stButton > button[kind="primary"] {{
        background: var(--up-primary);
        color: #FFFFFF;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 0.25rem;
        border-bottom: 1px solid rgba(141, 56, 201, 0.16);
    }}

    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px 8px 0 0;
        color: #535B68;
        font-weight: 700;
    }}

    .stTabs [aria-selected="true"] {{
        color: var(--up-primary-dark);
        border-bottom: 3px solid var(--up-accent);
        background: rgba(141, 56, 201, 0.06);
    }}

    div[data-testid="stDataFrame"] {{
        border: 1px solid rgba(141, 56, 201, 0.18);
        border-radius: 8px;
        overflow: hidden;
        background: #FFFFFF;
        box-shadow: 0 10px 22px rgba(94, 35, 137, 0.05);
    }}

    div[data-testid="stDataFrame"] [role="columnheader"] {{
        color: var(--up-primary-dark);
        font-weight: 800;
        font-size: 0.94rem;
        background: #F1E7F8;
        border-bottom: 1px solid rgba(196, 153, 108, 0.35);
    }}

    div[data-testid="stDataFrame"] [role="gridcell"] {{
        color: #252A33;
        font-size: 0.95rem;
        border-color: rgba(141, 56, 201, 0.08);
    }}

    div[data-testid="stDataFrame"] [role="row"]:nth-child(even) [role="gridcell"] {{
        background: #FBF8FD;
    }}

    div[data-testid="stAlert"] {{
        border-radius: 8px;
    }}

    [data-testid="stSidebarNav"],
    section[data-testid="stSidebar"] div[role="radiogroup"] {{
        gap: 0.16rem;
    }}

    .up-sidebar-menu-label {{
        margin: 1rem 0 0.45rem;
        color: var(--up-primary-dark);
        font-size: 0.9rem;
        font-weight: 800;
    }}

    .up-menu-active {{
        padding: 0.72rem 0.78rem;
        margin: 0.2rem 0 0.35rem;
        border-left: 4px solid var(--up-accent);
        border-radius: 8px;
        background: rgba(141, 56, 201, 0.10);
        color: var(--up-primary-dark);
        font-size: 0.98rem;
        font-weight: 800;
    }}

    .up-menu-active .menu-description {{
        margin-top: 0.2rem;
        color: #606875;
        font-size: 0.78rem;
        font-weight: 600;
        line-height: 1.35;
    }}

    .up-menu-group {{
        margin: 1rem 0 0.35rem;
        padding-top: 0.5rem;
        border-top: 1px solid rgba(141, 56, 201, 0.12);
        color: var(--up-primary-dark);
        font-size: 0.8rem;
        font-weight: 800;
    }}

    section[data-testid="stSidebar"] .stButton > button {{
        width: 100%;
        min-height: 44px;
        padding: 0.55rem 0.72rem;
        justify-content: flex-start;
        border: 1px solid rgba(141, 56, 201, 0.12);
        background: #FFFFFF;
        color: #4E5664;
        font-weight: 700;
        font-size: 0.92rem;
        text-align: left;
    }}

    section[data-testid="stSidebar"] .stButton > button:hover {{
        border-color: rgba(141, 56, 201, 0.35);
        background: rgba(141, 56, 201, 0.06);
        color: var(--up-primary-dark);
    }}
</style>
""",
        unsafe_allow_html=True,
    )


def render_sidebar_brand():
    st.sidebar.markdown(
        """
<div class="up-brand-lockup">
  <div class="product">EDU Sentinel</div>
  <div class="institution">University of Phayao</div>
  <div class="mission">Policy Intelligence &amp; Early Warning</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_page_banner(title: str, subtitle: str = "University of Phayao policy command center"):
    st.markdown(
        f"""
<section class="up-page-banner">
  <div class="eyebrow">University of Phayao</div>
  <h1>{title}</h1>
  <div class="subtitle">{subtitle}</div>
</section>
""",
        unsafe_allow_html=True,
    )


def render_sidebar_menu(allowed_pages: list) -> str:
    current = st.session_state.get("page")
    if current not in allowed_pages:
        current = allowed_pages[0]
        st.session_state.page = current

    st.sidebar.markdown('<div class="up-sidebar-menu-label">เลือกมุมมองงาน</div>', unsafe_allow_html=True)
    rendered = set()
    for group in MENU_GROUPS:
        group_pages = [page for page in allowed_pages if PAGE_METADATA.get(page, {}).get("group") == group]
        if not group_pages:
            continue
        st.sidebar.markdown(f'<div class="up-menu-group">{group}</div>', unsafe_allow_html=True)
        for menu_page in group_pages:
            meta = PAGE_METADATA.get(menu_page, {})
            label = meta.get("label", menu_page)
            description = meta.get("description", "")
            rendered.add(menu_page)
            if menu_page == current:
                st.sidebar.markdown(
                    f'<div class="up-menu-active">{label}<div class="menu-description">{description}</div></div>',
                    unsafe_allow_html=True,
                )
                continue
            if st.sidebar.button(label, key=f"nav_{menu_page}", width="stretch"):
                st.session_state.page = menu_page
                st.rerun()
    for menu_page in [page for page in allowed_pages if page not in rendered]:
        label = PAGE_METADATA.get(menu_page, {}).get("label", menu_page)
        if st.sidebar.button(label, key=f"nav_{menu_page}", width="stretch"):
            st.session_state.page = menu_page
            st.rerun()
    return st.session_state.page


def render_scope_summary(selected_period: str, selected_province: str, rows: int, alerts_count: int):
    period = "ทุกช่วงเวลา" if selected_period == "ทั้งหมด" else selected_period
    province = "ทุกพื้นที่" if selected_province == "ทั้งหมด" else selected_province
    st.markdown(
        f"""
<section class="up-scope-strip">
  <div class="up-scope-item"><div class="label">ช่วงข้อมูล</div><div class="value">{period}</div></div>
  <div class="up-scope-item"><div class="label">พื้นที่</div><div class="value">{province}</div></div>
  <div class="up-scope-item"><div class="label">จำนวนระเบียน</div><div class="value">{rows:,}</div></div>
  <div class="up-scope-item"><div class="label">Alert ในมุมมองนี้</div><div class="value">{alerts_count:,}</div></div>
</section>
""",
        unsafe_allow_html=True,
    )


def apply_chart_theme(fig):
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"color": UP_TEXT, "family": "Arial, sans-serif"},
        title={"font": {"color": UP_PRIMARY_DARK, "size": 18}},
        colorway=[UP_PRIMARY, UP_ACCENT, "#596171", "#A7B0BD"],
        margin={"l": 20, "r": 20, "t": 58, "b": 34},
    )
    fig.update_xaxes(gridcolor="rgba(141, 56, 201, 0.08)", zerolinecolor="rgba(141, 56, 201, 0.14)")
    fig.update_yaxes(gridcolor="rgba(141, 56, 201, 0.08)", zerolinecolor="rgba(141, 56, 201, 0.14)")
    return fig


def risk_cell_style(value) -> str:
    thai_to_level = {thai: level for level, thai in RISK_LABELS_TH.items()}
    color = RISK_COLORS.get(str(value)) or RISK_COLORS.get(thai_to_level.get(str(value)))
    if not color:
        return ""
    return f"color: {color}; background-color: {color}14; font-weight: 800;"


def style_up_dataframe(data):
    if not isinstance(data, pd.DataFrame):
        return data
    display_data = data.copy()
    for col in ["risk_level", "severity", "before_level", "after_level"]:
        if col in display_data.columns:
            display_data[col] = display_data[col].astype(str).replace(RISK_LABELS_TH)
    if "status" in display_data.columns:
        display_data["status"] = display_data["status"].astype(str).replace(
            {"Open": "เปิดอยู่", "In Progress": "กำลังดำเนินการ", "Closed": "ปิดแล้ว", "Active": "ใช้งาน", "Pilot": "นำร่อง"}
        )
    for col in ["dropout_risk_flag", "disability_flag", "remote_area_flag", "program_coverage_flag", "before_covered", "after_covered", "targeted"]:
        if col in display_data.columns:
            display_data[col] = display_data[col].replace({1: "ใช่", 0: "ไม่ใช่", True: "ใช่", False: "ไม่ใช่"})
    display_data = display_data.rename(columns=DISPLAY_COLUMN_LABELS)
    styler = display_data.style.set_table_styles(
        [
            {
                "selector": "thead th",
                "props": [
                    ("background-color", "#F1E7F8"),
                    ("color", UP_PRIMARY_DARK),
                    ("font-weight", "800"),
                    ("font-size", "15px"),
                    ("line-height", "1.35"),
                    ("border-bottom", f"1px solid {UP_ACCENT}66"),
                ],
            },
            {
                "selector": "tbody tr:nth-child(even)",
                "props": [("background-color", "#FBF8FD")],
            },
            {
                "selector": "tbody td",
                "props": [
                    ("border-color", "rgba(141, 56, 201, 0.08)"),
                    ("color", UP_TEXT),
                    ("font-size", "15px"),
                    ("line-height", "1.45"),
                ],
            },
        ]
    )
    risk_column_names = ["risk_level", "severity", "before_level", "after_level"]
    risk_columns = [
        DISPLAY_COLUMN_LABELS.get(col, col)
        for col in risk_column_names
        if DISPLAY_COLUMN_LABELS.get(col, col) in display_data.columns
    ]
    if risk_columns:
        if hasattr(styler, "map"):
            styler = styler.map(risk_cell_style, subset=risk_columns)
        else:
            styler = styler.applymap(risk_cell_style, subset=risk_columns)
    numeric_columns = display_data.select_dtypes(include="number").columns
    if len(numeric_columns):
        styler = styler.format(precision=1, thousands=",", subset=numeric_columns)
    return styler


def themed_dataframe(data, **kwargs):
    return st.dataframe(style_up_dataframe(data), **kwargs)


def weighted_choice(rng: random.Random, weights: dict):
    total = sum(weights.values())
    threshold = rng.random() * total
    running = 0.0
    for key, weight in weights.items():
        running += weight
        if running >= threshold:
            return key
    return next(reversed(weights))


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def demo_level_weights(profile: dict, month_index: int, school_pocket: bool) -> dict:
    base = {"Low": 0.375, "Medium": 0.420, "High": 0.115, "Critical": 0.090}
    shift = profile["risk_shift"] + (0.11 if school_pocket else 0)
    trend = (month_index - 2.5) * 0.012
    if "latest period" in profile["story"] or "improving" in profile["story"] or "recovery starting late" in profile["story"]:
        trend -= 0.055 if month_index >= 4 else 0
    weights = {
        "Low": base["Low"] - shift * 0.38 - trend,
        "Medium": base["Medium"] - shift * 0.08,
        "High": base["High"] + shift * 0.30 + trend * 0.72,
        "Critical": base["Critical"] + shift * 0.16 + trend * 0.28,
    }
    return {level: max(weight, 0.02) for level, weight in weights.items()}


def demo_metrics_for_level(rng: random.Random, level: str, remote: int, dropout: int, month_index: int) -> tuple:
    trend_gain = max(month_index - 3, 0)
    if level == "Low":
        attendance = rng.uniform(91, 99) + trend_gain * 0.4
        gpa = rng.uniform(2.85, 3.75) + trend_gain * 0.02
        income = rng.uniform(10500, 28000)
    elif level == "Medium":
        attendance = rng.uniform(74, 86) + trend_gain * 0.5
        gpa = rng.uniform(2.05, 2.75) + trend_gain * 0.02
        income = rng.uniform(4200, 12000)
    elif level == "High":
        attendance = rng.uniform(62, 76) + trend_gain * 0.35
        gpa = rng.uniform(1.45, 2.15) + trend_gain * 0.02
        income = rng.uniform(2200, 6500)
    else:
        attendance = rng.uniform(45, 55) + trend_gain * 0.25
        gpa = rng.uniform(1.00, 1.35) + trend_gain * 0.01
        income = rng.uniform(1000, 2800)
        dropout = 1

    if remote:
        attendance -= rng.uniform(1, 4)
        income -= rng.uniform(400, 1300)
    if dropout:
        attendance -= rng.uniform(1, 5)
        gpa -= rng.uniform(0.03, 0.16)

    return round(clamp(attendance, 45, 99), 1), round(clamp(gpa, 1.0, 4.0), 2), int(clamp(income, 1000, 35000))


def sample_data(seed: int = 202608, periods: list = None) -> pd.DataFrame:
    rng = random.Random(seed)
    periods = periods or DEMO_PERIODS
    rows = []
    student_no = 1

    for province, student_count in DEMO_STUDENTS_PER_PROVINCE.items():
        profile = DEMO_PROVINCE_PROFILES[province]
        district_names = list(profile["districts"].keys())
        for _ in range(student_count):
            student_id = f"STU-{student_no:05d}"
            student_no += 1
            district = rng.choice(district_names)
            school_name = rng.choice(profile["districts"][district])
            school_pocket = any(word in school_name for word in ["Opportunity", "Access", "Care", "Recovery", "Border", "Highland"])
            persistent_remote = int(rng.random() < profile["remote_bias"] + (0.12 if school_pocket else 0))
            persistent_disability = int(rng.random() < 0.055)
            base_dropout = int(rng.random() < profile["dropout_bias"] + (0.06 if school_pocket else 0))
            stability = rng.uniform(-0.06, 0.06)
            previous_level = None

            for month_index, period in enumerate(periods):
                weights = demo_level_weights(profile, month_index, school_pocket)
                weights["High"] += max(stability, 0)
                weights["Low"] += max(-stability, 0)
                target_level = weighted_choice(rng, weights)
                if previous_level is None or rng.random() < 0.30:
                    level = target_level
                else:
                    levels = ["Low", "Medium", "High", "Critical"]
                    current_idx = levels.index(previous_level)
                    target_idx = levels.index(target_level)
                    if abs(target_idx - current_idx) <= 1:
                        level = target_level
                    else:
                        step = 1 if target_idx > current_idx else -1
                        level = levels[current_idx + step]
                previous_level = level
                dropout = int(base_dropout or (level in ["High", "Critical"] and rng.random() < profile["dropout_bias"] + 0.20))
                remote = int(persistent_remote or (rng.random() < max(profile["remote_bias"] - 0.05, 0)))
                disability = int(persistent_disability or (level == "Critical" and rng.random() < 0.10))
                attendance, gpa, income = demo_metrics_for_level(rng, level, remote, dropout, month_index)
                coverage_chance = profile["coverage_base"]
                if level in ["High", "Critical"]:
                    coverage_chance -= 0.18
                if period in periods[-2:]:
                    coverage_chance += profile["latest_coverage_lift"]
                if remote and province in ["Chiang Mai", "Chiang Rai", "Tak", "Mae Hong Son"]:
                    coverage_chance -= 0.08
                program_coverage = int(rng.random() < clamp(coverage_chance, 0.18, 0.90))
                rows.append(
                    [
                        student_id,
                        province,
                        district,
                        school_name,
                        period,
                        attendance,
                        gpa,
                        income,
                        dropout,
                        disability,
                        remote,
                        program_coverage,
                    ]
                )

    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "student_id": ["student_id", "studentid", "id", "รหัสนักเรียน"],
        "province": ["province", "จังหวัด"],
        "district": ["district", "อำเภอ", "เขต"],
        "school_name": ["school_name", "school", "โรงเรียน"],
        "period": ["period", "เดือนข้อมูล", "รอบข้อมูล"],
        "attendance_rate": ["attendance_rate", "attendance", "อัตราเข้าเรียน"],
        "gpa": ["gpa", "grade", "เกรดเฉลี่ย"],
        "income_per_month": ["income_per_month", "income", "รายได้ครัวเรือน"],
        "dropout_risk_flag": ["dropout_risk_flag", "dropout_flag", "เสี่ยงหลุดระบบ"],
        "disability_flag": ["disability_flag", "disability", "พิการ"],
        "remote_area_flag": ["remote_area_flag", "remote_area", "พื้นที่ห่างไกล"],
        "program_coverage_flag": ["program_coverage_flag", "covered", "มีมาตรการครอบคลุม"],
    }
    names = {str(c).strip().lower(): c for c in df.columns}
    rename = {}
    for target, options in aliases.items():
        for option in options:
            if option.lower() in names:
                rename[names[option.lower()]] = target
                break
    df = df.rename(columns=rename).copy()
    defaults = {
        "student_id": None,
        "province": "Bangkok",
        "district": "Mueang",
        "school_name": "Demo School",
        "period": datetime.now().strftime("%Y-%m"),
        "attendance_rate": 100.0,
        "gpa": 3.0,
        "income_per_month": 15000.0,
        "dropout_risk_flag": 0,
        "disability_flag": 0,
        "remote_area_flag": 0,
        "program_coverage_flag": 0,
    }
    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = [f"STU-{i + 1:05d}" for i in range(len(df))] if col == "student_id" else val
    for col in ["attendance_rate", "gpa", "income_per_month"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["attendance_rate"] = df["attendance_rate"].clip(0, 100).fillna(100)
    df["gpa"] = df["gpa"].clip(0, 4).fillna(3)
    df["income_per_month"] = df["income_per_month"].clip(lower=0).fillna(15000)
    for col in ["dropout_risk_flag", "disability_flag", "remote_area_flag", "program_coverage_flag"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).clip(0, 1).astype(int)
    for col in ["student_id", "province", "district", "school_name", "period"]:
        df[col] = df[col].fillna(defaults.get(col) or "").astype(str).str.strip()
        df.loc[df[col] == "", col] = defaults.get(col) or "unknown"
    return df[REQUIRED_COLUMNS]


def validate_schema(raw: pd.DataFrame):
    normalized = {str(c).strip().lower() for c in raw.columns}
    checks = {
        "province": {"province", "จังหวัด"},
        "attendance_rate": {"attendance_rate", "attendance", "อัตราเข้าเรียน"},
        "gpa": {"gpa", "grade", "เกรดเฉลี่ย"},
        "income_per_month": {"income_per_month", "income", "รายได้ครัวเรือน"},
    }
    missing = [field for field, options in checks.items() if not normalized.intersection(options)]
    return ("pass" if not missing else "warning"), missing


def build_drivers(row) -> str:
    drivers = []
    if row["attendance_rate"] < 80:
        drivers.append(f"attendance {row['attendance_rate']:.0f}%")
    if row["gpa"] < 2.3:
        drivers.append(f"GPA {row['gpa']:.2f}")
    if row["income_per_month"] < 8000:
        drivers.append(f"income {row['income_per_month']:.0f} THB")
    if row["dropout_risk_flag"]:
        drivers.append("dropout flag")
    if row["disability_flag"]:
        drivers.append("disability flag")
    if row["remote_area_flag"]:
        drivers.append("remote area")
    if not row["program_coverage_flag"] and row["risk_score"] >= 50:
        drivers.append("coverage gap")
    return "; ".join(drivers) or "baseline monitoring"


def data_quality_flag(row) -> str:
    warnings = []
    if row["attendance_rate"] in (0, 100):
        warnings.append("attendance boundary")
    if row["income_per_month"] == 0:
        warnings.append("income missing/zero")
    if row["school_name"] == "Demo School":
        warnings.append("default school")
    return "OK" if not warnings else ", ".join(warnings)


def score_risk(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    score = pd.Series(0.0, index=out.index)
    score += ((100 - out["attendance_rate"]).clip(lower=0) * 0.9).clip(upper=35)
    score += ((2.5 - out["gpa"]).clip(lower=0) * 12).clip(upper=25)
    score += ((8000 - out["income_per_month"]).clip(lower=0) / 8000 * 20).clip(upper=20)
    score += out["dropout_risk_flag"].clip(0, 1) * 10
    score += out["disability_flag"].clip(0, 1) * 5
    score += out["remote_area_flag"].clip(0, 1) * 5
    out["risk_score"] = score.round(1).clip(0, 100)
    out["risk_level"] = pd.cut(
        out["risk_score"],
        bins=[-1, 24.9, 49.9, 74.9, 100],
        labels=["Low", "Medium", "High", "Critical"],
    ).astype(str)
    out["drivers"] = [build_drivers(row) for _, row in out.iterrows()]
    out["confidence"] = 0.95
    out["source_id"] = "seed/demo"
    out["data_quality_flag"] = [data_quality_flag(row) for _, row in out.iterrows()]
    return out


def record_import_run(source_name: str, df: pd.DataFrame, schema_status: str, quality_flag: str):
    completeness = float(df[REQUIRED_COLUMNS].notna().mean().mean()) if not df.empty else 0
    latest_period = sorted(df["period"].astype(str).unique())[-1] if not df.empty else datetime.now().strftime("%Y-%m")
    try:
        period_date = datetime.strptime(latest_period + "-01", "%Y-%m-%d")
        freshness_days = max((datetime.now() - period_date).days, 0)
    except ValueError:
        freshness_days = 999
    con = get_connection()
    con.execute(
        """INSERT INTO import_runs(source_name,period,imported_at,row_count,completeness,freshness_days,schema_status,data_quality_flag)
           VALUES(?,?,?,?,?,?,?,?)""",
        (
            source_name,
            latest_period,
            datetime.now().isoformat(timespec="seconds"),
            len(df),
            round(completeness, 3),
            freshness_days,
            schema_status,
            quality_flag,
        ),
    )
    con.commit()
    con.close()
    log_event(
        "data_import_recorded",
        "import_run",
        source_name,
        f"rows={len(df)}; period={latest_period}; schema={schema_status}; quality={quality_flag}",
    )


def generate_alerts(df: pd.DataFrame):
    con = get_connection()
    now = datetime.now().isoformat(timespec="seconds")
    risky = df[df["risk_level"].isin(["High", "Critical"])]
    for _, row in risky.iterrows():
        exists = con.execute(
            "SELECT 1 FROM alerts WHERE student_id=? AND period=? AND status IN ('Open','In Progress')",
            (str(row["student_id"]), str(row["period"])),
        ).fetchone()
        if exists:
            continue
        severity = str(row["risk_level"])
        priority_score = round(float(row["risk_score"]) * SEVERITY_ORDER[severity] / 4, 1)
        trigger = f"{RULE_VERSION}: score {row['risk_score']:.1f} reached {severity} threshold"
        evidence_refs = f"student:{row['student_id']}; period:{row['period']}; source:{row['source_id']}; province:{row['province']}"
        message = f"พบความเสี่ยงระดับ {RISK_LABELS_TH[severity]} ใน {row['school_name']} จากปัจจัย {row['drivers']}"
        con.execute(
            """INSERT INTO alerts(
                created_at,student_id,province,district,school_name,period,risk_level,score,message,status,
                severity,confidence,priority_score,trigger,drivers,evidence_refs,source_id,data_quality_flag,
                rule_version,model_version,sla_due_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                now,
                str(row["student_id"]),
                str(row["province"]),
                str(row["district"]),
                str(row["school_name"]),
                str(row["period"]),
                severity,
                float(row["risk_score"]),
                message,
                "Open",
                severity,
                float(row["confidence"]),
                priority_score,
                trigger,
                str(row["drivers"]),
                evidence_refs,
                str(row["source_id"]),
                str(row["data_quality_flag"]),
                RULE_VERSION,
                MODEL_VERSION,
                (datetime.now() + timedelta(days=7 if severity == "Critical" else 14)).date().isoformat(),
            ),
        )
    con.commit()
    con.close()


def ensure_seed_state():
    if "data" not in st.session_state:
        st.session_state.data = score_risk(sample_data())
        record_import_run("seed/demo", st.session_state.data, "pass", "OK")
        generate_alerts(st.session_state.data)


def load_table(table: str) -> pd.DataFrame:
    con = get_connection()
    df = pd.read_sql_query(f"SELECT * FROM {table}", con)
    con.close()
    return df


def load_alerts() -> pd.DataFrame:
    alerts = load_table("alerts")
    if alerts.empty:
        return alerts
    return alerts.sort_values(["priority_score", "id"], ascending=[False, False])


def update_alert_status(alert_id: int, status: str):
    con = get_connection()
    con.execute("UPDATE alerts SET status=? WHERE id=?", (status, alert_id))
    con.commit()
    con.close()
    log_event("alert_status_updated", "alert", alert_id, f"status={status}")


def create_case(alert_id: int, owner: str, due_at, action_note: str):
    con = get_connection()
    con.execute(
        """INSERT INTO cases(alert_id,owner,status,action_note,due_at,created_at)
           VALUES(?,?,?,?,?,?)""",
        (alert_id, owner, "Open", action_note, str(due_at), datetime.now().isoformat(timespec="seconds")),
    )
    con.execute("UPDATE alerts SET status='In Progress' WHERE id=?", (alert_id,))
    con.commit()
    con.close()
    log_event("case_created", "alert", alert_id, f"owner={owner}; due_at={due_at}; note={action_note[:120]}")


def update_case(case_id: int, status: str, outcome: str):
    con = get_connection()
    resolved_at = datetime.now().isoformat(timespec="seconds") if status == "Closed" else None
    con.execute(
        "UPDATE cases SET status=?, outcome=?, resolved_at=COALESCE(?, resolved_at) WHERE case_id=?",
        (status, outcome, resolved_at, case_id),
    )
    con.commit()
    con.close()
    log_event("case_updated", "case", case_id, f"status={status}; outcome={outcome[:120]}")


def apply_filters(df: pd.DataFrame):
    st.sidebar.divider()
    st.sidebar.subheader("ตัวกรองมุมมอง")
    periods = ["ทั้งหมด"] + sorted(df["period"].dropna().astype(str).unique().tolist(), reverse=True)
    provinces = ["ทั้งหมด"] + sorted(df["province"].dropna().astype(str).unique().tolist())
    selected_period = st.sidebar.selectbox("ช่วงข้อมูล", periods)
    selected_province = st.sidebar.selectbox("พื้นที่/จังหวัด", provinces)
    filtered = df.copy()
    if selected_period != "ทั้งหมด":
        filtered = filtered[filtered["period"] == selected_period]
    if selected_province != "ทั้งหมด":
        filtered = filtered[filtered["province"] == selected_province]
    return filtered, selected_period, selected_province


def coverage_gap(df: pd.DataFrame) -> pd.DataFrame:
    risky = df[df["risk_score"] >= 50]
    if risky.empty:
        return pd.DataFrame(columns=["province", "risk_people", "covered", "coverage_gap", "gap_rate"])
    out = risky.groupby("province", as_index=False).agg(risk_people=("student_id", "count"), covered=("program_coverage_flag", "sum"))
    out["coverage_gap"] = out["risk_people"] - out["covered"]
    out["gap_rate"] = (out["coverage_gap"] / out["risk_people"] * 100).round(1)
    return out.sort_values(["coverage_gap", "gap_rate"], ascending=False)


def what_changed(df: pd.DataFrame) -> pd.DataFrame:
    periods = sorted(df["period"].dropna().astype(str).unique())
    if len(periods) < 2:
        return pd.DataFrame(columns=["province", "previous_risk", "current_risk", "change"])
    previous, current = periods[-2], periods[-1]
    prev = df[df["period"] == previous].groupby("province")["risk_score"].mean()
    curr = df[df["period"] == current].groupby("province")["risk_score"].mean()
    out = pd.concat([prev.rename("previous_risk"), curr.rename("current_risk")], axis=1).fillna(0).reset_index()
    out["change"] = (out["current_risk"] - out["previous_risk"]).round(1)
    return out.sort_values("change", ascending=False)


def scenario_target_mask(df: pd.DataFrame, target_group: str) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=bool)
    if target_group == "High/Critical with coverage gap":
        return (df["risk_score"] >= 50) & (df["program_coverage_flag"] == 0)
    if target_group == "Critical only":
        return df["risk_level"] == "Critical"
    if target_group == "Attendance below 80%":
        return df["attendance_rate"] < 80
    if target_group == "Remote or disability":
        return (df["remote_area_flag"] == 1) | (df["disability_flag"] == 1)
    return df["risk_score"] >= 50


def simulate_policy_impact(
    df: pd.DataFrame,
    target_group: str,
    attendance_gain: float,
    gpa_gain: float,
    income_support: float,
    new_coverage_slots: int,
):
    base = df.copy()
    simulated = base.copy()
    target = scenario_target_mask(simulated, target_group)

    simulated.loc[target, "attendance_rate"] = (simulated.loc[target, "attendance_rate"] + attendance_gain).clip(0, 100)
    simulated.loc[target, "gpa"] = (simulated.loc[target, "gpa"] + gpa_gain).clip(0, 4)
    simulated.loc[target, "income_per_month"] = (simulated.loc[target, "income_per_month"] + income_support).clip(lower=0)

    uncovered_target = simulated[target & (simulated["program_coverage_flag"] == 0)].sort_values("risk_score", ascending=False)
    coverage_ids = uncovered_target.head(int(new_coverage_slots)).index
    simulated.loc[coverage_ids, "program_coverage_flag"] = 1
    simulated = score_risk(simulated)

    comparison = base[["student_id", "province", "school_name", "risk_score", "risk_level", "program_coverage_flag"]].copy()
    comparison = comparison.rename(
        columns={
            "risk_score": "before_score",
            "risk_level": "before_level",
            "program_coverage_flag": "before_covered",
        }
    )
    comparison["after_score"] = simulated["risk_score"]
    comparison["after_level"] = simulated["risk_level"]
    comparison["after_covered"] = simulated["program_coverage_flag"]
    comparison["risk_delta"] = (comparison["after_score"] - comparison["before_score"]).round(1)
    comparison["targeted"] = target

    before_risky = int((base["risk_score"] >= 50).sum()) if not base.empty else 0
    after_risky = int((simulated["risk_score"] >= 50).sum()) if not simulated.empty else 0
    before_critical = int((base["risk_level"] == "Critical").sum()) if not base.empty else 0
    after_critical = int((simulated["risk_level"] == "Critical").sum()) if not simulated.empty else 0
    before_gap = int(coverage_gap(base)["coverage_gap"].sum()) if not coverage_gap(base).empty else 0
    after_gap = int(coverage_gap(simulated)["coverage_gap"].sum()) if not coverage_gap(simulated).empty else 0

    impact = {
        "targeted": int(target.sum()) if not target.empty else 0,
        "new_coverage": int(len(coverage_ids)),
        "risk_people_before": before_risky,
        "risk_people_after": after_risky,
        "risk_people_reduced": before_risky - after_risky,
        "critical_before": before_critical,
        "critical_after": after_critical,
        "critical_reduced": before_critical - after_critical,
        "coverage_gap_before": before_gap,
        "coverage_gap_after": after_gap,
        "coverage_gap_reduced": before_gap - after_gap,
        "avg_risk_before": round(float(base["risk_score"].mean()), 1) if not base.empty else 0,
        "avg_risk_after": round(float(simulated["risk_score"].mean()), 1) if not simulated.empty else 0,
    }

    province_impact = base.groupby("province", as_index=False).agg(
        before_avg_risk=("risk_score", "mean"),
        before_risk_people=("risk_score", lambda s: int((s >= 50).sum())),
        before_critical=("risk_level", lambda s: int((s == "Critical").sum())),
    )
    after_province = simulated.groupby("province", as_index=False).agg(
        after_avg_risk=("risk_score", "mean"),
        after_risk_people=("risk_score", lambda s: int((s >= 50).sum())),
        after_critical=("risk_level", lambda s: int((s == "Critical").sum())),
    )
    province_impact = province_impact.merge(after_province, on="province", how="outer").fillna(0)
    province_impact["avg_risk_delta"] = (province_impact["after_avg_risk"] - province_impact["before_avg_risk"]).round(1)
    province_impact["risk_people_reduced"] = province_impact["before_risk_people"] - province_impact["after_risk_people"]
    province_impact["critical_reduced"] = province_impact["before_critical"] - province_impact["after_critical"]
    province_impact["before_avg_risk"] = province_impact["before_avg_risk"].round(1)
    province_impact["after_avg_risk"] = province_impact["after_avg_risk"].round(1)

    return simulated, comparison, province_impact.sort_values(["risk_people_reduced", "avg_risk_delta"], ascending=[False, True]), impact


def executive_summary_sections(df: pd.DataFrame, alerts: pd.DataFrame, selected_period: str, selected_province: str):
    n = len(df)
    high = int((df["risk_level"] == "High").sum()) if n else 0
    critical = int((df["risk_level"] == "Critical").sum()) if n else 0
    pct = ((high + critical) / n * 100) if n else 0
    top = df.groupby("province")["risk_score"].mean().sort_values(ascending=False).head(3) if n else pd.Series(dtype=float)
    top_text = ", ".join([f"{p} ({s:.1f})" for p, s in top.items()]) or "-"
    open_alerts = int((alerts["status"] != "Closed").sum()) if not alerts.empty else 0
    gap = coverage_gap(df)
    top_gap = gap.iloc[0]["province"] if not gap.empty else "-"
    scope = f"period={selected_period}, area={selected_province}"
    return {
        "Answer": f"จากข้อมูล {n:,} ราย พบ High {high:,} และ Critical {critical:,} ราย ({pct:.1f}%) โดยมี alert ที่ยังไม่ปิด {open_alerts:,} รายการ.",
        "Evidence": f"พื้นที่คะแนนเสี่ยงเฉลี่ยสูงสุด: {top_text}. Coverage gap สูงสุด: {top_gap}. Citations: filtered_dataset:{scope}; alert_table:{len(alerts)} records; rule_version:{RULE_VERSION}.",
        "Why": "ปัจจัยหลักมาจากการเข้าเรียนต่ำ, GPA ต่ำ, รายได้ครัวเรือนเปราะบาง, dropout flag และพื้นที่ที่ยังไม่มีมาตรการครอบคลุมสำหรับกลุ่มเสี่ยง.",
        "Limitations": "MVP ใช้ข้อมูล seed/import ล่าสุดและ rule-based model เท่านั้น ยังไม่ใช่การตัดสินสิทธิรายบุคคล และต้องตรวจ data lineage ก่อนใช้เพื่อกำหนดมาตรการจริง.",
        "Next Action": "ให้เปิด case สำหรับ Critical alerts, ตรวจ coverage gap รายจังหวัด, มอบหมาย owner พร้อม SLA และทบทวนผลรายสัปดาห์.",
    }


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="RiskData")
        load_alerts().to_excel(writer, index=False, sheet_name="Alerts")
        load_table("cases").to_excel(writer, index=False, sheet_name="Cases")
        load_table("import_runs").to_excel(writer, index=False, sheet_name="DataHealth")
    return output.getvalue()


def report_html(df: pd.DataFrame, alerts: pd.DataFrame, sections: dict) -> str:
    sections_html = "".join(f"<h2>{k}</h2><p>{v}</p>" for k, v in sections.items())
    alerts_html = alerts.head(50).to_html(index=False) if not alerts.empty else "<p>No alerts.</p>"
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>EDU Sentinel Executive Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #172033; }}
    h1 {{ color: {UP_PRIMARY_DARK}; border-top: 4px solid {UP_PRIMARY}; padding-top: 12px; }}
    h2 {{ margin-top: 24px; color: {UP_PRIMARY_DARK}; border-bottom: 1px solid {UP_ACCENT}; padding-bottom: 4px; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 12px; margin-top: 12px; }}
    th, td {{ border: 1px solid #d4dbe5; padding: 6px; text-align: left; }}
    th {{ background: #f3eaf9; color: {UP_PRIMARY_DARK}; }}
    .meta {{ color: #52616f; }}
  </style>
</head>
<body>
  <h1>EDU Sentinel Executive Report</h1>
  <p class="meta">Generated {datetime.now().isoformat(timespec="seconds")} | model {MODEL_VERSION} | prompt {PROMPT_VERSION}</p>
  {sections_html}
  <h2>Top Risk Records</h2>
  {df.sort_values("risk_score", ascending=False).head(30).to_html(index=False)}
  <h2>Alerts</h2>
  {alerts_html}
</body>
</html>"""


def render_login():
    render_page_banner("EDU Sentinel", "University of Phayao | Policy Intelligence & Early Warning")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("เข้าสู่ระบบ", width="stretch")
    if submit:
        user = authenticate(username, password)
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    st.info("Demo: admin/admin1234, analyst/analyst1234, executive/exec1234")


def command_center(df: pd.DataFrame, alerts: pd.DataFrame, selected_period: str, selected_province: str):
    render_page_banner("ภาพรวมผู้บริหาร", "ดูสัญญาณสำคัญเพื่อจัดลำดับพื้นที่ มาตรการ และการติดตามเชิงนโยบาย")
    total = len(df)
    critical = int((df.risk_level == "Critical").sum()) if total else 0
    high = int((df.risk_level == "High").sum()) if total else 0
    avg = df.risk_score.mean() if total else 0
    open_alerts = int((alerts.status != "Closed").sum()) if not alerts.empty else 0
    render_scope_summary(selected_period, selected_province, total, len(alerts))

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("ผู้เรียนในมุมมองนี้", f"{total:,}")
    c2.metric("วิกฤต ต้องเร่งติดตาม", f"{critical:,}")
    c3.metric("เสี่ยงสูง", f"{high:,}")
    c4.metric("คะแนนเสี่ยงเฉลี่ย", f"{avg:.1f}/100")
    c5.metric("Alert ที่ยังไม่ปิด", f"{open_alerts:,}")
    st.info("อ่านจากซ้ายไปขวา: ขนาดปัญหา, กลุ่มเร่งด่วน, ระดับความเสี่ยงเฉลี่ย, และงานที่ยังต้องติดตาม")

    left, right = st.columns([1, 1])
    with left:
        counts = df.risk_level.value_counts().reindex(["Low", "Medium", "High", "Critical"], fill_value=0).reset_index()
        counts.columns = ["risk_level", "count"]
        fig = px.bar(
            counts,
            x="risk_level",
            y="count",
            title="สัดส่วนระดับความเสี่ยง",
            text="count",
            color="risk_level",
            color_discrete_map=RISK_COLORS,
        )
        st.plotly_chart(apply_chart_theme(fig), width="stretch")
    with right:
        trend = what_changed(st.session_state.data)
        if trend.empty:
            prov = df.groupby("province", as_index=False).agg(avg_risk=("risk_score", "mean"), people=("student_id", "count"))
            fig2 = px.bar(prov.sort_values("avg_risk", ascending=False).head(10), x="avg_risk", y="province", orientation="h", title="จังหวัดที่มีคะแนนเสี่ยงเฉลี่ยสูง")
        else:
            fig2 = px.bar(trend.head(10), x="change", y="province", orientation="h", title="พื้นที่ที่เปลี่ยนแปลงจากรอบก่อน")
        fig2.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(apply_chart_theme(fig2), width="stretch")

    gap = coverage_gap(df)
    a, b = st.columns([1, 1])
    with a:
        st.subheader("Alert ที่ควรดูเป็นลำดับแรก")
        cols = ["id", "severity", "province", "school_name", "score", "priority_score", "status", "sla_due_at"]
        themed_dataframe(alerts[cols].head(10) if not alerts.empty else pd.DataFrame(columns=cols), width="stretch", hide_index=True)
    with b:
        st.subheader("ช่องว่างมาตรการ")
        themed_dataframe(gap.head(10), width="stretch", hide_index=True)

    st.subheader("ที่มาและความน่าเชื่อถือของข้อมูล")
    themed_dataframe(load_table("import_runs").sort_values("run_id", ascending=False).head(5), width="stretch", hide_index=True)
    with st.expander("KPI Dictionary"):
        themed_dataframe(load_table("kpi_definitions"), width="stretch", hide_index=True)
    with st.expander("Data Sources & Lineage"):
        themed_dataframe(load_table("data_sources"), width="stretch", hide_index=True)


def operations_dashboard(df: pd.DataFrame, alerts: pd.DataFrame, selected_period: str, selected_province: str):
    render_page_banner("ติดตามสถานการณ์", "ดูแนวโน้มรายเดือน ภาระงานพื้นที่ และสถานศึกษาที่ควรติดตาม")

    if df.empty:
        st.info("ไม่มีข้อมูลตามตัวกรองที่เลือก")
        return

    latest_period = sorted(df["period"].dropna().astype(str).unique())[-1]
    focus_period = latest_period if selected_period == "ทั้งหมด" else selected_period
    focus_df = df[df["period"] == focus_period] if selected_period == "ทั้งหมด" else df
    risky = focus_df[focus_df["risk_level"].isin(["High", "Critical"])]
    coverage = int(risky["program_coverage_flag"].sum()) if not risky.empty else 0
    coverage_rate = (coverage / len(risky) * 100) if len(risky) else 0
    open_alerts = int((alerts["status"] != "Closed").sum()) if not alerts.empty else 0
    critical_alerts = int((alerts["severity"] == "Critical").sum()) if not alerts.empty and "severity" in alerts.columns else 0
    render_scope_summary(selected_period, selected_province, len(focus_df), len(alerts))

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("ผู้เรียนรอบปัจจุบัน", f"{len(focus_df):,}", f"รอบ {focus_period}")
    k2.metric("เสี่ยงสูง/วิกฤต", f"{len(risky):,}", f"{(len(risky) / len(focus_df) * 100):.1f}%")
    k3.metric("มาตรการครอบคลุม", f"{coverage_rate:.1f}%")
    k4.metric("Alert เปิดอยู่", f"{open_alerts:,}")
    k5.metric("Alert วิกฤต", f"{critical_alerts:,}")

    trend_base = st.session_state.data.copy()
    if selected_province != "ทั้งหมด":
        trend_base = trend_base[trend_base["province"] == selected_province]
    monthly = trend_base.groupby("period", as_index=False).agg(
        avg_risk=("risk_score", "mean"),
        learners=("student_id", "count"),
        high=("risk_level", lambda s: int((s == "High").sum())),
        critical=("risk_level", lambda s: int((s == "Critical").sum())),
        covered=("program_coverage_flag", "sum"),
    )
    monthly["high_critical"] = monthly["high"] + monthly["critical"]
    monthly["coverage_rate"] = (monthly["covered"] / monthly["high_critical"].replace(0, pd.NA) * 100).fillna(0).round(1)

    left, right = st.columns([1.2, 1])
    with left:
        fig = px.line(
            monthly,
            x="period",
            y=["avg_risk", "high_critical"],
            markers=True,
            title="แนวโน้มคะแนนเสี่ยงและจำนวนกลุ่มเสี่ยงสูง/วิกฤต",
        )
        fig.update_layout(legend_title_text="", yaxis_title="Score / learners")
        st.plotly_chart(apply_chart_theme(fig), width="stretch")
    with right:
        mix = focus_df["risk_level"].value_counts().reindex(["Low", "Medium", "High", "Critical"], fill_value=0).reset_index()
        mix.columns = ["risk_level", "learners"]
        fig = px.pie(
            mix,
            names="risk_level",
            values="learners",
            hole=0.45,
            title=f"สัดส่วนความเสี่ยง: {focus_period}",
            color="risk_level",
            color_discrete_map=RISK_COLORS,
        )
        st.plotly_chart(apply_chart_theme(fig), width="stretch")

    p1, p2 = st.columns([1.1, 1])
    with p1:
        province = focus_df.groupby("province", as_index=False).agg(
            avg_risk=("risk_score", "mean"),
            learners=("student_id", "count"),
            high=("risk_level", lambda s: int((s == "High").sum())),
            critical=("risk_level", lambda s: int((s == "Critical").sum())),
            covered=("program_coverage_flag", "sum"),
        )
        province["risk_load"] = province["high"] + province["critical"]
        province["coverage_gap"] = (province["risk_load"] - province["covered"]).clip(lower=0)
        province["avg_risk"] = province["avg_risk"].round(1)
        province_view = province.sort_values(["risk_load", "avg_risk"], ascending=False).head(10)
        fig = px.bar(
            province_view,
            x="risk_load",
            y="province",
            orientation="h",
            color="coverage_gap",
            title="ภาระความเสี่ยงและช่องว่างมาตรการรายจังหวัด",
            text="risk_load",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, xaxis_title="High/Critical learners")
        st.plotly_chart(apply_chart_theme(fig), width="stretch")
    with p2:
        st.subheader("ตารางจังหวัดเพื่อจัดลำดับการติดตาม")
        themed_dataframe(
            province.sort_values(["coverage_gap", "risk_load"], ascending=False)[
                ["province", "learners", "avg_risk", "risk_load", "critical", "coverage_gap"]
            ],
            width="stretch",
            hide_index=True,
        )

    w1, w2 = st.columns([1, 1])
    with w1:
        st.subheader("สถานศึกษาที่ควรติดตาม")
        school = focus_df.groupby(["province", "district", "school_name"], as_index=False).agg(
            avg_risk=("risk_score", "mean"),
            learners=("student_id", "count"),
            high=("risk_level", lambda s: int((s == "High").sum())),
            critical=("risk_level", lambda s: int((s == "Critical").sum())),
            uncovered=("program_coverage_flag", lambda s: int((s == 0).sum())),
        )
        school["risk_load"] = school["high"] + school["critical"]
        school["avg_risk"] = school["avg_risk"].round(1)
        themed_dataframe(
            school.sort_values(["critical", "risk_load", "avg_risk"], ascending=False).head(12),
            width="stretch",
            hide_index=True,
        )
    with w2:
        st.subheader("ภาระงาน Alert รายพื้นที่")
        if alerts.empty:
            st.info("ยังไม่มี alert ตามตัวกรอง")
        else:
            workload = alerts.groupby(["province", "severity"], as_index=False).agg(alerts=("id", "count"))
            fig = px.bar(
                workload,
                x="province",
                y="alerts",
                color="severity",
                title="จำนวน Alert แยกตามจังหวัดและความรุนแรง",
                color_discrete_map=RISK_COLORS,
            )
            fig.update_layout(xaxis_title="", yaxis_title="Alerts")
            st.plotly_chart(apply_chart_theme(fig), width="stretch")


def data_import():
    render_page_banner("Data Import", "Validated ingestion for educational equity risk data")
    st.write("รองรับ CSV/Excel พร้อม schema validation, import status, source/period และ data quality metadata")
    uploaded = st.file_uploader("เลือกไฟล์", type=["csv", "xlsx", "xls"])
    if uploaded:
        try:
            raw = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
            schema_status, missing = validate_schema(raw)
            scored = score_risk(normalize_columns(raw))
            quality_flag = "OK" if (scored["data_quality_flag"] == "OK").mean() >= 0.8 else "Needs review"
            st.success(f"อ่านข้อมูลสำเร็จ {len(scored):,} ราย | schema={schema_status} | quality={quality_flag}")
            if missing:
                st.warning(f"คอลัมน์สำคัญที่ไม่พบและถูกเติมค่า default: {', '.join(missing)}")
            themed_dataframe(scored.head(50), width="stretch", hide_index=True)
            if st.button("นำข้อมูลเข้าสู่ระบบ", type="primary"):
                st.session_state.data = scored
                record_import_run(uploaded.name, scored, schema_status, quality_flag)
                generate_alerts(scored)
                st.success("นำเข้าข้อมูลและประมวลผลความเสี่ยงแล้ว")
        except Exception as exc:
            st.error(f"ไม่สามารถอ่านไฟล์ได้: {exc}")
    st.download_button(
        "ดาวน์โหลด Sample CSV",
        sample_data().to_csv(index=False).encode("utf-8-sig"),
        "edu_sentinel_sample.csv",
        "text/csv",
    )


def risk_map(df: pd.DataFrame):
    render_page_banner("Thailand Risk Map", "Geographic risk scan with province, district and school drill-down")
    prov = df.groupby("province", as_index=False).agg(risk_score=("risk_score", "mean"), people=("student_id", "count"))
    prov[["lat", "lon"]] = prov["province"].apply(lambda p: pd.Series(PROVINCE_COORDS.get(str(p), (13.0, 101.0))))
    st.map(prov.rename(columns={"lat": "latitude", "lon": "longitude"}), latitude="latitude", longitude="longitude", size="risk_score")

    selected_province = st.selectbox("Drill-down จังหวัด", sorted(df["province"].unique()))
    district_df = df[df["province"] == selected_province].groupby(["district", "school_name"], as_index=False).agg(
        avg_risk=("risk_score", "mean"),
        people=("student_id", "count"),
        critical=("risk_level", lambda s: int((s == "Critical").sum())),
    )
    themed_dataframe(district_df.sort_values("avg_risk", ascending=False), width="stretch", hide_index=True)
    selected_school = st.selectbox("Drill-down โรงเรียน", sorted(district_df["school_name"].unique()))
    themed_dataframe(df[(df["province"] == selected_province) & (df["school_name"] == selected_school)].sort_values("risk_score", ascending=False), width="stretch", hide_index=True)
    st.caption("MVP แสดง heat/risk bubble ระดับจังหวัดและ drill-down จังหวัด > อำเภอ > โรงเรียน")


def warning_engine(df: pd.DataFrame):
    render_page_banner("Early Warning Engine", "Transparent MVP rules, lineage and risk scoring controls")
    st.markdown(
        f"""**Rule version:** `{RULE_VERSION}`

- Attendance ต่ำ เพิ่มคะแนนสูงสุด 35
- GPA ต่ำ เพิ่มคะแนนสูงสุด 25
- รายได้ครัวเรือนต่ำกว่า 8,000 บาท เพิ่มสูงสุด 20
- Dropout flag +10, Disability +5, Remote area +5
- Low 0-24.9 | Medium 25-49.9 | High 50-74.9 | Critical 75-100
"""
    )
    if st.button("ประมวลผลใหม่"):
        st.session_state.data = score_risk(st.session_state.data)
        generate_alerts(st.session_state.data)
        st.success("ประมวลผลและสร้าง Alert ใหม่เรียบร้อย")
    cols = ["student_id", "period", "province", "school_name", "risk_score", "risk_level", "confidence", "drivers", "data_quality_flag"]
    themed_dataframe(df[cols].sort_values("risk_score", ascending=False), width="stretch", hide_index=True)


def alert_center(alerts: pd.DataFrame):
    render_page_banner("Alert Center & Detail", "Prioritized case signals with evidence, SLA and action controls")
    if alerts.empty:
        st.info("ยังไม่มี Alert")
        return
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        status = st.selectbox("สถานะ", ["ทั้งหมด", "Open", "In Progress", "Closed"])
    with c2:
        severity = st.selectbox("Severity", ["ทั้งหมด", "Critical", "High", "Medium", "Low"])
    with c3:
        sort_by = st.selectbox("เรียงตาม", ["priority_score", "score", "sla_due_at", "created_at"])
    view = alerts.copy()
    if status != "ทั้งหมด":
        view = view[view.status == status]
    if severity != "ทั้งหมด":
        view = view[view.severity == severity]
    if view.empty:
        st.info("ไม่พบ Alert ตามตัวกรองที่เลือก")
        return
    view = view.sort_values(sort_by, ascending=False if sort_by != "sla_due_at" else True)
    themed_dataframe(view, width="stretch", hide_index=True)

    selected = st.selectbox("Alert Detail", view["id"].tolist())
    detail = alerts[alerts.id == selected].iloc[0]
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader(f"Alert #{int(detail.id)}")
        st.write(detail.message)
        st.json(
            {
                "trigger": detail.trigger,
                "drivers": detail.drivers,
                "evidence_refs": detail.evidence_refs,
                "data_quality": detail.data_quality_flag,
                "rule_version": detail.rule_version,
                "model_version": detail.model_version,
                "confidence": detail.confidence,
                "sla_due_at": detail.sla_due_at,
            }
        )
    with right:
        if can_access("Case / Action Tracking"):
            new_status = st.selectbox("เปลี่ยนสถานะ Alert", ["Open", "In Progress", "Closed"], index=["Open", "In Progress", "Closed"].index(detail.status))
            if st.button("บันทึกสถานะ"):
                update_alert_status(int(selected), new_status)
                st.rerun()
            st.divider()
            owner = st.text_input("Owner", value="Area Response Team")
            due_at = st.date_input("SLA / Due date", value=datetime.now().date() + timedelta(days=7))
            note = st.text_area("Next action", value="ตรวจสอบหลักฐานและประสานโรงเรียน/หน่วยพื้นที่")
            if st.button("Create Case / Action", type="primary"):
                create_case(int(selected), owner, due_at, note)
                st.success("สร้าง Case แล้ว")
                st.rerun()
        else:
            st.info("บัญชีนี้ดูรายละเอียดได้ แต่ไม่มีสิทธิ์แก้ไขสถานะหรือสร้าง case")


def case_tracking():
    render_page_banner("Case / Action Tracking", "Operational follow-through for assigned education risk cases")
    cases = load_table("cases")
    if cases.empty:
        st.info("ยังไม่มี Case")
        return
    themed_dataframe(cases.sort_values("case_id", ascending=False), width="stretch", hide_index=True)
    selected = st.selectbox("Case ID", cases["case_id"].tolist())
    status = st.selectbox("สถานะ Case", ["Open", "In Progress", "Closed"])
    outcome = st.text_area("Outcome / Learning note")
    if st.button("บันทึก Case"):
        update_case(int(selected), status, outcome)
        st.success("อัปเดต Case แล้ว")
        st.rerun()


def policy_intelligence(df: pd.DataFrame, alerts: pd.DataFrame):
    render_page_banner("Policy Intelligence", "Executive policy lens for program coverage and impact simulation")
    st.caption("วิเคราะห์ช่องว่างระหว่างกลุ่มเสี่ยง มาตรการช่วยเหลือ และสถานะการตอบสนอง")
    programs = load_table("policy_programs")
    gap = coverage_gap(df)

    overview_tab, simulation_tab = st.tabs(["Policy Snapshot", "What-if Scenario & Impact Simulation"])

    with overview_tab:
        c1, c2, c3 = st.columns(3)
        risk_people = int((df["risk_score"] >= 50).sum()) if not df.empty else 0
        covered = int(df.loc[df["risk_score"] >= 50, "program_coverage_flag"].sum()) if not df.empty else 0
        overdue = 0
        if not alerts.empty and "sla_due_at" in alerts.columns:
            due = pd.to_datetime(alerts["sla_due_at"], errors="coerce")
            overdue = int(((alerts["status"] != "Closed") & (due < pd.Timestamp.today().normalize())).sum())
        c1.metric("กลุ่มเสี่ยงที่ต้องติดตาม", f"{risk_people:,}")
        c2.metric("มีมาตรการครอบคลุมแล้ว", f"{covered:,}")
        c3.metric("Alert เกิน SLA", f"{overdue:,}")

        left, right = st.columns([1, 1])
        with left:
            st.subheader("Coverage Gap by Province")
            themed_dataframe(gap, width="stretch", hide_index=True)
        with right:
            st.subheader("Policy / Program Registry")
            themed_dataframe(programs, width="stretch", hide_index=True)

        st.subheader("Recommended Policy Focus")
        if gap.empty:
            st.success("ยังไม่พบ coverage gap ในตัวกรองนี้")
        else:
            top = gap.iloc[0]
            st.write(
                f"ควรเริ่มจาก {top['province']} เพราะมี coverage gap {int(top['coverage_gap']):,} ราย "
                f"({top['gap_rate']:.1f}% ของกลุ่มเสี่ยงในพื้นที่) และตรวจว่าโปรแกรมที่ active ครอบคลุมกลุ่มเป้าหมายจริงหรือไม่"
            )

    with simulation_tab:
        st.subheader("What-if Scenario")
        if df.empty:
            st.info("ไม่มีข้อมูลตามตัวกรองที่เลือก")
            return

        s1, s2, s3 = st.columns([1.2, 1, 1])
        with s1:
            target_group = st.selectbox(
                "กลุ่มเป้าหมาย",
                [
                    "High/Critical with coverage gap",
                    "All High/Critical",
                    "Critical only",
                    "Attendance below 80%",
                    "Remote or disability",
                ],
            )
        with s2:
            attendance_gain = st.slider("เพิ่ม attendance เฉลี่ย (จุด %)", 0, 30, 8, 1)
            gpa_gain = st.slider("เพิ่ม GPA เฉลี่ย", 0.0, 1.0, 0.2, 0.05)
        with s3:
            income_support = st.number_input("เงิน/ทรัพยากรเสริมต่อเดือน (บาท)", min_value=0, max_value=20000, value=1500, step=500)
            max_slots = int(((df["risk_score"] >= 50) & (df["program_coverage_flag"] == 0)).sum())
            new_coverage_slots = st.number_input("เพิ่ม coverage slots", min_value=0, max_value=max(max_slots, 0), value=min(3, max_slots), step=1)

        simulated, comparison, province_impact, impact = simulate_policy_impact(
            df,
            target_group,
            attendance_gain,
            gpa_gain,
            income_support,
            new_coverage_slots,
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Targeted learners", f"{impact['targeted']:,}")
        m2.metric("High/Critical ลดลง", f"{impact['risk_people_reduced']:,}", f"{impact['risk_people_after']:,} หลังจำลอง")
        m3.metric("Critical ลดลง", f"{impact['critical_reduced']:,}", f"{impact['critical_after']:,} หลังจำลอง")
        m4.metric("Coverage gap ลดลง", f"{impact['coverage_gap_reduced']:,}", f"{impact['coverage_gap_after']:,} หลังจำลอง")

        chart_df = province_impact.sort_values("risk_people_reduced", ascending=False).head(10)
        if not chart_df.empty:
            fig = px.bar(
                chart_df,
                x="risk_people_reduced",
                y="province",
                orientation="h",
                title="Estimated Risk Reduction by Province",
                text="risk_people_reduced",
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(apply_chart_theme(fig), width="stretch")

        st.subheader("Policy Impact Simulation")
        themed_dataframe(province_impact, width="stretch", hide_index=True)

        st.subheader("Scenario Detail")
        detail_cols = [
            "student_id",
            "province",
            "school_name",
            "before_score",
            "after_score",
            "risk_delta",
            "before_level",
            "after_level",
            "before_covered",
            "after_covered",
            "targeted",
        ]
        themed_dataframe(
            comparison.sort_values(["targeted", "risk_delta", "before_score"], ascending=[False, True, False])[detail_cols].head(100),
            width="stretch",
            hide_index=True,
        )

        scenario_note = (
            f"Scenario target={target_group}; attendance_gain={attendance_gain}; gpa_gain={gpa_gain}; "
            f"income_support={income_support}; new_coverage_slots={new_coverage_slots}; "
            f"risk_people {impact['risk_people_before']}->{impact['risk_people_after']}; "
            f"critical {impact['critical_before']}->{impact['critical_after']}; "
            f"coverage_gap {impact['coverage_gap_before']}->{impact['coverage_gap_after']}."
        )
        st.caption(f"Simulation is non-persistent and uses {RULE_VERSION}. {scenario_note}")
        st.download_button(
            "Export Scenario CSV",
            comparison.to_csv(index=False).encode("utf-8-sig"),
            "edu_sentinel_policy_scenario.csv",
            "text/csv",
        )


def ai_summary(df: pd.DataFrame, alerts: pd.DataFrame, selected_period: str, selected_province: str):
    render_page_banner("AI Executive Summary", "Evidence-bound executive narrative for policy decisions")
    sections = executive_summary_sections(df, alerts, selected_period, selected_province)
    log_event("ai_summary_generated", "summary", selected_period, f"area={selected_province}; rows={len(df)}; alerts={len(alerts)}")
    st.caption(f"model_version={MODEL_VERSION} | prompt_version={PROMPT_VERSION} | evidence-bound offline MVP")
    for title, body in sections.items():
        st.subheader(title)
        st.write(body)
    text = "\n\n".join(f"{k}\n{v}" for k, v in sections.items())
    st.download_button("ดาวน์โหลดสรุป (.txt)", text.encode("utf-8"), "edu_sentinel_executive_summary.txt", "text/plain")


def report_export(df: pd.DataFrame, alerts: pd.DataFrame, selected_period: str, selected_province: str):
    render_page_banner("Executive Report Export", "UP-styled printable brief and workbook export")
    sections = executive_summary_sections(df, alerts, selected_period, selected_province)
    html = report_html(df, alerts, sections)
    log_event("report_view_generated", "report", selected_period, f"area={selected_province}; rows={len(df)}; alerts={len(alerts)}")
    st.components.v1.html(html, height=520, scrolling=True)
    st.download_button("Export Excel", to_excel_bytes(df), "EDU_Sentinel_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.download_button("Export HTML Print View", html.encode("utf-8"), "EDU_Sentinel_Report.html", "text/html")


def admin_governance():
    render_page_banner("Admin & Governance", "RBAC, data health, KPI dictionary, lineage and audit readiness")
    st.subheader("RBAC Matrix")
    rows = [{"role": role, "allowed_pages": ", ".join(page for page in PAGES if page in pages)} for role, pages in ROLE_PERMISSIONS.items()]
    themed_dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.subheader("Data Health")
    themed_dataframe(load_table("import_runs").sort_values("run_id", ascending=False), width="stretch", hide_index=True)
    st.subheader("KPI Dictionary")
    themed_dataframe(load_table("kpi_definitions"), width="stretch", hide_index=True)
    st.subheader("Policy / Program Registry")
    themed_dataframe(load_table("policy_programs"), width="stretch", hide_index=True)
    st.subheader("Data Source Lineage")
    themed_dataframe(load_table("data_sources"), width="stretch", hide_index=True)
    st.subheader("Audit Trail")
    themed_dataframe(load_table("audit_logs").sort_values("audit_id", ascending=False).head(100), width="stretch", hide_index=True)
    st.subheader("Audit Notes")
    st.write(
        "MVP records user role, source, period, data quality flag, rule/model version, evidence references and SLA fields. "
        "Production should add immutable audit logs, PDPA masking scopes and approved identity provider integration."
    )


def main():
    st.set_page_config(page_title="EDU Sentinel", page_icon="🛡️", layout="wide")
    apply_up_theme()
    init_db()
    if "user" not in st.session_state:
        render_login()
        return
    ensure_seed_state()

    render_sidebar_brand()
    st.sidebar.caption(f"ผู้ใช้: {st.session_state.user['username']} | สิทธิ์: {st.session_state.user['role']}")
    allowed_pages = [page for page in PAGES if page in ROLE_PERMISSIONS[st.session_state.user["role"]]]
    page = render_sidebar_menu(allowed_pages)
    if st.sidebar.button("ออกจากระบบ"):
        st.session_state.pop("user", None)
        st.session_state.pop("page", None)
        st.rerun()

    filtered_df, selected_period, selected_province = apply_filters(st.session_state.data)
    alerts = load_alerts()
    if selected_period != "ทั้งหมด" and not alerts.empty:
        alerts = alerts[alerts.period == selected_period]
    if selected_province != "ทั้งหมด" and not alerts.empty:
        alerts = alerts[alerts.province == selected_province]
    display_df = mask_sensitive_dataframe(filtered_df)
    display_alerts = mask_sensitive_dataframe(alerts)

    if page == "Executive Command Center":
        command_center(display_df, display_alerts, selected_period, selected_province)
    elif page == "Operations Dashboard":
        operations_dashboard(display_df, display_alerts, selected_period, selected_province)
    elif page == "Data Import":
        data_import()
    elif page == "Thailand Risk Map":
        risk_map(display_df)
    elif page == "Early Warning Engine":
        warning_engine(display_df)
    elif page == "Alert Center & Detail":
        alert_center(display_alerts)
    elif page == "Case / Action Tracking":
        case_tracking()
    elif page == "Policy Intelligence":
        policy_intelligence(display_df, display_alerts)
    elif page == "AI Executive Summary":
        ai_summary(display_df, display_alerts, selected_period, selected_province)
    elif page == "Executive Report Export":
        report_export(display_df, display_alerts, selected_period, selected_province)
    elif page == "Admin & Governance":
        admin_governance()


if __name__ == "__main__":
    main()

