circle_portable

Portable Streamlit app for your ATM interactive tools.

Structure:
- 4_ATM_merge_interactive.py — main interactive app
- 1_Multi_Filter_Display.py, 3_Batch_Trend_Generator.py, 5_Trend_Similarity_Analyzer.py — feature modules (imported by the main app)
- 0_Module/ — shared helper modules
- 3_DB/ATM_merge.db — put your SQLite DB here

Run:
1) Copy ATM_merge.db into 3_DB/
2) In terminal:
   cd <this-folder>
   streamlit run 4_ATM_merge_interactive.py