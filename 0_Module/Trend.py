# === Portable path bootstrap (auto) ===
import os, sys
_THIS_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = _THIS_FILE_DIR if os.path.basename(_THIS_FILE_DIR) != "0_Module" else os.path.dirname(_THIS_FILE_DIR)
_MODULE_PATH = os.path.join(_ROOT_DIR, "0_Module")
if _MODULE_PATH not in sys.path:
    sys.path.insert(0, _MODULE_PATH)
# Unified DB path for the whole project
DB_PATH = os.path.join(_ROOT_DIR, "3_DB", "ATM_merge.db")
# === End path bootstrap ===

# -*- coding: utf-8 -*-
# 檔案：Trend.py (最終穩定版：優化 Hover 格式與線條視覺)
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import pandas as pd
import plotly.graph_objs as go
import numpy as np

@dataclass
class TrendOptions:
    start_date: str
    days: int = 3
    time_col: str = "dt"
    ft_col: str = "FT價格"
    ft_chg_col_candidates: Tuple[str, ...] = ("FT漲跌", "漲跌價")
    kph_cols: List[str] = field(default_factory=lambda: ["價平和(價平)"])
    kph_ratio: float = 0.40 # 價平和佔 Y 軸比例 (40%)
    # 【新增】增加 Y 軸基準點參數
    ft_base_price: Optional[float] = None

WEEK = "一二三四五六日"

# --- 輔助函數 (為 Hover 統一化優化) ---

def _fmt_dt_with_week(series_dt: pd.Series) -> list:
    out = []
    for dt in pd.to_datetime(series_dt, errors="coerce"):
        if pd.isna(dt): out.append(""); continue
        wk_idx = dt.weekday()
        wk = WEEK[wk_idx] if 0 <= wk_idx <= 6 else WEEK[6]
        out.append(dt.strftime(f"%Y-%m-%d ({wk}) %H:%M"))
    return out

def _pick_first_column(df: pd.DataFrame, candidates: Tuple[str, ...]) -> Optional[str]:
    for c in candidates:
        if c in df.columns: return c
    return None

def _ft_text_with_change(df: pd.DataFrame, ft_col: str, chg_col_candidates: Tuple[str, ...]) -> list:
    ft = pd.to_numeric(df[ft_col], errors="coerce")
    chg_col = _pick_first_column(df, chg_col_candidates)

    if chg_col is None or chg_col not in df.columns:
        return [f"{x:,.0f}" if pd.notna(x) else "" for x in ft]

    chg = pd.to_numeric(df[chg_col], errors="coerce")
    txt = []
    for a, b in zip(ft, chg):
        if pd.isna(a): txt.append(""); continue
        if pd.isna(b): txt.append(f"{a:,.0f}"); continue
        # 使用 :+.0f 格式化：自動包含 +/- 號，只會有一個 + 號
        change_text = f"{b:+.0f}"
        txt.append(f"{a:,.0f} ({change_text})") # 格式: 價格 (+/-漲跌價)
    return txt

def _kph_text_with_change(df: pd.DataFrame, kph_col: str) -> list:
    kph = pd.to_numeric(df[kph_col], errors="coerce")
    chg_col = "價平和漲跌(價平)"

    if chg_col not in df.columns:
        return [f"{x:,.0f}" if pd.notna(x) else "" for x in kph]

    chg = pd.to_numeric(df[chg_col], errors="coerce")
    txt = []
    for a, b in zip(kph, chg):
        if pd.isna(a): txt.append(""); continue
        if pd.isna(b): txt.append(f"{a:,.0f}"); continue
        # 使用 :+.0f 格式化：自動包含 +/- 號，只會有一個 + 號
        change_text = f"{b:+.0f}"
        txt.append(f"{a:,.0f} ({change_text})") # 格式: 價格 (+/-漲跌價)
    return txt

def map_y(y, y_min, y_max, t_min, t_max):
    if y_max - y_min == 0: return (t_max + t_min) / 2
    return (y - y_min) / (y_max - y_min) * (t_max - t_min) + t_min

