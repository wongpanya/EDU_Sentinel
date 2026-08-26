import io
import os
import sqlite3
import hashlib
import hmac
import secrets
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = os.path.join(os.path.dirname(__file__), 'edu_sentinel.db')

PROVINCE_COORDS = {
    'Bangkok': (13.7563, 100.5018), 'Chiang Mai': (18.7883, 98.9853),
    'Chiang Rai': (19.9105, 99.8406), 'Khon Kaen': (16.4322, 102.8236),
    'Nakhon Ratchasima': (14.9799, 102.0978), 'Ubon Ratchathani': (15.2447, 104.8473),
    'Udon Thani': (17.4138, 102.7872), 'Phitsanulok': (16.8211, 100.2659),
    'Nakhon Sawan': (15.7047, 100.1372), 'Chonburi': (13.3611, 100.9847),
    'Rayong': (12.6814, 101.2816), 'Phetchaburi': (13.1119, 99.9391),
    'Surat Thani': (9.1382, 99.3217), 'Phuket': (7.8804, 98.3923),
    'Songkhla': (7.1898, 100.5954), 'Pattani': (6.8695, 101.2505),
    'Yala': (6.5411, 101.2804), 'Narathiwat': (6.4255, 101.8253),
    'Tak': (16.8839, 99.1258), 'Mae Hong Son': (19.3020, 97.9654),
}

