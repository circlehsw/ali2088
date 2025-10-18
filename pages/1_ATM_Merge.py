# pages/1_ATM_Merge.py — 將「4_ATM_merge_interactive.py」包成 Streamlit 子頁
import os, sys, types, importlib.util, traceback
import streamlit as st

st.set_page_config(page_title="ATM Merge Interactive", page_icon="🧩", layout="wide")
st.title("🧩 ATM Merge Interactive")

# 讓 modules 可以 import 到專案根目錄的模組
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 你原本的互動式腳本檔名（就放在專案根目錄）
ORIG_FILE = os.path.join(PROJECT_ROOT, "4_ATM_merge_interactive.py")

if not os.path.exists(ORIG_FILE):
    st.error(f"找不到檔案：{ORIG_FILE}")
    st.stop()

# 給模組一個乾淨的 module 物件，避免頂層執行汙染全域
def _load_module_from_path(name: str, path: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # 會執行原檔頂層程式碼
    return mod

st.caption("此頁會載入原始檔執行；如檔內有 `main()` / `run()` / `app()` 會優先呼叫。")

try:
    mod = _load_module_from_path("atm_merge_interactive_orig", ORIG_FILE)

    # 若你的互動式檔案本身已用 Streamlit，且以函式包起來，這裡會優先呼叫
    entry = None
    for candidate in ("main", "run", "app"):
        if hasattr(mod, candidate) and callable(getattr(mod, candidate)):
            entry = getattr(mod, candidate)
            break

    if entry:
        st.info(f"偵測到函式 `{entry.__name__}()`，直接呼叫。")
        entry()  # 呼叫你檔案內的主程式
    else:
        st.warning("未偵測到 main()/run()/app()，已直接執行原檔頂層程式碼。若畫面沒有東西，代表原檔不是用 Streamlit 繪製 UI。")
        # 注意：上面的 _load_module_from_path 已執行過頂層程式碼；這裡不再 exec。

    st.success("載入完成 ✅")

except Exception as e:
    st.error("載入或執行發生例外")
    st.exception(e)
    st.code("".join(traceback.format_exc()))
