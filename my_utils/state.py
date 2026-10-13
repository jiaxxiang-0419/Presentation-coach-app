import streamlit as st

def init_session():
    """アプリ全体で使う共通の変数を初期化する関数"""
    
    # --- 基本設定 ---
    if "view" not in st.session_state: st.session_state.view = "home"
    if "theme" not in st.session_state: st.session_state.theme = "light"
    if "mode" not in st.session_state: st.session_state.mode = None
    
    # --- 練習モード用 ---
    if "page_num" not in st.session_state: st.session_state.page_num = 0
    if "stopwatch_active" not in st.session_state: st.session_state.stopwatch_active = False
    if "stopwatch_seconds" not in st.session_state: st.session_state.stopwatch_seconds = 0
    if "scripts" not in st.session_state: st.session_state.scripts = {}
    if "selected_pdf_bytes" not in st.session_state: st.session_state.selected_pdf_bytes = None
    if "slide_name" not in st.session_state: st.session_state.slide_name = "新規プレゼン資料"
    if "slide_timestamps" not in st.session_state: st.session_state.slide_timestamps = {}
    if "last_slide_speed_verdict" not in st.session_state: st.session_state.last_slide_speed_verdict = ""
    if "opt_record" not in st.session_state: st.session_state.opt_record = True
    if "opt_speed" not in st.session_state: st.session_state.opt_speed = True
    if "opt_filler" not in st.session_state: st.session_state.opt_filler = True
    if "current_advice" not in st.session_state: 
        st.session_state.current_advice = "まずは冒頭で『結論（ゴール）』をスッと提示し、聞き手を迷子にさせないロードマップを示しましょう。"
        
    # --- 練習モード追加分（終了トリガー＆JS連携用） ---
    if "trigger_exit_p" not in st.session_state: st.session_state.trigger_exit_p = False
    if "js_sync_practice" not in st.session_state: st.session_state.js_sync_practice = None
    
    # --- 本番モード用 ---
    if "secure_mode" not in st.session_state: st.session_state.secure_mode = False
    if "live_target_minutes" not in st.session_state: st.session_state.live_target_minutes = 5
    if "live_timeline" not in st.session_state: st.session_state.live_timeline = []
    if "live_final_fillers" not in st.session_state: st.session_state.live_final_fillers = 0
    if "room_url" not in st.session_state: st.session_state.room_url = ""
    if "booked_time" not in st.session_state: st.session_state.booked_time = ""
    if "booked_room" not in st.session_state: st.session_state.booked_room = ""
    if "time_last_changed" not in st.session_state: st.session_state.time_last_changed = 0.0
    if "reset_js_flag" not in st.session_state: st.session_state.reset_js_flag = False
    if "trigger_exit_l" not in st.session_state: st.session_state.trigger_exit_l = False
    if "js_sync_live" not in st.session_state: st.session_state.js_sync_live = None
    
    # --- ペルソナ機能用 ---
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'persona' not in st.session_state: st.session_state.persona = None