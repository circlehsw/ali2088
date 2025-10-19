# 檔案：output_multi_filter.py (v1.2 - 修正收盤價計算邏輯)
import pandas as pd
import streamlit as st
from typing import List

__all__ = ["render_output"]

def _weekday_mysql(weekdays: List[int]) -> str:
    if not weekdays: return "2,3,4,5,6,7"
    mapping = {1:2, 2:3, 3:4, 4:5, 5:6, 6:7}
    return ",".join(str(mapping.get(d, 0)) for d in sorted(weekdays))

def _wrap_headers(df: pd.DataFrame) -> pd.DataFrame:
    mapping = { "日盤收盤的價平和(價平)": "日盤收盤的\n價平和(價平)", "夜盤收盤的價平和(價平)": "夜盤收盤的\n價平和(價平)", "FT次交易日日盤收盤": "FT次交易日\n日盤收盤", "FT次交易日(FT漲跌-日盤)": "FT次交易日\n(FT漲跌-日盤)", "FT次交易日夜盤收盤": "FT次交易日\n夜盤收盤", "FT次交易日(FT漲跌-夜盤)": "FT次交易日\n(FT漲跌-夜盤)", "次交易日日盤收盤的價平和(價平)": "次交易日(日盤)\n價平和(價平)", "次交易日夜盤收盤的價平和(價平)": "次交易日(夜盤)\n價平和(價平)", "FT日盤收盤": "FT日盤\n收盤", "FT漲跌(日盤)": "FT漲跌\n(日盤)", "FT夜盤收盤": "FT夜盤\n收盤", "FT漲跌(夜盤)": "FT漲跌\n(夜盤)", }
    return df.rename(columns=mapping)

def _render_table(df, start_date, end_date, mode, weekdays):
    st.caption(f"資料區間：{start_date} ~ {end_date}｜Mode：{mode}｜星期：{sorted(weekdays or [])}")
    column_config = {
        "日期": st.column_config.DateColumn("日期", width=120, format="YYYY-MM-DD"),
        "星期": st.column_config.TextColumn("星期", width=60),
        "FT日盤\n收盤": st.column_config.NumberColumn("FT日盤\n收盤", width=110),
        "FT漲跌\n(日盤)": st.column_config.NumberColumn("FT漲跌\n(日盤)", width=110, format="%.0f"),
        "FT夜盤\n收盤": st.column_config.NumberColumn("FT夜盤\n收盤", width=110),
        "FT漲跌\n(夜盤)": st.column_config.NumberColumn("FT漲跌\n(夜盤)", width=110, format="%.0f"),
        "日盤收盤的\n價平和(價平)": st.column_config.NumberColumn("日盤收盤的\n價平和(價平)", width=120, format="%.0f"),
        "夜盤收盤的\n價平和(價平)": st.column_config.NumberColumn("夜盤收盤的\n價平和(價平)", width=120, format="%.0f"),
        "FT次交易日\n日盤收盤": st.column_config.NumberColumn("FT次交易日\n日盤收盤", width=120),
        "FT次交易日\n(FT漲跌-日盤)": st.column_config.NumberColumn("FT次交易日\n(FT漲跌-日盤)", width=140, format="%.0f"),
        "FT次交易日\n夜盤收盤": st.column_config.NumberColumn("FT次交易日\n夜盤收盤", width=120),
        "FT次交易日\n(FT漲跌-夜盤)": st.column_config.NumberColumn("FT次交易日\n(FT漲跌-夜盤)", width=140, format="%.0f"),
        "次交易日(日盤)\n價平和(價平)": st.column_config.NumberColumn("次交易日(日盤)\n價平和(價平)", width=140, format="%.0f"),
        "次交易日(夜盤)\n價平和(價平)": st.column_config.NumberColumn("次交易日(夜盤)\n價平和(價平)", width=140, format="%.0f"),
    }
    st.dataframe(df, use_container_width=True, column_config=column_config, hide_index=True, height=300)

