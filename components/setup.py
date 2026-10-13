import streamlit as st
from my_utils.db_manager import save_slide_to_db, get_all_slides
from my_utils.actions import handle_delete_slide, handle_start_practice

def render():
    # ==========================================
    # CSS（ボタンを綺麗な青色にするスタイル）
    # ==========================================
    st.markdown("""
        <style>
        button[kind="primary"] {
            background-color: #3b82f6 !important;
            border-color: #3b82f6 !important;
            color: white !important;
        }
        button[kind="primary"]:hover {
            background-color: #2563eb !important;
            border-color: #2563eb !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # ==========================================
    # ナビゲーション（ホームボタンのみ）
    # ==========================================
    if st.button("ホーム", key="setup_nav_home", use_container_width=True): 
        st.session_state.view = "home"
        st.session_state.view_history = []
        st.rerun()

    st.title("プレゼン準備スタジオ")
    st.markdown("練習用資料の登録と管理")
    
    # 💡 修正ポイント①：必ずここで現在のユーザーを取得する！
    current_user = st.session_state.get("current_user", "default_user")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### 新規資料の登録")
        uploaded_file = st.file_uploader(
            "PDFファイルをドロップ", 
            type=["pdf"],
            help="ファイルサイズは200MBまで対応しています。"
        )
        if uploaded_file:
            if st.button("保存", type="primary", use_container_width=True):
                with st.spinner("保存中..."):
                    file_bytes = uploaded_file.read()
                    
                    # 保存するときに「誰のファイルか」を記録
                    save_slide_to_db(current_user, uploaded_file.name, file_bytes)
                    
                    st.success("保存完了！")
                    import time
                    time.sleep(1) # 保存完了の文字を一瞬見せる
                    st.rerun()

    with col2:
        st.markdown("#### 過去の資料から選択")
        
        # 💡 修正ポイント②：ここで「自分の資料だけ」を呼び出す！
        slides = get_all_slides(username=current_user)
        
        if slides:
            slide_options = {slide[1]: slide[0] for slide in slides}
            selected_name = st.selectbox("資料一覧", options=list(slide_options.keys()), label_visibility="collapsed")
            
            with st.expander("資料名の変更"):
                new_name = st.text_input("新しい名前", value=selected_name, key=f"rename_input_{selected_name}")
                if st.button("更新", use_container_width=True):
                    if new_name == selected_name:
                        st.write("名前が変更されていません。")
                    elif not new_name.strip():
                        st.write("名前を空にはできません。")
                    else:
                        from my_utils.db_manager import rename_slide
                        if rename_slide(selected_name, new_name, username=current_user):
                            st.write(f"「{new_name}」に変更しました。")
                            st.rerun() 
                        else:
                            st.write("変更に失敗しました。")
            
            st.write("")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("練習開始", type="primary", use_container_width=True):
                    handle_start_practice(slide_options[selected_name], selected_name)
    
            with col_btn2:
                if st.button("削除", use_container_width=True):
                    from my_utils.db_manager import delete_slide_by_id
                    delete_slide_by_id(slide_options[selected_name], username=current_user)
                    st.warning(f"「{selected_name}」を削除しました。")
                    st.rerun()                
        else:
            st.write("登録されている資料はありません。")