# 檔案：five_standard.py (雲端資料庫版本)
import os, calendar
import pandas as pd
import streamlit as st

__all__ = ["render"]
__version__ = "v1.3.4-tight-gap-04"

def _set_weekdays(val: bool):
    import streamlit as st
    for i in range(1,7):
        st.session_state[f"fs_w{i}"] = val

@st.cache_data(show_spinner=False)
def _get_date_bounds(table, date_col):
    conn = st.connection("mysql", type="sql")
    q = f'SELECT MIN(DATE(`{date_col}`)) AS min_d, MAX(DATE(`{date_col}`)) AS max_d FROM `{table}`'
    s = conn.query(q, ttl=3600)
    if s.empty: return "2020-01-01", "2025-12-31"
    return str(s.at[0,"min_d"]), str(s.at[0,"max_d"])

@st.cache_data(show_spinner=False)
def _get_years(table, date_col):
    conn = st.connection("mysql", type="sql")
    q = f'SELECT DISTINCT SUBSTR(`{date_col}`,1,4) AS y FROM `{table}` WHERE `{date_col}` IS NOT NULL ORDER BY 1'
    ser = conn.query(q, ttl=3600)["y"]
    years = []
    for v in ser:
        if pd.isna(v): continue
        s = str(v).strip()
        if s.isdigit():
            y = int(s)
            if 1900 <= y <= 2100: years.append(str(y))
    return sorted(set(years))

def _last_day_of_month(y:int, m:int)->int:
    return calendar.monthrange(y, m)[1]

def _clamp_day(y:str, m:str, d:str)->str:
    try: dmax = _last_day_of_month(int(y), int(m))
    except Exception: return "01"
    try: di = int(d)
    except Exception: di = 1
    di = max(1, min(di, dmax))
    return f"{di:02d}"

