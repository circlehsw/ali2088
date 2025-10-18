# 檔案：1_Multi_Filter_Display.py (雲端資料庫版本)
import pandas as pd
import streamlit as st
from datetime import timedelta
from typing import List

from five_standard import render as render_five
from output_multi_filter import render_output
from Trend import TrendOptions, make_trend
from daily_seamless_trend import _fetch_intraday_data as _fetch_trend_data_for_days

TABLE = "atm"
DATE_COL = "時間戳記"
DEFAULT_MODE = "1344"
FT_COL = "FT價格"

def render_page():
    st.subheader("1. 基礎篩選 (日期/Mode/星期)")
    fs = render_five(table=TABLE, date_col=DATE_COL, default_mode=DEFAULT_MODE)
    st.subheader("2. 分鐘級數據篩選區間")
    col_l, col_gap, col_r = st.columns([1, 0.1, 1])
    with col_l:
        st.markdown("##### 🎯 價格/**區間漲跌點** 區間")
        ft_filter_mode = st.selectbox("FT價格 篩選", ["不篩選", "啟用篩選"], key='ft_filter_mode_select', index=0)
        min_ft_price, max_ft_price = None, None
        if ft_filter_mode == '啟用篩選':
            st.markdown("**FT價格 區間**"); c_l1, c_l2 = st.columns(2)
            with c_l1: min_ft_price = st.number_input("最小值", min_value=0, max_value=50000, value=8000, step=1, key='filter_min_ft_price_input')
            with c_l2: max_ft_price = st.number_input("最大值", min_value=0, max_value=50000, value=30000, step=1, key='filter_max_ft_price_input')
        st.markdown("---"); st.markdown("**區間最高漲點/最大跌點**")
        filter_target = st.selectbox("選擇篩選目標", ["不篩選", "區間最高漲點 (Max Up)", "區間最大跌點 (Max Down)"], key='filter_target_select')
        min_value, max_value = 0.0, 0.0
        if filter_target != "不篩選":
            c_l3, c_l4 = st.columns(2)
            min_limit, max_limit = (0, 2000) if filter_target == "區間最高漲點 (Max Up)" else (-2000, 0)
            default_min, default_max = (100, 500) if filter_target == "區間最高漲點 (Max Up)" else (-500, -100)
            with c_l3: min_value = st.number_input("最小值", min_value=min_limit, max_value=max_limit, value=default_min, step=1, key='filter_min_val_input')
            with c_l4: max_value = st.number_input("最大值", min_value=min_limit, max_value=max_limit, value=default_max, step=1, key='filter_max_val_input')
    with col_r:
        st.markdown("##### ⏳ 價平和與時間區間")
        kph_filter_mode = st.selectbox("價平和 篩選", ["不篩選", "啟用篩選"], key='kph_filter_mode_select', index=0)
        min_kph, max_kph = None, None
        if kph_filter_mode == '啟用篩選':
            st.markdown("**價平和 區間**"); c_r1, c_r2 = st.columns(2)
            with c_r1: min_kph = st.number_input("最小值", min_value=0, max_value=2000, value=0, step=1, key='filter_min_kph_input')
            with c_r2: max_kph = st.number_input("最大值", min_value=0, max_value=2000, value=800, step=1, key='filter_max_kph_input')
        st.markdown("---"); st.markdown("**價平和漲跌 區間**")
        filter_kph_change_target = st.selectbox( "選擇篩選目標", ["不篩選", "價平和上漲", "價平和下跌"], key='filter_kph_change_target_select')
        min_kph_change_value, max_kph_change_value = 0.0, 0.0
        if filter_kph_change_target != "不篩選":
            c_r3, c_r4 = st.columns(2)
            kph_min_limit, kph_max_limit = (0, 1000) if filter_kph_change_target == "價平和上漲" else (-1000, 0)
            kph_default_min, kph_default_max = (50, 300) if filter_kph_change_target == "價平和上漲" else (-300, -50)
            with c_r3: min_kph_change_value = st.number_input("最小值", min_value=kph_min_limit, max_value=kph_max_limit, value=kph_default_min, step=1, key='filter_kph_change_min_val_input')
            with c_r4: max_kph_change_value = st.number_input("最大值", min_value=kph_min_limit, max_value=kph_max_limit, value=kph_default_max, step=1, key='filter_kph_change_max_val_input')
        st.markdown("---")
        time_filter_mode = st.selectbox("分鐘級時間 篩選", ["不篩選", "啟用篩選"], key='time_filter_mode_select', index=0)
        min_time, max_time = None, None
        if time_filter_mode == '啟用篩選':
            st.markdown("**分鐘級時間區間 (HH:MM)**"); hour_options, minute_options = [f"{h:02d}" for h in range(24)], [f"{m:02d}" for m in range(0, 60, 5)]; c_h_min, c_m_min, c_gap1, c_h_max, c_m_max, c_gap2 = st.columns([1, 1, 0.5, 1, 1, 0.5])
            with c_h_min: min_h = st.selectbox("起始 時", hour_options, index=8, key='filter_min_h')
            with c_m_min: min_m = st.selectbox("起始 分", minute_options, index=9, key='filter_min_m')
            with c_h_max: max_h = st.selectbox("結束 時", hour_options, index=13, key='filter_max_h')
            with c_m_max: max_m = st.selectbox("結束 分", minute_options, index=9, key='filter_max_m')
            min_time, max_time = f"{min_h}:{min_m}", f"{max_h}:{max_m}"
    st.subheader("3. 交易日清單（符合所有條件）")
    date_choices = []
    if isinstance(fs, dict):
        date_choices = render_output(
            table=TABLE, date_col=DATE_COL, start_date=fs.get('start_date'), end_date=fs.get('end_date'),
            mode=fs.get('mode'), weekdays=fs.get('weekdays'),
            ft_price_filter_enabled=(ft_filter_mode == '啟用篩選'), min_ft_price=float(min_ft_price or 0.0), max_ft_price=float(max_ft_price or 0.0),
            kph_filter_enabled=(kph_filter_mode == '啟用篩選'), min_kph=float(min_kph or 0.0), max_kph=float(max_kph or 0.0),
            time_filter_enabled=(time_filter_mode == '啟用篩選'), min_time=min_time or "00:00", max_time=max_time or "23:59",
            filter_target=filter_target, min_value=float(min_value), max_value=float(max_value),
            filter_kph_change_target=filter_kph_change_target, min_kph_change_value=float(min_kph_change_value), max_kph_change_value=float(max_kph_change_value),
        )
    else: st.error("🚨 錯誤：基礎篩選模組 **five_standard** 執行失敗或未返回有效結果。")
    date_choices = date_choices if isinstance(date_choices, list) else []
    if date_choices:
        st.markdown("---"); st.subheader("4. 趨勢圖顯示"); default_day = date_choices[0]; n_days_options = [1, 2, 3, 5, 7, 10]; c1, c2 = st.columns([1, 1])
        base_day_key = st.session_state.get('trend_base_day', default_day)
        base_day_index = date_choices.index(base_day_key) if base_day_key in date_choices else 0
        with c1: base_day = st.selectbox("選擇繪圖起始日", date_choices, index=base_day_index, key="trend_base_day")
        with c2: n_days = st.selectbox("顯示天數", n_days_options, key="trend_n_days", format_func=lambda x: f"{x} 天")
        n_days_int = int(n_days); start_dt = pd.to_datetime(base_day, errors='coerce').normalize(); need_days = []
        if pd.notna(start_dt):
            for i in range(n_days_int): need_days.append((start_dt + timedelta(days=i)).strftime('%Y-%m-%d'))
        if not need_days: st.warning(f"無法從選定起始日 {base_day} 計算出連續交易日。")
        mode_val = fs.get('mode', DEFAULT_MODE)
        rows_df = _fetch_trend_data_for_days(TABLE, DATE_COL, mode_val, need_days)
        if rows_df.empty: st.warning(f"在選定的 {len(need_days)} 個日曆天中，沒有資料符合篩選條件。")
        else:
            try:
                ft_base_price = None
                try:
                    first_row = rows_df.iloc[0]; ft_price = pd.to_numeric(first_row.get(FT_COL), errors='coerce')
                    ft_change_col_name = "FT漲跌" if "FT漲跌" in rows_df.columns else "漲跌價"
                    if ft_change_col_name in rows_df.columns:
                        ft_change = pd.to_numeric(first_row.get(ft_change_col_name), errors='coerce')
                        if pd.notna(ft_price) and pd.notna(ft_change):
                            ft_base_price = ft_price - ft_change
                            st.caption(f"📈 Y 軸基準點已設為：{ft_base_price:,.0f} (來自 {first_row[DATE_COL]} 的價格 {ft_price:,.0f} 與漲跌 {ft_change:+.0f})")
                except (IndexError, KeyError) as e: st.warning(f"無法計算 Y 軸基準點，將使用預設範圍。錯誤：{e}")
                opts = TrendOptions(start_date=base_day, days=n_days_int, time_col="dt", ft_col="FT價格", kph_cols=["價平和(價平)"], ft_base_price=ft_base_price)
                fig = make_trend(rows_df, opts); st.plotly_chart(fig, use_container_width=True)
            except ValueError as e: st.error(f"繪製趨勢圖失敗：{e}")