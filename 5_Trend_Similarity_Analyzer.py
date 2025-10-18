# 檔案：5_Trend_Similarity_Analyzer.py (雲端資料庫版本)
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from datetime import time, datetime
import calendar

from daily_seamless_trend import _fetch_intraday_data, _get_all_unique_dates
try: from dtw import dtw
except ImportError: st.error("錯誤：缺少 'dtw-python' 套件。請在終端機執行 `pip install dtw-python` 後再試一次。"); st.stop()

TABLE = "atm"
DATE_COL = "時間戳記"
DEFAULT_MODE = "1344"
FT_COL = "FT價格"
CHARTS_PER_ROW = 3
WEEKDAYS_CH = ['一', '二', '三', '四', '五', '六', '日']

def _normalize_series(series: pd.Series, method: str) -> pd.Series:
    if series.empty or len(series) < 2: return pd.Series(dtype=np.float64)
    if method == "Relative Magnitude": return series / series.iloc[0]
    elif method == "Pure Shape":
        min_val, max_val = series.min(), series.max()
        if max_val == min_val: return pd.Series(np.zeros(len(series)), index=series.index)
        return (series - min_val) / (max_val - min_val)
    return pd.Series(dtype=np.float64)

def _plot_comparison_chart(df: pd.DataFrame, title: str):
    if df.empty: return go.Figure().update_layout(title="無數據")
    df = df.copy(); reference_price = df[FT_COL].iloc[0]; df['price_change'] = df[FT_COL] - reference_price; df['weekday'] = df['dt'].dt.weekday.map(lambda x: WEEKDAYS_CH[x]); fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['dt'], y=df[FT_COL], mode='lines', name='FT 價格', customdata=df[['weekday', 'price_change']], hovertemplate=("日期: %{x|%Y-%m-%d} (%{customdata[0]})<br>時間: %{x|%H:%M}<br>價格: %{y:,.0f}<br>漲跌: %{customdata[1]:+,.0f}<extra></extra>")))
    fig.update_layout(title=title, xaxis_title="時間", yaxis_title="價格", height=300, margin=dict(l=40, r=20, t=40, b=40), hovermode="x unified")
    fig.update_xaxes(showspikes=True, spikethickness=1, spikedash='dot'); fig.update_yaxes(showspikes=True, spikethickness=1, spikedash='dot'); return fig

def display_results(template_df, template_date, top_results):
    st.markdown("---"); st.subheader("📈 分析結果"); col1, col2 = st.columns([1, 2])
    with col1: st.markdown(f"#### 基準範本"); st.plotly_chart(_plot_comparison_chart(template_df, f"日期: {template_date}"), use_container_width=True)
    with col2:
        st.markdown("#### 相似度排行榜 (分數越低越相似)"); display_df = pd.DataFrame(top_results)[['date', 'similarity_score']]; display_df['similarity_score'] = display_df['similarity_score'].round(4)
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.markdown("---")
    if top_results:
        st.markdown(f"#### Top {len(top_results)} 相似走勢圖"); num_results = len(top_results)
        for i in range(0, num_results, CHARTS_PER_ROW):
            cols = st.columns(CHARTS_PER_ROW); row_results = top_results[i : i + CHARTS_PER_ROW]
            for j, result in enumerate(row_results):
                with cols[j]: st.plotly_chart(_plot_comparison_chart(result['raw_data'], f"{result['date']} (Score: {result['similarity_score']:.2f})"), use_container_width=True)

