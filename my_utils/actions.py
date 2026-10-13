import streamlit as st
import time
from my_utils.db_manager import delete_slide_by_id, get_slide_by_id

def handle_delete_slide(slide_id, slide_name):
    """資料を削除してメッセージを表示する"""
    current_user = st.session_state.get("current_user", "default_user")
    
    # 削除を実行
    delete_slide_by_id(slide_id, username=current_user)
    
    # メッセージを出して1秒待ってから画面をリロード
    st.success(f"「{slide_name}」を削除しました。")
    time.sleep(1)
    st.rerun()

def handle_start_practice(slide_id, slide_name):
    """資料を読み込んで練習画面へ移動する"""
    current_user = st.session_state.get("current_user", "default_user")

    st.session_state.selected_pdf_bytes = get_slide_by_id(slide_id, username=current_user)
    st.session_state.slide_name = slide_name
    
    st.session_state.page_num = 0
    st.session_state.filler_count = 0
    st.session_state.practice_duration = "00:00"
    st.session_state.ai_feedback = ""
    
    st.session_state.view = "practice"
    st.rerun()