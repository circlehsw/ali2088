# -*- coding: utf-8 -*-
# 檔案：4_ATM_merge_interactive.py（已移除「趨勢圖批次生成與存檔」）
import os
import sys
import importlib
import streamlit as st

# --- 版面與標題 ---
st.set_page_config(layout="wide", page_title="ATM 資料多模組分析平台")
st.title("ATM 資料互動分析平台")

# --- 路徑啟動（確保能 import 0_Module 內的檔案） ---
ROOT = os.path.dirname(os.path.abspath(__file__))
MODULE_DIR = os.path.join(ROOT, "0_Module")
if MODULE_DIR not in sys.path:
    sys.path.insert(0, MODULE_DIR)

# --- 可用模組（已移除「趨勢圖批次生成與存檔」） ---
MODULES = {
    "🎯 1. 多條件篩選與趨勢圖顯示": "1_Multi_Filter_Display",
    "🔍 3. 趨勢相似度分析模組": "5_Trend_Similarity_Analyzer",
}

def _clear_and_reset():
    """清除所有狀態並回到預設模組"""
    st.session_state.clear()
    st.session_state["selected_module_name"] = list(MODULES.keys())[0]

# --- 側欄導覽 ---
with st.sidebar:
    st.header("功能模組導航")

    if "selected_module_name" not in st.session_state:
        st.session_state["selected_module_name"] = list(MODULES.keys())[0]

    selected_module_name = st.radio(
        "請選擇要執行的功能模組：",
        list(MODULES.keys()),
        index=list(MODULES.keys()).index(
            st.session_state.get("selected_module_name", list(MODULES.keys())[0])
        ),
        key="selected_module_name",
    )

    st.markdown("---")
    st.button(
        "↩️ 清除所有狀態",
        help="強制清除 Session State，重啟應用程式回到初始狀態。",
        key="global_reset_final",
        on_click=_clear_and_reset,
        use_container_width=True,
    )

# --- 載入與執行所選模組 ---
def load_module_and_render(module_name: str):
    try:
        module = importlib.import_module(module_name)
        importlib.reload(module)

        # 兩個模組的慣例入口
        if hasattr(module, "render_page"):
            module.render_page()
        elif hasattr(module, "render_page_similarity_analyzer"):
            module.render_page_similarity_analyzer()
        else:
            st.error(f"❌ 模組 '{module_name}.py' 未提供 render_page() 或 render_page_similarity_analyzer()。")
    except Exception as e:
        st.error(f"❌ 執行模組 '{module_name}' 時發生錯誤！")
        st.exception(e)

st.subheader(selected_module_name)
load_module_and_render(MODULES[selected_module_name])
