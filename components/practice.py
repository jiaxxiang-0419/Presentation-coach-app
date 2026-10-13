import streamlit as st
import fitz
import random
import json
import re
import sqlite3
from datetime import datetime
import zoneinfo
from streamlit_mic_recorder import mic_recorder
from components.practice_utils import get_pdf_page_image, call_gemini_api
import io

def render():
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
    # セッションステートの初期化
    # ==========================================
    if "view_history" not in st.session_state:
        st.session_state.view_history = []
    if "show_script" not in st.session_state: 
        st.session_state.show_script = True
    if "page_num" not in st.session_state: 
        st.session_state.page_num = 0
    if "filler_count" not in st.session_state:
        st.session_state.filler_count = 0
    if "ai_feedback" not in st.session_state:
        st.session_state.ai_feedback = ""
    if "practice_duration" not in st.session_state:
        st.session_state.practice_duration = "00:00"
        
    if "practice_tip" not in st.session_state:
        tips = [
            "重要なキーワードの直前で1〜2秒の沈黙を作り、聞き手の注目を引きつけましょう。",
            "第一声は1トーン高い声で、会場の奥へ向けて発声しましょう。",
            "自己紹介の際は、一瞬の笑顔を添えてみてください。",
            "「〜だと思います」を避け、「〜です」と言い切ることで説得力を生み出します。",
            "「えー」「あのー」などの言葉のひげを減らすには、文を短く区切ることが効果的です。"
        ] 
        st.session_state.practice_tip = random.choice(tips)

    # ==========================================
    # 1. ナビゲーション（ホーム ＆ 戻る）
    # ==========================================
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("ホーム", key="practice_nav_home", use_container_width=True): 
            st.session_state.view = "home"
            st.session_state.view_history.clear()
            st.rerun()
    with col_nav2:
        if st.button("戻る", key="practice_nav_prev", use_container_width=True): 
            st.session_state.view = "setup"
            st.rerun()    
            
    # ==========================================
    # メイン画面分割（左：スライド、右：原稿）
    # ==========================================
    col_main1, col_main2 = st.columns([2, 1])

    with col_main1:
        total_pages = 0
        file_type = None
        doc = None
        
        if "selected_pdf_bytes" in st.session_state:
            file_type = "pdf"
            try:
                doc = fitz.open(stream=st.session_state.selected_pdf_bytes, filetype="pdf")
                total_pages = len(doc)
            except Exception:
                total_pages = 10 

        if total_pages > 0:
            st.session_state.page_num = int(max(0, min(st.session_state.page_num, total_pages - 1)))

            if total_pages > 1:
                c_label, c_slider, c_input, c_btn = st.columns([2.5, 4, 1.5, 1.5])
                with c_label:
                    st.markdown("<div style='margin-top: 8px;'><b>ページ移動：</b></div>", unsafe_allow_html=True)
                with c_slider:
                    slider_val = st.slider("スライダー", 1, total_pages, st.session_state.page_num + 1, label_visibility="collapsed")
                with c_input:
                    jump_input = st.number_input("ページ番号", 1, total_pages, st.session_state.page_num + 1, label_visibility="collapsed")
                with c_btn:
                    if st.button("移動", use_container_width=True):
                        st.session_state.page_num = jump_input - 1
                        st.rerun()

                if slider_val - 1 != st.session_state.page_num:
                    st.session_state.page_num = slider_val - 1
                    st.rerun()
            else:
                st.write("1ページの資料です。")

            nav1, nav2, nav3, nav4 = st.columns(4)
            if nav1.button("最初", use_container_width=True): st.session_state.page_num = 0; st.rerun()
            if nav2.button("前へ", use_container_width=True): st.session_state.page_num = max(0, st.session_state.page_num - 1); st.rerun()
            if nav3.button("次へ", use_container_width=True): st.session_state.page_num = min(total_pages - 1, st.session_state.page_num + 1); st.rerun()
            if nav4.button("最後", use_container_width=True): st.session_state.page_num = total_pages - 1; st.rerun()

            if file_type == "pdf":
                img = get_pdf_page_image(st.session_state.selected_pdf_bytes, st.session_state.page_num)
                st.image(img, use_container_width=True)
        else:
            st.write("スライドが読み込まれていません。")
            
    # --- 右側（原稿） ---
    with col_main2:
        # 💡 現在のユーザーを取得
        current_user = st.session_state.get("current_user", "default_user")
        
        if st.session_state.show_script:
            slide_title = st.session_state.get("selected_slide_name") or st.session_state.get("slide_name") or st.session_state.get("selected_slide") or st.session_state.get("title")
            current_page = str(st.session_state.get("page_num", 0))
            
            notes_dict = {}
            try:
                from my_utils.db_manager import get_db
                cursor = get_db().cursor()
                # 💡 原稿の読み込み時も自分のデータに絞る
                cursor.execute("SELECT notes_json FROM slide_assets WHERE title = ? AND username = ?", (slide_title, current_user))
                row = cursor.fetchone()
                if row and row[0]:
                    try:
                        notes_dict = json.loads(row[0])
                    except json.JSONDecodeError:
                        notes_dict = {"0": row[0]}
            except Exception:
                pass

            saved_script = notes_dict.get(current_page, "原稿を入力...")

            script = st.text_area(f"発表原稿 ({int(current_page) + 1}枚目):", value=saved_script, height=200, key=f"script_area_{current_page}")
            
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                if st.button("ページを保存", use_container_width=True):
                    try:
                        from my_utils.db_manager import update_slide_notes_by_title
                        if slide_title:
                            notes_dict[current_page] = script
                            updated_notes_json = json.dumps(notes_dict, ensure_ascii=False)
                            # 💡 原稿の保存にも username を使うように関数に渡す
                            update_slide_notes_by_title(slide_title, updated_notes_json, username=current_user)
                            st.write(f"{int(current_page) + 1}枚目の原稿を保存しました。")
                        else:
                            st.write("スライドが選択されていません。")
                    except Exception as e:
                        st.write(f"保存エラー: {e}")
            with col_s2:
                if st.button("原稿を隠す", use_container_width=True):
                    st.session_state.show_script = False
                    st.rerun()
            
            st.markdown("---")
            st.markdown("#### AI原稿アシスト")
            st.caption("入力した文章をスピーチ用に最適化します。")
            
            if st.button("AIに添削を依頼", use_container_width=True):
                with st.spinner("分析中..."):
                    coach_instruction = "あなたはプロのスピーチコーチです。入力された原稿を、声に出して聞き手の心に届くスピーチ台本に最適化してください。出力は「### 1. 改善後の台本」から始めてください。"
                    optimized_text = call_gemini_api(f"原稿: {script}", coach_instruction)
                    st.write("分析完了")
                    st.markdown(optimized_text)
        else:
            st.write("暗記モード中（原稿非表示）")
            if st.button("原稿を表示", use_container_width=True):
                st.session_state.show_script = True
                st.rerun()

    # ==========================================
    # 練習タイマー ＆ AI音声分析パネル
    # ==========================================
    st.markdown("---")
    st.markdown("### スピーチタイマー ＆ AI分析")
    st.caption("録音してAIに分析させることで、無意識の「えー」「あのー」を可視化し、説得力のある話し方を身につけられます。")

    if "timer_running" not in st.session_state: st.session_state.timer_running = False
    if "timer_start_time" not in st.session_state: st.session_state.timer_start_time = None
    if "timer_elapsed" not in st.session_state: st.session_state.timer_elapsed = 0

    import time
    col_t1, col_t2 = st.columns([1, 1])
    
    with col_t1:
        with st.container(border=True):
            st.markdown("<div style='text-align: center; color: #64748b; font-weight: bold; font-size: 14px; margin-bottom: 5px;'>⏱️ 練習ストップウォッチ</div>", unsafe_allow_html=True)
            timer_placeholder = st.empty()
            
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if not st.session_state.timer_running:
                    if st.button("スタート", use_container_width=True, key="start_btn"):
                        st.session_state.timer_running = True
                        st.session_state.timer_start_time = datetime.now().timestamp() - st.session_state.timer_elapsed
                        st.rerun()
                else:
                    if st.button("一時停止", use_container_width=True, key="pause_btn"):
                        st.session_state.timer_running = False
                        st.rerun()
            with c_btn2:
                if st.button(" リセット", use_container_width=True, key="reset_btn"):
                    st.session_state.timer_running = False
                    st.session_state.timer_elapsed = 0
                    st.rerun()
    with col_t2:
        with st.container(border=True):
            st.markdown("<div style='text-align: center; color: #64748b; font-weight: bold; font-size: 14px; margin-bottom: 5px;'>🧠 AIスピーチ解析（録音）</div>", unsafe_allow_html=True)
            
            audio_data = mic_recorder(
                start_prompt="録音してAI分析を開始",
                stop_prompt="ストップ＆分析結果を見る",
                key="practice_recorder",
                use_container_width=True
            )
            
            if not st.session_state.ai_feedback:
                st.caption("💡 **なぜ録音するの？**\n「えー」「あのー」を減らすだけで、スピーチが洗練され、聞き手に「自信がある」という強い印象を与えられます。")

    # ==========================================
    # 分析レポート
    # ==========================================
    if st.session_state.ai_feedback:
        st.write("解析完了")
        with st.container(border=True):
            st.markdown("#### スピーチ分析レポート")
            res_col1, res_col2 = st.columns(2)
            res_col1.metric("言葉のひげ（フィラー）合計", f"{st.session_state.filler_count} 回")
            res_col2.metric("音声の長さ", st.session_state.practice_duration)
            
            with st.expander("詳しいアドバイスと内訳"):
                st.markdown(st.session_state.ai_feedback)

    st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================
    # アクションボタン
    # ==========================================
    nav_b1, nav_b2 = st.columns(2)
    with nav_b1:
        if st.button("次の練習へ（データクリア）", use_container_width=True):
            st.session_state.filler_count = 0
            st.session_state.practice_duration = "00:00"
            st.session_state.ai_feedback = ""
            st.session_state.page_num = 0 
            st.session_state.timer_running = False
            st.session_state.timer_elapsed = 0
            st.rerun()
    with nav_b2:
        if st.button("ホームへ戻って記録を保存", type="primary", use_container_width=True):
            total_seconds = int(st.session_state.get("timer_elapsed", 0))
            
            tz_str = st.session_state.get("timezone", "Asia/Tokyo")
            local_tz = zoneinfo.ZoneInfo(tz_str)
            today_str = datetime.now(local_tz).strftime("%Y-%m-%d %H:%M")
            
            fillers = st.session_state.get("filler_count", 0)
            slide_title = st.session_state.get("selected_slide_name") or "練習セッション"
            current_user = st.session_state.get("current_user", "default_user")
            
            try:
                with sqlite3.connect("presentation_app.db", timeout=20.0) as conn:
                    cursor = conn.cursor()
                    # 💡 修正：保存時に必ず自分の username を含める
                    cursor.execute("""
                        INSERT INTO practice_history (username, date, slide_name, duration, fillers, recorded, is_live)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (current_user, today_str, slide_title, total_seconds, fillers, 1, 0))
                    conn.commit()
            except: pass

            st.session_state.view = "home"
            if "practice_tip" in st.session_state: del st.session_state.practice_tip
            st.session_state.timer_running = False
            st.session_state.timer_elapsed = 0
            st.rerun()

    # ==========================================
    # 裏側処理：音声解析の実行
    # ==========================================
    if audio_data is not None:
        if "last_audio_id" not in st.session_state or st.session_state.last_audio_id != audio_data['id']:
            st.session_state.last_audio_id = audio_data['id']
            
            st.write("音声解析中...")
            with st.spinner("AI分析中..."):
                prompt = """
                この音声データから、不要な言葉（フィラー）の回数を数え、音声の長さを測ってください。
                必ず以下のJSON形式のみで出力してください。Markdown記号(```jsonなど)や解説は不要です。
                {
                  "録音時間_秒": 0,
                  "えー": 0,
                  "あのー": 0,
                  "そのー": 0,
                  "えーっと": 0,
                  "その他": 0
                }
                """
                res = call_gemini_api(prompt, audio_bytes=audio_data['bytes'])
                
                try:
                    match = re.search(r'\{.*\}', res, re.DOTALL)
                    if match:
                        filler_data = json.loads(match.group())
                    else:
                        raise ValueError("JSONデータが見つかりませんでした")
                    
                    duration_sec = filler_data.pop("録音時間_秒", 0)
                    minutes = duration_sec // 60
                    seconds = duration_sec % 60
                    st.session_state.practice_duration = f"{minutes:02}:{seconds:02}"
                    
                    total_fillers = sum(filler_data.values())
                    st.session_state.filler_count = total_fillers
                    
                    breakdown_text = "#### フィラーの詳細内訳\n"
                    if total_fillers == 0:
                        breakdown_text += "フィラーは検出されませんでした。"
                    else:
                        for word, count in filler_data.items():
                            if count > 0:
                                breakdown_text += f"- {word}: {count} 回\n"
                            
                    st.session_state.ai_feedback = breakdown_text
                except Exception as e:
                    st.session_state.ai_feedback = f"解析に失敗しました。\n\n{res}"
            
            st.rerun()

    # ==========================================
    # 裏側処理：タイマー描画更新
    # ==========================================
    if st.session_state.timer_running:
        st.session_state.timer_elapsed = datetime.now().timestamp() - st.session_state.timer_start_time
        m = int(st.session_state.timer_elapsed // 60)
        s = int(st.session_state.timer_elapsed % 60)
        
        timer_placeholder.markdown(
            f"<div style='text-align: center; font-size: 38px; font-family: monospace; font-weight: bold; color: #3b82f6;'>{m:02d}:{s:02d}</div>", 
            unsafe_allow_html=True
        )
        time.sleep(1)
        st.rerun()
    else:
        m = int(st.session_state.timer_elapsed // 60)
        s = int(st.session_state.timer_elapsed % 60)
        timer_placeholder.markdown(
            f"<div style='text-align: center; font-size: 38px; font-family: monospace; font-weight: bold; color: #94a3b8;'>{m:02d}:{s:02d}</div>", 
            unsafe_allow_html=True
        )
        