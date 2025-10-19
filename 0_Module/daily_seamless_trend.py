# 檔案：daily_seamless_trend.py (雲端資料庫 v2 - 最終修正版)

import pandas as pd
import numpy as np
import plotly.graph_objs as go
import streamlit as st
from typing import List
from datetime import time, timedelta

# --- 設定與常量 ---
TABLE   = "atm"
DATE_COL= "時間戳記"
FT_COL  = "FT價格"
KPH_COL = "價平和(價平)"
WEEKDAYS_CH = ['一', '二', '三', '四', '五', '六', '日']
TARGET_END_TIME_NIGHT = time(5, 0)
T_PLUS_1_CUTOFF = time(5, 1)
TARGET_END_TIME_DAY = time(13, 46)

# --- 1. 數據獲取與清理 ---

def _fetch_intraday_data(table, date_col, mode, date_list: List[str]) -> pd.DataFrame:
    """【雲端版 v2】獲取特定日期列表的分時數據 (修正 IN clause 語法)"""
    if not date_list:
        return pd.DataFrame()

    conn = st.connection("mysql", type="sql")

    # --- 【核心修正】---
    # 1. 產生與 date_list 長度相符的參數佔位符，例如 ( :date_0, :date_1, ... )
    date_placeholders = ", ".join([f":date_{i}" for i in range(len(date_list))])

    # 2. 準備 SQL 查詢，將佔位符直接放入 SQL 字串
    sql_query = f"""
        SELECT *
        FROM `{table}`
        WHERE LOWER(TRIM(mode)) = LOWER(TRIM(:mode))
          AND DATE(`{date_col}`) IN ( {date_placeholders} )
        ORDER BY `{date_col}`
    """
    
    # 3. 建立參數字典，包含 mode 和所有 date_list 裡的值
    params = {"mode": mode}
    for i, date_val in enumerate(date_list):
        params[f"date_{i}"] = date_val
    # --- 【修正結束】---

    rows_df = conn.query(sql_query, params=params, ttl=600)

    if rows_df.empty:
        return rows_df

    rows_df["dt"] = pd.to_datetime(rows_df[DATE_COL], errors="coerce")
    for c in [FT_COL, KPH_COL, "FT漲跌", "價平和漲跌(價平)"]:
        if c in rows_df.columns:
            rows_df[c] = pd.to_numeric(rows_df[c], errors="coerce")
    rows_df = rows_df.dropna(subset=["dt", FT_COL]).sort_values("dt").reset_index(drop=True)
    return rows_df


@st.cache_data
def _get_all_unique_dates(table, date_col, mode):
    """【雲端版】從數據庫獲取所有不重複的交易日"""
    conn = st.connection("mysql", type="sql")
    sql = f"""
        SELECT DISTINCT DATE(`{date_col}`) AS d
        FROM `{table}`
        WHERE LOWER(TRIM(mode)) = LOWER(TRIM(:mode))
        ORDER BY d
    """
    df = conn.query(sql, params={'mode': mode}, ttl=3600)
    # 確保返回的是字串格式 'YYYY-MM-DD'
    return df['d'].dt.strftime('%Y-%m-%d').tolist() if not df.empty else []


# --- 2. 核心：數據縫合與斷層處理 ---

@st.cache_data
def _prepare_seamless_data(df: pd.DataFrame, start_date_str: str, end_date_str: str) -> pd.DataFrame:
    if df.empty: return df
    MAX_TRADING_GAP_SEC = 10 * 60
    df['dt_date'] = df['dt'].dt.strftime('%Y-%m-%d')
    df['dt_time'] = df['dt'].dt.time
    start_date = start_date_str
    end_date = end_date_str
    cond1 = (df['dt_date'] == start_date) & (df['dt_time'] >= time(15, 0))
    cond2 = (df['dt_date'] == end_date) & (df['dt_time'] < T_PLUS_1_CUTOFF)
    dff = df[cond1 | cond2].copy()
    if dff.empty: return dff
    dff['x_sequence'] = dff.index
    dff = dff.sort_values('dt').reset_index(drop=True)
    new_data_list = []
    x_counter = 0
    for i in range(len(dff)):
        current_row = dff.iloc[i].copy()
        current_dt = current_row['dt']
        if i > 0:
            prev_dt = dff.iloc[i-1]['dt']
            time_diff = (current_dt - prev_dt).total_seconds()
            if time_diff > MAX_TRADING_GAP_SEC:
                nan_row = dff.iloc[i-1].copy()
                nan_row[[FT_COL, KPH_COL]] = np.nan
                nan_row['dt'] = prev_dt + timedelta(minutes=1)
                nan_row['x_sequence'] = x_counter
                new_data_list.append(nan_row)
                x_counter += 1
        current_row['x_sequence'] = x_counter
        new_data_list.append(current_row)
        x_counter += 1
    final_df = pd.DataFrame(new_data_list).reset_index(drop=True)
    return final_df