# --- 核心繪圖函數 ---

def make_trend(df: pd.DataFrame, opts: TrendOptions) -> go.Figure:

    dff = df.copy()
    for col in [opts.ft_col] + (opts.kph_cols or []):
        if col in dff.columns:
            dff[col] = pd.to_numeric(dff[col], errors="coerce")
    dff = dff.dropna(subset=[opts.time_col]).sort_values(opts.time_col).reset_index(drop=True)

    if dff.empty: raise ValueError("DataFrame 為空或關鍵欄位值為空，無法繪製趨勢圖。")

    # 數據範圍計算
    kph_cols_valid = [c for c in opts.kph_cols if c in dff.columns]
    kph_all = pd.concat([dff[c] for c in kph_cols_valid]).dropna()

    # 【關鍵修正】價平和的最小值直接使用 0
    kph_min = 0 # kph_all.min() if not kph_all.empty else 0

    kph_max = kph_all.max() if not kph_all.empty else 0
    if kph_max - kph_min < 1: kph_max += 1 # 確保有範圍

    ft_valid = dff[opts.ft_col].dropna()
    ft_min = ft_valid.min() if not ft_valid.empty else 0
    ft_max = ft_valid.max() if not ft_valid.empty else 0
    if ft_max - ft_min < 1: ft_min -= 10; ft_max += 10

    # --- 【核心修改】如果傳入了 Y 軸基準點，則以此為中心重新計算 Y 軸範圍 ---
    if opts.ft_base_price is not None:
        # 以基準點為中心，計算上下對稱的最大振幅
        max_deviation = max(abs(ft_max - opts.ft_base_price), abs(ft_min - opts.ft_base_price))
        # 根據最大振幅，重新定義 Y 軸的 min / max，確保對稱
        ft_min = opts.ft_base_price - max_deviation
        ft_max = opts.ft_base_price + max_deviation
    # --- 【修改結束】 ---
    
    # Y 軸分段比例定義：KPH 40%, FT 60%
    kph_seg = (0, opts.kph_ratio) # 0 to 0.4
    ft_seg = (opts.kph_ratio, 1) # 0.4 to 1.0

    # 數據映射
    for c in kph_cols_valid:
        dff[f'{c}_mapped'] = dff[c].apply(lambda y: map_y(y, kph_min, kph_max, kph_seg[0], kph_seg[1]))
    dff[f'{opts.ft_col}_mapped'] = dff[opts.ft_col].apply(lambda y: map_y(y, ft_min, ft_max, ft_seg[0], ft_seg[1]))

    # --- 準備統一 Hover 數據 ---
    dff['ft_text_hover'] = _ft_text_with_change(dff, opts.ft_col, opts.ft_chg_col_candidates)
    dff['kph_text_hover'] = _kph_text_with_change(dff, kph_cols_valid[0])
    dff['time_text_hover'] = _fmt_dt_with_week(dff[opts.time_col])

    # 建立統一 Hover 提示框的內容
    dff['unified_hover'] = (
        dff['time_text_hover'] + '<br>' +
        'FT價格：' + dff['ft_text_hover'] + '<br>' +
        '價平和：' + dff['kph_text_hover']
    )
    # --- 統一 Hover 數據準備完畢 ---


    # 繪圖
    fig = go.Figure()
    # 定義用於線條分段的顏色
    color_palette = ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf"]

    unique_dates = sorted(dff[opts.time_col].dt.strftime("%Y-%m-%d").unique().tolist())

    # ------------------- 按日分段繪圖 (換日換色 & 單一圖例 & 忽略 Hover) -------------------

    for i, d in enumerate(unique_dates):
        sub = dff[dff[opts.time_col].dt.strftime("%Y-%m-%d")==d].copy()
        if sub.empty: continue
        is_first_day = (i == 0)

        day_color = color_palette[i % len(color_palette)]

        # 1. FT 價格線
        if opts.ft_col in sub.columns:
            fig.add_trace(go.Scatter(
                x=sub[opts.time_col], y=sub[f'{opts.ft_col}_mapped'],
                mode="lines",
                # FT 線徑 1.0
                line=dict(color=day_color, width=1.0),
                name='FT價格',
                legendgroup='FT_Group',
                showlegend=is_first_day,
                hoverinfo='skip',
            ))

        # 2. 價平和線
        if kph_cols_valid:
            kcol = kph_cols_valid[0]
            fig.add_trace(go.Scatter(
                x=sub[opts.time_col], y=sub[f'{kcol}_mapped'],
                mode="lines",
                # 價平和線徑 0.8
                line=dict(color=day_color, width=0.8, dash="dot"),
                name=kcol,
                legendgroup='KPH_Group',
                showlegend=is_first_day,
                hoverinfo='skip',
            ))

    # ------------------- 統一 Hover 追蹤 (Invisible Trace) -------------------

    # 新增一個完全透明的追蹤，它負責提供所有統一的 Hover 資訊
    fig.add_trace(go.Scatter(
        x=dff[opts.time_col],
        y=dff[f'{opts.ft_col}_mapped'],
        mode='lines',
        line=dict(width=0, color='rgba(0,0,0,0)'),
        name='統一查價線',
        showlegend=False,
        hoverinfo='text',
        hovertemplate='%{text}<extra></extra>',
        text=dff['unified_hover'],
    ))

    # ------------------- 軸線和佈局設定 -------------------

    # 刻度計算
    k_min_val = 0 # 直接使用 0 作為最小值
    k_max_val = kph_max # 使用數據中的最大值
    k_mid_val = (k_min_val + k_max_val) / 2

    # 映射後的刻度位置
    k_ticks = [
        map_y(k_min_val, k_min_val, k_max_val, kph_seg[0], kph_seg[1]),
        map_y(k_mid_val, k_min_val, k_max_val, kph_seg[0], kph_seg[1]),
        map_y(k_max_val, k_min_val, k_max_val, kph_seg[0], kph_seg[1])
    ]
    # 刻度文字
    k_labels = [f"{k_min_val:,.0f}", f"{k_mid_val:,.0f}", f"{k_max_val:,.0f}"] if kph_cols_valid else ["", "", ""]

    ft_grid = 4
    ft_ticks = [map_y(ft_min + (ft_max - ft_min) * i / ft_grid, ft_min, ft_max, ft_seg[0], ft_seg[1]) for i in range(ft_grid + 1)]
    ft_labels = [f"{ft_min + (ft_max - ft_min) * i / ft_grid:,.0f}" for i in range(ft_grid + 1)]

    xmin = dff[opts.time_col].min()
    xmax = dff[opts.time_col].max()

    fig.update_yaxes(
        title_text="台指期 (60%) & 價平和 (40%)",
        range=[0, 1],
        tickvals=k_ticks + ft_ticks,
        ticktext=k_labels + ft_labels,
        showgrid=True,
    )

    # 強制顯示垂直查價線
    fig.update_xaxes(
        range=[xmin, xmax],
        showgrid=True,
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikethickness=1,
        spikedash="solid",
        spikecolor="#888888",
        rangeselector=dict(
            buttons=[
                dict(count=1, label="1h", step="hour", stepmode="backward"),
                dict(count=6, label="6h", step="hour", stepmode="backward"),
                dict(count=1, label="1d", step="day", stepmode="backward"),
                dict(step="all")
            ]
        )
    )

    # 調整 Hover Label 樣式，並設定 Hovermode
    fig.update_layout(
        title=f"趨勢圖：從 {opts.start_date} 起連續 {len(unique_dates)} 個交易日",
        height=700,
        hovermode="x",
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="sans-serif",
        ),
        margin=dict(l=50, r=50, t=50, b=50),
        shapes=[
            dict(
                type="line", xref="paper", yref="paper",
                x0=0, y0=opts.kph_ratio, x1=1, y1=opts.kph_ratio,
                line=dict(color="black", width=2, dash="dashdot"),
            )
        ]
    )

    return fig