RISK_ORDER = {'Low': 1, 'Medium': 2, 'High': 3, 'Critical': 4}
RISK_LABELS_TH = {'Low': 'ต่ำ', 'Medium': 'ปานกลาง', 'High': 'สูง', 'Critical': 'วิกฤต'}


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'executive'
    )''')
    con.execute('''CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        student_id TEXT,
        province TEXT,
        risk_level TEXT,
        score REAL,
        message TEXT,
        status TEXT DEFAULT 'Open'
    )''')
    cur = con.execute('SELECT COUNT(*) FROM users')
    if cur.fetchone()[0] == 0:
        salt = secrets.token_hex(16)
        pwd_hash = hash_password('admin1234', salt)
        con.execute('INSERT INTO users(username,password_hash,salt,role) VALUES(?,?,?,?)',
                    ('admin', pwd_hash, salt, 'admin'))
    con.commit()
    con.close()


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 120000).hex()


def authenticate(username: str, password: str):
    con = sqlite3.connect(DB_PATH)
    row = con.execute('SELECT username,password_hash,salt,role FROM users WHERE username=?', (username,)).fetchone()
    con.close()
    if not row:
        return None
    candidate = hash_password(password, row[2])
    if hmac.compare_digest(candidate, row[1]):
        return {'username': row[0], 'role': row[3]}
    return None


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        'student_id': ['student_id', 'studentid', 'id', 'รหัสนักเรียน'],
        'province': ['province', 'จังหวัด'],
        'attendance_rate': ['attendance_rate', 'attendance', 'อัตราเข้าเรียน'],
        'gpa': ['gpa', 'grade', 'เกรดเฉลี่ย'],
        'income_per_month': ['income_per_month', 'income', 'รายได้ครัวเรือน'],
        'dropout_risk_flag': ['dropout_risk_flag', 'dropout_flag', 'เสี่ยงหลุดระบบ'],
        'disability_flag': ['disability_flag', 'disability', 'พิการ'],
        'remote_area_flag': ['remote_area_flag', 'remote_area', 'พื้นที่ห่างไกล'],
    }
    normalized = {str(c).strip().lower(): c for c in df.columns}
    rename = {}
    for target, names in aliases.items():
        for name in names:
            if name.lower() in normalized:
                rename[normalized[name.lower()]] = target
                break
    df = df.rename(columns=rename).copy()
    if 'student_id' not in df.columns:
        df['student_id'] = [f'STU-{i+1:05d}' for i in range(len(df))]
    if 'province' not in df.columns:
        df['province'] = 'Bangkok'
    defaults = {
        'attendance_rate': 100.0, 'gpa': 3.0, 'income_per_month': 15000.0,
        'dropout_risk_flag': 0, 'disability_flag': 0, 'remote_area_flag': 0,
    }
    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val
    numeric_cols = list(defaults.keys())
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(defaults[c])
    return df


def score_risk(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    score = pd.Series(0.0, index=out.index)
    score += ((100 - out['attendance_rate']).clip(lower=0) * 0.9).clip(upper=35)
    score += ((2.5 - out['gpa']).clip(lower=0) * 12).clip(upper=25)
    score += ((8000 - out['income_per_month']).clip(lower=0) / 8000 * 20).clip(upper=20)
    score += out['dropout_risk_flag'].clip(0, 1) * 10
    score += out['disability_flag'].clip(0, 1) * 5
    score += out['remote_area_flag'].clip(0, 1) * 5
    out['risk_score'] = score.round(1).clip(0, 100)
    out['risk_level'] = pd.cut(out['risk_score'], bins=[-1, 24.9, 49.9, 74.9, 100],
                               labels=['Low', 'Medium', 'High', 'Critical']).astype(str)
    return out


def generate_alerts(df: pd.DataFrame):
    risky = df[df['risk_level'].isin(['High', 'Critical'])].copy()
    if risky.empty:
        return
    con = sqlite3.connect(DB_PATH)
    now = datetime.now().isoformat(timespec='seconds')
    for _, r in risky.iterrows():
        exists = con.execute(
            "SELECT 1 FROM alerts WHERE student_id=? AND risk_level=? AND status='Open'",
            (str(r['student_id']), r['risk_level'])
        ).fetchone()
        if not exists:
            msg = f"พบความเสี่ยงระดับ {RISK_LABELS_TH[r['risk_level']]} ควรตรวจสอบปัจจัยการเข้าเรียน ผลสัมฤทธิ์ และฐานะครัวเรือน"
            con.execute('INSERT INTO alerts(created_at,student_id,province,risk_level,score,message,status) VALUES(?,?,?,?,?,?,?)',
                        (now, str(r['student_id']), str(r['province']), r['risk_level'], float(r['risk_score']), msg, 'Open'))
    con.commit()
    con.close()


def load_alerts():
    con = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query('SELECT * FROM alerts ORDER BY id DESC', con)
    con.close()
    return df


def update_alert_status(alert_id: int, status: str):
    con = sqlite3.connect(DB_PATH)
    con.execute('UPDATE alerts SET status=? WHERE id=?', (status, alert_id))
    con.commit(); con.close()


def executive_summary(df: pd.DataFrame) -> str:
    n = len(df)
    if n == 0:
        return 'ยังไม่มีข้อมูลสำหรับสรุป'
    counts = df['risk_level'].value_counts()
    high = int(counts.get('High', 0)); critical = int(counts.get('Critical', 0))
    avg_att = df['attendance_rate'].mean(); avg_gpa = df['gpa'].mean()
    prov = (df.groupby('province')['risk_score'].mean().sort_values(ascending=False).head(3))
    top_prov = ', '.join([f'{p} ({s:.1f})' for p, s in prov.items()]) or '-'
    pct = (high + critical) / n * 100
    priority = 'เร่งด่วนมาก' if critical > 0 or pct >= 25 else ('ควรเฝ้าระวังใกล้ชิด' if pct >= 10 else 'อยู่ในระดับควบคุมได้')
    return (
        f"ข้อมูลทั้งหมด {n:,} ราย พบกลุ่มเสี่ยงสูง {high:,} ราย และวิกฤต {critical:,} ราย "
        f"คิดเป็น {pct:.1f}% ของข้อมูลทั้งหมด ภาพรวมสถานการณ์อยู่ในระดับ “{priority}”. "
        f"อัตราเข้าเรียนเฉลี่ย {avg_att:.1f}% และ GPA เฉลี่ย {avg_gpa:.2f}. "
        f"พื้นที่ที่มีคะแนนความเสี่ยงเฉลี่ยสูงสุด ได้แก่ {top_prov}. "
        "ข้อเสนอเชิงบริหาร: ให้จัดลำดับช่วยเหลือกลุ่มวิกฤตก่อน ตรวจสอบเคสที่มีการเข้าเรียนต่ำร่วมกับฐานะครัวเรือนเปราะบาง "
        "และมอบหมายหน่วยปฏิบัติการติดตามพื้นที่เสี่ยงสูง พร้อมทบทวนผลอย่างน้อยรายสัปดาห์."
    )


def sample_data() -> pd.DataFrame:
    return pd.DataFrame([
        ['STU-00001','Bangkok',96,3.35,22000,0,0,0],
        ['STU-00002','Chiang Mai',82,2.40,7200,1,0,1],
        ['STU-00003','Tak',68,1.85,4800,1,0,1],
        ['STU-00004','Pattani',74,2.05,6500,1,0,0],
        ['STU-00005','Khon Kaen',90,2.85,11000,0,1,0],
        ['STU-00006','Mae Hong Son',61,1.60,3900,1,1,1],
        ['STU-00007','Songkhla',88,2.70,9000,0,0,0],
        ['STU-00008','Ubon Ratchathani',77,2.20,7000,1,0,1],
        ['STU-00009','Chonburi',98,3.60,26000,0,0,0],
        ['STU-00010','Narathiwat',71,1.95,5500,1,0,0],
    ], columns=['student_id','province','attendance_rate','gpa','income_per_month','dropout_risk_flag','disability_flag','remote_area_flag'])


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='RiskData')
        alerts = load_alerts()
        alerts.to_excel(writer, index=False, sheet_name='Alerts')
    return output.getvalue()


def render_login():
    st.title('EDU Sentinel')
    st.caption('Policy Intelligence & Early Warning for Educational Equity')
    with st.form('login'):
        username = st.text_input('Username')
        password = st.text_input('Password', type='password')
        submit = st.form_submit_button('เข้าสู่ระบบ', use_container_width=True)
    if submit:
        user = authenticate(username, password)
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')
    st.info('บัญชีเดโม: admin / admin1234')


def main():
    st.set_page_config(page_title='EDU Sentinel', page_icon='🛡️', layout='wide')
    init_db()
    if 'user' not in st.session_state:
        render_login(); return

    if 'data' not in st.session_state:
        st.session_state.data = score_risk(sample_data())
        generate_alerts(st.session_state.data)

    st.sidebar.title('🛡️ EDU Sentinel')
    st.sidebar.caption(f"ผู้ใช้: {st.session_state.user['username']} ({st.session_state.user['role']})")
    page = st.sidebar.radio('เมนู', [
        'Executive Dashboard','Data Import','Thailand Risk Map','Early Warning Engine',
        'Alert Center','AI Executive Summary','Report Export'
    ])
    if st.sidebar.button('ออกจากระบบ'):
        st.session_state.pop('user', None); st.rerun()

    df = st.session_state.data

    if page == 'Executive Dashboard':
        st.title('Executive Dashboard')
        total = len(df); critical = int((df.risk_level=='Critical').sum()); high = int((df.risk_level=='High').sum())
        avg = df.risk_score.mean() if total else 0
        c1,c2,c3,c4 = st.columns(4)
        c1.metric('เด็ก/เยาวชนในระบบ', f'{total:,}')
        c2.metric('Critical', f'{critical:,}')
        c3.metric('High Risk', f'{high:,}')
        c4.metric('Risk Score เฉลี่ย', f'{avg:.1f}/100')

        left,right = st.columns([1,1])
        with left:
            counts = df.risk_level.value_counts().reindex(['Low','Medium','High','Critical'], fill_value=0).reset_index()
            counts.columns=['risk_level','count']
            fig = px.bar(counts, x='risk_level', y='count', title='Risk Distribution', text='count')
            st.plotly_chart(fig, use_container_width=True)
        with right:
            prov = df.groupby('province', as_index=False).agg(avg_risk=('risk_score','mean'), people=('student_id','count')).sort_values('avg_risk', ascending=False).head(10)
            fig2 = px.bar(prov, x='avg_risk', y='province', orientation='h', title='Top Risk Provinces')
            fig2.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig2, use_container_width=True)
        st.subheader('รายการที่ต้องให้ความสนใจ')
        st.dataframe(df.sort_values('risk_score', ascending=False).head(20), use_container_width=True, hide_index=True)

    elif page == 'Data Import':
        st.title('Data Import (CSV / Excel)')
        st.write('รองรับคอลัมน์หลัก: student_id, province, attendance_rate, gpa, income_per_month, dropout_risk_flag, disability_flag, remote_area_flag')
        uploaded = st.file_uploader('เลือกไฟล์', type=['csv','xlsx','xls'])
        if uploaded:
            try:
                raw = pd.read_csv(uploaded) if uploaded.name.lower().endswith('.csv') else pd.read_excel(uploaded)
                clean = normalize_columns(raw)
                scored = score_risk(clean)
                st.success(f'อ่านข้อมูลสำเร็จ {len(scored):,} ราย')
                st.dataframe(scored.head(50), use_container_width=True)
                if st.button('นำข้อมูลเข้าสู่ระบบ', type='primary'):
                    st.session_state.data = scored
                    generate_alerts(scored)
                    st.success('นำเข้าข้อมูลและประมวลผลความเสี่ยงแล้ว')
            except Exception as e:
                st.error(f'ไม่สามารถอ่านไฟล์ได้: {e}')
        st.download_button('ดาวน์โหลด Sample CSV', sample_data().to_csv(index=False).encode('utf-8-sig'), 'edu_sentinel_sample.csv', 'text/csv')

    elif page == 'Thailand Risk Map':
        st.title('Thailand Risk Map')
        prov = df.groupby('province', as_index=False).agg(risk_score=('risk_score','mean'), people=('student_id','count'))
        prov[['lat','lon']] = prov['province'].apply(lambda p: pd.Series(PROVINCE_COORDS.get(str(p), (13.0,101.0))))
        prov['risk_level'] = pd.cut(prov['risk_score'], bins=[-1,24.9,49.9,74.9,100], labels=['Low','Medium','High','Critical']).astype(str)
        st.map(prov.rename(columns={'lat':'latitude','lon':'longitude'}), latitude='latitude', longitude='longitude', size='risk_score')
        st.dataframe(prov.sort_values('risk_score', ascending=False), use_container_width=True, hide_index=True)
        st.caption('MVP ใช้จุดศูนย์กลางจังหวัดเพื่อแสดง Heat/Risk Bubble; รุ่นถัดไปสามารถเปลี่ยนเป็น GeoJSON choropleth รายจังหวัด/อำเภอได้')

    elif page == 'Early Warning Engine':
        st.title('Early Warning Engine')
        st.markdown('''**กติกา MVP**\n- Attendance ต่ำ เพิ่มคะแนนสูงสุด 35\n- GPA ต่ำ เพิ่มคะแนนสูงสุด 25\n- รายได้ครัวเรือนต่ำกว่า 8,000 บาท เพิ่มสูงสุด 20\n- Dropout flag +10, Disability +5, Remote area +5\n- Low 0–24.9 | Medium 25–49.9 | High 50–74.9 | Critical 75–100''')
        if st.button('ประมวลผลใหม่'):
            st.session_state.data = score_risk(df)
            generate_alerts(st.session_state.data)
            st.success('ประมวลผลและสร้าง Alert ใหม่เรียบร้อย')
        st.dataframe(st.session_state.data.sort_values('risk_score', ascending=False), use_container_width=True, hide_index=True)

    elif page == 'Alert Center':
        st.title('Alert Center')
        alerts = load_alerts()
        if alerts.empty:
            st.info('ยังไม่มี Alert')
        else:
            col1,col2 = st.columns([2,1])
            with col1:
                status = st.selectbox('กรองสถานะ', ['ทั้งหมด','Open','In Progress','Closed'])
            view = alerts if status=='ทั้งหมด' else alerts[alerts.status==status]
            st.dataframe(view, use_container_width=True, hide_index=True)
            with col2:
                ids = alerts['id'].tolist()
                selected = st.selectbox('Alert ID', ids)
                new_status = st.selectbox('เปลี่ยนสถานะ', ['Open','In Progress','Closed'])
                if st.button('บันทึกสถานะ'):
                    update_alert_status(int(selected), new_status); st.rerun()

    elif page == 'AI Executive Summary':
        st.title('AI Executive Summary')
        summary = executive_summary(df)
        st.text_area('Executive Brief', summary, height=260)
        st.download_button('ดาวน์โหลดสรุป (.txt)', summary.encode('utf-8'), 'edu_sentinel_executive_summary.txt', 'text/plain')
        st.caption('MVP นี้ใช้ Executive Summary Engine แบบอธิบายได้และทำงานออฟไลน์; สามารถต่อ LLM/API ภายหลังโดยไม่เปลี่ยนโครงสร้างข้อมูลหลัก')

    elif page == 'Report Export':
        st.title('Report Export')
        summary = executive_summary(df)
        st.subheader('Executive Summary')
        st.write(summary)
        st.download_button('Export Excel', to_excel_bytes(df), 'EDU_Sentinel_Report.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        html = f'''<html><meta charset="utf-8"><body><h1>EDU Sentinel Executive Report</h1><p>{summary}</p><h2>Risk Data</h2>{df.to_html(index=False)}</body></html>'''
        st.download_button('Export HTML Report', html.encode('utf-8'), 'EDU_Sentinel_Report.html', 'text/html')


if __name__ == '__main__':
    main()