@st.cache_data
def _prepare_day_session_data(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df
    MAX_TRADING_GAP_SEC = 10 * 60
    df['dt_date'] = df['dt'].dt.strftime('%Y-%m-%d')
    df['dt_time'] = df['dt'].dt.time
    is_time_range = (df['dt_time'] >= time(8, 45)) & (df['dt_time'] <= TARGET_END_TIME_DAY)
    dff = df[is_time_range].copy()
    if dff.empty: return dff
    dff['x_sequence'] = np.arange(len(dff))
    dff = dff.sort_values('dt').reset_index(drop=True)
    new_data_list = []
    x_counter = 0
    for i in range(len(dff)):
        current_row = dff.iloc[i].copy()
        current_dt = current_row['dt']
        if i > 0:
            prev_dt = dff.iloc[i-1]['dt']
            time_diff = (current_dt - prev_dt).total_seconds()
            if time_diff > MAX_TRADING_GAP_SEC:
                nan_row = dff.iloc[i-1].copy()
                nan_row[FT_COL] = np.nan
                nan_row['dt'] = prev_dt + timedelta(minutes=1)
                nan_row['x_sequence'] = x_counter
                new_data_list.append(nan_row)
                x_counter += 1
        current_row['x_sequence'] = x_counter
        new_data_list.append(current_row)
        x_counter += 1
    final_df = pd.DataFrame(new_data_list).reset_index(drop=True)
    return final_df


# --- 3. 繪圖核心 ---

def make_seamless_daily_trend(df: pd.DataFrame, y_range: List[float], y_ticks: List[float], session_type: str) -> go.Figure:
    if df.empty:
        return go.Figure().update_layout(title="無數據")
    x_col = 'x_sequence'
    is_night_session = (session_type == "Night")
    fig = go.Figure()
    line_color = '#FF8C00' if is_night_session else '#1E90FF'
    fig.add_trace(go.Scatter(
        x=df[x_col],
        y=df[FT_COL],
        mode='lines',
        name='台指期價格',
        line=dict(color=line_color, width=1.0),
        connectgaps=False,
        customdata=[d.strftime("%Y-%m-%d %H:%M") for d in df['dt']],
        hovertemplate='日期時間: %{customdata}<br>價格: %{y:,.0f}<extra></extra>'
    ))
    df['dt_date'] = df['dt'].dt.date
    df['dt_time'] = df['dt'].dt.time
    unique_dates = sorted(df['dt_date'].unique())
    target_times_str = ['16:00', '18:00', '20:00', '22:00', '00:00', '02:00', '04:00'] if is_night_session else ['09:00', '11:00', '13:00']
    tick_indices = []
    tick_labels = []
    for t_str in target_times_str:
        h, m = map(int, t_str.split(':'))
        target_time_obj = time(h, m)
        if h >= 15:
            target_date = unique_dates[0]
        elif len(unique_dates) > 1:
            target_date = unique_dates[1]
        else:
            target_date = unique_dates[0]
        is_target_date = (df['dt_date'] == target_date)
        is_target_time_or_after = (df['dt_time'] >= target_time_obj)
        valid_points = df[is_target_date & is_target_time_or_after].sort_values('dt')
        if not valid_points.empty:
            x_val = valid_points['x_sequence'].iloc[0]
            dt_val = valid_points['dt'].iloc[0]
            if x_val not in tick_indices:
                tick_indices.append(x_val)
                date_part = dt_val.strftime("%Y-%m-%d")
                weekday_ch = WEEKDAYS_CH[dt_val.weekday()]
                label = f"{date_part}({weekday_ch})<br>{t_str}"
                tick_labels.append(label)
    if tick_indices:
        sorted_ticks = sorted(zip(tick_indices, tick_labels))
        tick_indices, tick_labels = zip(*sorted_ticks)
    else:
        tick_indices, tick_labels = [], []
    title_text = "夜盤交易時段 (15:00 ~ 次日 05:00，已壓縮)" if is_night_session else "日盤交易時段 (08:45 ~ 13:45，已壓縮)"
    fig.update_xaxes(
        title_text=title_text,
        tickvals=list(tick_indices),
        ticktext=list(tick_labels),
        showgrid=True,
        type='linear',
        tickangle=0
    )
    fig.update_yaxes(
        title_text="FT 價格",
        range=y_range,
        tickvals=y_ticks,
        showgrid=True,
        tickformat=',.0f'
    )
    fig.update_layout(
        title="單日連續交易時段趨勢圖 (FT 走勢)",
        height=600,
        hovermode="x",
        margin=dict(l=90, r=50, t=50, b=100),
        showlegend=False
    )
    return fig