def render(table:str, date_col:str="時間戳記", default_mode:str="1344"):
    st.markdown(
        """
        <style>
        :root { --fs-accent: #ff4b4b; }
        [data-testid="stSlider"] [role="slider"]{ background-color: var(--fs-accent) !important; box-shadow: 0 0 0 4px rgba(255,75,75,.15); }
        [data-testid="stSlider"] .st-emotion-cache-14f0kfv, [data-testid="stSlider"] .st-emotion-cache-1inwz65{ background: linear-gradient(90deg, var(--fs-accent), var(--fs-accent)) !important; }
        section.main > div.block-container [data-testid="stVerticalBlock"]{ gap: .20rem !important; }
        section.main > div.block-container [data-testid="stVerticalBlock"] > div{ margin-top: 0 !important; margin-bottom: 0 !important; }
        :where(.block-container) div.row-widget{ margin-bottom: .20rem !important; }
        [data-testid="column"]{ padding-top: 0 !important; padding-bottom: 0 !important; }
        .stSelectbox label, .stCheckbox > label{ margin-bottom: 0 !important; }
        .fs-row-nudge{ margin-top: -84px !important; }
        .fs-week-cols{ display:flex; align-items:center; gap:.35rem; }
        .fs-week-cols label{ white-space:nowrap; line-height:1; padding:0 .15rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    min_d, max_d = _get_date_bounds(table, date_col)
    years = _get_years(table, date_col)
    if not years:
        years = [str(pd.to_datetime(min_d).year), str(pd.to_datetime(max_d).year)]
        years = sorted(set(years))
    months = [f"{i:02d}" for i in range(1,13)]
    y1_def, m1_def, d1_def = years[0], "01", "01"
    _max_dt = pd.to_datetime(max_d)
    if not all(k in st.session_state for k in ("fs_y2","fs_m2","fs_d2")) or st.session_state.get("fs__db_max_cache") != str(_max_dt.date()):
        st.session_state["fs_y2"], st.session_state["fs_m2"], st.session_state["fs_d2"] = f"{_max_dt.year}", f"{_max_dt.month:02d}", f"{_max_dt.day:02d}"
        st.session_state["fs__db_max_cache"] = str(_max_dt.date())
    y1, m1, d1 = str(st.session_state.get("fs_y1", y1_def)), str(st.session_state.get("fs_m1", m1_def)), _clamp_day(str(st.session_state.get("fs_y1", y1_def)), str(st.session_state.get("fs_m1", m1_def)), str(st.session_state.get("fs_d1", d1_def)))
    y2, m2, d2 = str(st.session_state.get("fs_y2")), str(st.session_state.get("fs_m2")), _clamp_day(str(st.session_state.get("fs_y2")), str(st.session_state.get("fs_m2")), str(st.session_state.get("fs_d2")))
    try:
        if pd.to_datetime(f"{y2}-{m2}-{d2}") > pd.to_datetime(max_d):
            y2, m2, d2 = f"{_max_dt.year}", f"{_max_dt.month:02d}", f"{_max_dt.day:02d}"
            st.session_state["fs_y2"], st.session_state["fs_m2"], st.session_state["fs_d2"] = y2, m2, d2
    except Exception: pass
    start_dt, end_dt = pd.to_datetime(f"{y1}-{m1}-{d1}", errors='coerce').to_pydatetime(), pd.to_datetime(f"{y2}-{m2}-{d2}", errors='coerce').to_pydatetime()
    st.slider("日期視覺（不操作）", value=(start_dt, end_dt), min_value=pd.to_datetime(min_d).to_pydatetime(), max_value=pd.to_datetime(max_d).to_pydatetime(), disabled=True)
    lc, rc = st.columns(2)
    with lc:
        st.markdown("**起始**"); c1,c2,c3 = st.columns(3, gap="small")
        with c1: y1 = st.selectbox("年", years, index=years.index(y1) if y1 in years else 0, key="fs_y1")
        with c2: m1 = st.selectbox("月", months, index=months.index(m1) if m1 in months else 0, key="fs_m1")
        day_opts1 = [f"{i:02d}" for i in range(1, _last_day_of_month(int(y1), int(m1)) + 1)]
        with c3: d1 = st.selectbox("日", day_opts1, index=day_opts1.index(d1) if d1 in day_opts1 else 0, key="fs_d1")
    with rc:
        st.markdown("**結束**"); c4,c5,c6 = st.columns(3, gap="small")
        with c4: y2 = st.selectbox("年", years, key="fs_y2")
        with c5: m2 = st.selectbox("月", [f"{i:02d}" for i in range(1,13)], key="fs_m2")
        day_opts2 = [f"{i:02d}" for i in range(1, _last_day_of_month(int(st.session_state.get("fs_y2", y2)), int(st.session_state.get("fs_m2", m2))) + 1)]
        with c6: d2 = st.selectbox("日", day_opts2, key="fs_d2")
    st.markdown('<div class="fs-row-nudge">', unsafe_allow_html=True); cols = st.columns([5,12,2,2,1])
    with cols[0]: mode = st.selectbox("Mode", ["1344", "floating"], index=0 if default_mode=="1344" else 1, key="fs_mode")
    for i in range(1,7): st.session_state.setdefault(f"fs_w{i}", True)
    with cols[1]:
        wcols = st.columns(6, gap="small"); labels = ["週一","週二","週三","週四","週五","週六"]
        for i, lab in enumerate(labels, start=1):
            with wcols[i-1]: st.checkbox(lab, key=f"fs_w{i}")
    with cols[2]: st.button("全選", use_container_width=True, key="fs_sel_all", on_click=_set_weekdays, args=(True,))
    with cols[3]: st.button("全消", use_container_width=True, key="fs_sel_none", on_click=_set_weekdays, args=(False,))
    st.markdown('</div>', unsafe_allow_html=True)
    weekdays = [i for i in range(1,7) if st.session_state.get(f"fs_w{i}", True)]
    return {"start_date": f"{y1}-{m1}-{d1}", "end_date": f"{y2}-{m2}-{d2}", "mode": mode, "weekdays": weekdays}