def render_page_similarity_analyzer():
    st.markdown("##### 透過選擇「基準範本」與「時間區間」，找出歷史上走勢最相似的交易日。")
    with st.container(border=True):
        all_days = _get_all_unique_dates(TABLE, DATE_COL, DEFAULT_MODE); all_days_set = set(all_days)
        if not all_days: st.error("無法從資料庫讀取有效的交易日清單。"); return
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            st.markdown("**1. 選擇基準範本日期**"); sc1, sc2, sc3 = st.columns(3); years = sorted(list(set([d.split('-')[0] for d in all_days]))); months = [f"{i:02d}" for i in range(1, 13)]; default_y, default_m, default_d = all_days[-1].split('-')
            with sc1: selected_year = st.selectbox("年", years, index=years.index(default_y), key="year_selector", label_visibility="collapsed")
            with sc2: selected_month = st.selectbox("月", months, index=months.index(default_m), key="month_selector", label_visibility="collapsed")
            days_in_month = calendar.monthrange(int(selected_year), int(selected_month))[1]; days = [f"{i:02d}" for i in range(1, days_in_month + 1)]; day_index = days.index(default_d) if default_d in days else len(days) - 1
            with sc3: selected_day = st.selectbox("日", days, index=day_index, key="day_selector", label_visibility="collapsed")
            template_date = f"{selected_year}-{selected_month}-{selected_day}"
        with c2: st.markdown("**2. 設定開始時間**"); start_time = st.time_input("開始時間", value=time(9, 0), key="start_time_selector", label_visibility="collapsed")
        with c3: st.markdown("**3. 設定結束時間**"); end_time = st.time_input("結束時間", value=time(10, 0), key="end_time_selector", label_visibility="collapsed")
        c4, c5, c6 = st.columns([2, 2, 1])
        with c4: norm_method = st.selectbox("**4. 分析方法 (功力旋鈕)**", options=["Relative Magnitude", "Pure Shape"], index=0, help="**Relative Magnitude**: 注重相對漲跌幅度與力道。\n\n**Pure Shape**: 只看走勢形狀，忽略波動大小。", key="norm_method_selector")
        with c5: top_n_selection = st.selectbox("**5. 顯示結果數量**", options=[15, 30, 45, "不限制"], index=3, key="top_n_selector")
        with c6: st.markdown("<br/>", unsafe_allow_html=True); run_analysis = st.button("🚀 開始分析", type="primary", use_container_width=True)
        st.caption(f"✅ 日期 `{template_date}` 是有效交易日" if template_date in all_days_set else f"⚠️ 日期 `{template_date}` 非資料庫中的交易日")
    if run_analysis:
        if template_date not in all_days_set: st.error(f"分析中止：選擇的日期 {template_date} 不是一個有效的交易日，請重新選擇。"); return
        top_n = None if top_n_selection == "不限制" else top_n_selection; start_dt, end_dt = datetime.combine(datetime.strptime(template_date, '%Y-%m-%d'), start_time), datetime.combine(datetime.strptime(template_date, '%Y-%m-%d'), end_time)
        if start_dt >= end_dt: st.error("錯誤：開始時間必須早於結束時間。")
        else:
            progress_bar = st.progress(0, text="正在初始化分析..."); template_df_raw = _fetch_intraday_data(TABLE, DATE_COL, DEFAULT_MODE, [template_date]); template_df = template_df_raw[(template_df_raw['dt'] >= start_dt) & (template_df_raw['dt'] <= end_dt)]
            if len(template_df) < 5: st.warning(f"基準範本 ({template_date}) 在指定時間區間內的數據不足 (少於5筆)，請更換日期或擴大時間區間。")
            else:
                template_series_norm = _normalize_series(template_df[FT_COL].reset_index(drop=True), norm_method); results = []; total_days = len(all_days)
                for i, day in enumerate(all_days):
                    progress_bar.progress((i + 1) / total_days, text=f"正在比對 {day}...");
                    if day == template_date: continue
                    day_dt_obj, day_start_dt, day_end_dt = datetime.strptime(day, '%Y-%m-%d'), datetime.combine(datetime.strptime(day, '%Y-%m-%d'), start_time), datetime.combine(datetime.strptime(day, '%Y-%m-%d'), end_time)
                    historical_df_raw = _fetch_intraday_data(TABLE, DATE_COL, DEFAULT_MODE, [day]); historical_df = historical_df_raw[(historical_df_raw['dt'] >= day_start_dt) & (historical_df_raw['dt'] <= day_end_dt)]
                    if len(historical_df) >= 5:
                        historical_series_norm = _normalize_series(historical_df[FT_COL].reset_index(drop=True), norm_method)
                        distance = dtw(template_series_norm.values, historical_series_norm.values, distance_only=True).distance
                        results.append({"date": day, "similarity_score": distance, "raw_data": historical_df})
                progress_bar.empty()
                if not results: st.warning("找不到任何可用於比對的歷史數據。")
                else: display_results(template_df, template_date, sorted(results, key=lambda x: x['similarity_score'])[:top_n])
    else: st.info("請設定好以上參數後，點擊「開始分析」按鈕。")