def render_output(
    table:str="atm", date_col:str="時間戳記", start_date:str=None, end_date:str=None,
    mode:str="1344", weekdays:List[int]=None, ft_price_filter_enabled: bool = False,
    min_ft_price:float=0.0, max_ft_price:float=0.0, kph_filter_enabled: bool = False,
    min_kph:float=0.0, max_kph:float=0.0, time_filter_enabled: bool = False,
    min_time:str="00:00", max_time:str="23:59", filter_target:str="不篩選",
    min_value:float=0.0, max_value:float=0.0, filter_kph_change_target: str = "不篩選",
    min_kph_change_value: float = 0.0, max_kph_change_value: float = 0.0
) -> List[str]:
    col_run = st.columns([1, 1, 1])[1]
    run_key = f"out_run_button_{start_date}_{end_date}_{mode}_{min_time}_{max_time}_{filter_target}_{filter_kph_change_target}"
    with col_run:
        run = st.button("🚀 執行查詢", use_container_width=True, type="primary", key=run_key)
    is_snapshot_available = ('__df_snapshot__' in st.session_state and not st.session_state['__df_snapshot__'].empty)
    params = {}
    target_filter_sql = "1=1"
    if filter_target == "區間最高漲點 (Max Up)": target_filter_sql = "(MaxUp BETWEEN :min_value AND :max_value)"; params.update({"min_value": min_value, "max_value": max_value})
    elif filter_target == "區間最大跌點 (Max Down)": target_filter_sql = "(MaxDown BETWEEN :min_value AND :max_value)"; params.update({"min_value": min_value, "max_value": max_value})
    kph_filter_sql = "1=1"
    if filter_kph_change_target == "價平和上漲": kph_filter_sql = "(KphMaxUp BETWEEN :min_kph_value AND :max_kph_value)"; params.update({"min_kph_value": min_kph_change_value, "max_kph_value": max_kph_change_value})
    elif filter_kph_change_target == "價平和下跌": kph_filter_sql = "(KphMaxDown BETWEEN :min_kph_value AND :max_kph_value)"; params.update({"min_kph_value": min_kph_change_value, "max_kph_value": max_kph_change_value})
    if run:
        end_date_plus_one = (pd.to_datetime(end_date) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        main_params = {"start_date": start_date, "end_date_plus_one": end_date_plus_one, "mode": mode}; main_params.update(params)
        wk_sql = _weekday_mysql(weekdays or [])
        range_data_where_clauses = []
        if time_filter_enabled: range_data_where_clauses.append("TIME(ts) BETWEEN :min_time AND :max_time"); main_params.update({"min_time": min_time, "max_time": max_time})
        if ft_price_filter_enabled: range_data_where_clauses.append('CAST(`FT價格` AS DECIMAL(10,2)) BETWEEN :min_ft_price AND :max_ft_price'); main_params.update({"min_ft_price": min_ft_price, "max_ft_price": max_ft_price})
        if kph_filter_enabled: range_data_where_clauses.append('CAST(`價平和(價平)` AS DECIMAL(10,2)) BETWEEN :min_kph AND :max_kph'); main_params.update({"min_kph": min_kph, "max_kph": max_kph})
        range_data_where_sql = " AND ".join(range_data_where_clauses) if range_data_where_clauses else "1=1"
        sql = f"""
        WITH base AS (
            SELECT DATE(`{date_col}`) AS d, `{date_col}` AS ts, mode, `FT價格`, `FT漲跌`, `價平和(價平)`, `價平和漲跌(價平)`
            FROM `{table}`
            WHERE `{date_col}` >= :start_date AND `{date_col}` < :end_date_plus_one
              AND LOWER(TRIM(mode)) = LOWER(TRIM(:mode))
        ), RangeData AS (
            SELECT d, CAST(`FT漲跌` AS DECIMAL(10,2)) AS ft_chg, CAST(`價平和漲跌(價平)` AS DECIMAL(10,2)) AS kph_chg
            FROM base WHERE {range_data_where_sql}
        ), TargetDates AS (
            SELECT d, COALESCE(MAX(CASE WHEN ft_chg > 0 THEN ft_chg ELSE NULL END), 0.0) AS MaxUp, COALESCE(MIN(CASE WHEN ft_chg < 0 THEN ft_chg ELSE NULL END), 0.0) AS MaxDown,
            COALESCE(MAX(CASE WHEN kph_chg > 0 THEN kph_chg ELSE NULL END), 0.0) AS KphMaxUp, COALESCE(MIN(CASE WHEN kph_chg < 0 THEN kph_chg ELSE NULL END), 0.0) AS KphMaxDown
            FROM RangeData GROUP BY d HAVING ({target_filter_sql}) AND ({kph_filter_sql})
        ), FilteredBase AS (SELECT b.* FROM base b JOIN TargetDates td ON td.d = b.d
        ), day_close AS (
            -- 【最終修正】改為從 base 讀取，避免受到分鐘級篩選影響
            SELECT d, MAX(ts) AS ts_day_close FROM base WHERE TIME(ts) <= '13:44:59' GROUP BY d
        ), night_close AS (
            SELECT x.d, MAX(x.ts) AS ts_night_close FROM (
                -- 【最終修正】改為從 base 讀取，避免受到分鐘級篩選影響
                SELECT DATE(CASE WHEN TIME(ts) < '05:00:00' THEN DATE_SUB(ts, INTERVAL 1 DAY) ELSE ts END) AS d, ts
                FROM base WHERE TIME(ts) >= '15:00:00' OR TIME(ts) < '05:00:00'
            ) x GROUP BY x.d
        ), All_Day_Close_TS AS (SELECT d, MAX(ts) AS ts_day_close FROM base WHERE TIME(ts) <= '13:44:59' GROUP BY d
        ), All_Night_Close_TS AS (
            SELECT x.d, MAX(x.ts) AS ts_night_close FROM (
                SELECT DATE(CASE WHEN TIME(ts) < '05:00:00' THEN DATE_SUB(ts, INTERVAL 1 DAY) ELSE ts END) AS d, ts
                FROM base WHERE TIME(ts) >= '15:00:00' OR TIME(ts) < '05:00:00'
            ) x GROUP BY x.d
        ), AllTradeDates AS (SELECT DISTINCT d FROM base ORDER BY d
        ), NextTradeDates AS (SELECT d AS d_today, LEAD(d, 1) OVER (ORDER BY d) AS d_next_trade FROM AllTradeDates
        ), next_trade AS (
            SELECT t.d AS d_today, ntd.d_next_trade FROM TargetDates t JOIN NextTradeDates ntd ON ntd.d_today = t.d WHERE ntd.d_next_trade IS NOT NULL
        ), today_day AS (SELECT dc.d, b.`FT價格` AS ft_day_close, b.`FT漲跌` AS ft_day_chg, b.`價平和(價平)` AS kph_day_close FROM day_close dc JOIN base b ON b.ts = dc.ts_day_close
        ), today_night AS (SELECT nc.d, b.`FT價格` AS ft_night_close, b.`FT漲跌` AS ft_night_chg, b.`價平和(價平)` AS kph_night_close FROM night_close nc JOIN base b ON b.ts = nc.ts_night_close
        ), nd_day AS (SELECT nt.d_today AS d, b.`FT價格` AS ft_nd_day_close, b.`FT漲跌` AS ft_nd_day_chg, b.`價平和(價平)` AS kph_nd_day_close FROM next_trade nt JOIN All_Day_Close_TS d2 ON d2.d = nt.d_next_trade JOIN base b ON b.ts = d2.ts_day_close
        ), nd_night AS (SELECT nt.d_today AS d, b.`FT價格` AS ft_nd_night_close, b.`FT漲跌` AS ft_nd_night_chg, b.`價平和(價平)` AS kph_nd_night_close FROM next_trade nt JOIN All_Night_Close_TS n2 ON n2.d = nt.d_next_trade JOIN base b ON b.ts = n2.ts_night_close
        )
        SELECT
            t.d AS 日期,
            CASE DAYOFWEEK(t.d) WHEN 1 THEN '日' WHEN 2 THEN '一' WHEN 3 THEN '二' WHEN 4 THEN '三' WHEN 5 THEN '四' WHEN 6 THEN '五' WHEN 7 THEN '六' END AS 星期,
            t.ft_day_close AS `FT日盤收盤`, t.ft_day_chg AS `FT漲跌(日盤)`, tn.ft_night_close AS `FT夜盤收盤`, tn.ft_night_chg AS `FT漲跌(夜盤)`,
            t.kph_day_close AS `日盤收盤的價平和(價平)`, tn.kph_night_close AS `夜盤收盤的價平和(價平)`,
            nd.ft_nd_day_close AS `FT次交易日日盤收盤`, nd.ft_nd_day_chg AS `FT次交易日(FT漲跌-日盤)`, nn.ft_nd_night_close AS `FT次交易日夜盤收盤`, nn.ft_nd_night_chg AS `FT次交易日(FT漲跌-夜盤)`,
            nd.kph_nd_day_close AS `次交易日日盤收盤的價平和(價平)`, nn.kph_nd_night_close AS `次交易日夜盤收盤的價平和(價平)`
        FROM TargetDates td JOIN today_day t ON t.d = td.d
        LEFT JOIN today_night tn ON tn.d = t.d LEFT JOIN nd_day nd ON nd.d = t.d LEFT JOIN nd_night nn ON nn.d = t.d
        WHERE DAYOFWEEK(t.d) IN ({wk_sql}) ORDER BY t.d DESC;
        """
        df, dates_list = pd.DataFrame(), []
        with st.spinner("🚀 正在執行查詢..."):
            try:
                conn = st.connection("mysql", type="sql")
                df = conn.query(sql, params=main_params)
            except Exception as e:
                st.error(f"查詢雲端資料庫失敗！錯誤訊息：{e}")
                st.session_state['__df_snapshot__'] = pd.DataFrame(); st.session_state['__date_list_snapshot__'] = []
                return []
        count_days = len(df); st.info(f"符合篩選條件的交易日數：**{count_days}** 天")
        if df.empty:
            st.warning("沒有資料符合您的篩選條件。"); st.session_state['__df_snapshot__'] = pd.DataFrame(); st.session_state['__date_list_snapshot__'] = []
            return []
        dates_list = pd.to_datetime(df["日期"]).dt.strftime('%Y-%m-%d').unique().tolist() if "日期" in df.columns else []
        st.session_state['__date_list_snapshot__'] = dates_list; st.session_state['__df_snapshot__'] = df.copy()
        _render_table(df, start_date, end_date, mode, weekdays); return dates_list
    elif is_snapshot_available:
        df = st.session_state['__df_snapshot__']; dates_list = st.session_state['__date_list_snapshot__']
        st.info(f"符合篩選條件的交易日數：**{len(df)}** 天")
        _render_table(df, start_date, end_date, mode, weekdays); return dates_list
    else:
        st.info("請點擊 **🚀 執行查詢** 按鈕開始查詢。"); return []