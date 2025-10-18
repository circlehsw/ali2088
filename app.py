# app.py — 最小可用的資料探索網站（Streamlit）
import streamlit as st
import pandas as pd
from sqlalchemy import text
from db import get_engine

st.set_page_config(page_title="GoodLife Data Portal", page_icon="📊", layout="wide")
st.title("📊 GoodLife Data Portal")
st.caption("已連線到 Cloud SQL（MySQL 8.4.x-google） — 由 circle_admin 授權")

# 連線測試 + 基本資訊
with st.sidebar:
    st.subheader("連線狀態")
    try:
        eng = get_engine()
        with eng.connect() as conn:
            row = conn.exec_driver_sql("SELECT @@version AS v").fetchone()
        st.success(f"Connected ✅ 版本：{row.v}")
    except Exception as e:
        st.error(f"連線失敗：{e}")

tab1, tab2, tab3 = st.tabs(["🔎 快速查詢", "🗂 資料表清單", "🧪 自訂 SQL"])

# --- Tab1：快速查詢（示範 SELECT * LIMIT）
with tab1:
    st.subheader("快速查詢（示範）")
    table = st.text_input("輸入資料表名稱（例如：products 或 your_table）", value="", placeholder="例如：your_table_name")
    limit = st.number_input("最多顯示筆數", min_value=1, max_value=5000, value=50, step=10)
    if st.button("查詢", type="primary"):
        if not table:
            st.warning("請先輸入資料表名稱")
        else:
            try:
                sql = text(f"SELECT * FROM `{table}` LIMIT :lim")
                df = pd.read_sql(sql, eng.connect(), params={"lim": int(limit)})
                st.success(f"查到 {len(df)} 筆")
                st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"查詢失敗：{e}")

# --- Tab2：列出所有資料表
with tab2:
    st.subheader("所有資料表")
    try:
        with eng.connect() as conn:
            # INFORMATION_SCHEMA 適用 MySQL
            tables = pd.read_sql(text("""
                SELECT TABLE_NAME, TABLE_ROWS, CREATE_TIME, UPDATE_TIME
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                ORDER BY TABLE_NAME
            """), conn)
        st.dataframe(tables, use_container_width=True)
    except Exception as e:
        st.error(f"讀取失敗：{e}")

# --- Tab3：自訂 SQL（唯讀）
with tab3:
    st.subheader("自訂 SQL（唯讀）")
    st.caption("⚠️ 請勿執行 DROP/DELETE/UPDATE 等修改語句（先上 read-only）。")
    user_sql = st.text_area("輸入 SELECT 語句", height=160, placeholder="例如：SELECT * FROM your_table LIMIT 100;")
    if st.button("執行 SQL"):
        if not user_sql.strip().lower().startswith("select"):
            st.warning("目前僅允許 SELECT 查詢。")
        else:
            try:
                with eng.connect() as conn:
                    df = pd.read_sql(text(user_sql), conn)
                st.success(f"查到 {len(df)} 筆")
                st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"執行失敗：{e}")

st.divider()
st.caption("© GoodLife | Powered by Streamlit + SQLAlchemy + MySQL Connector (TLS)")
