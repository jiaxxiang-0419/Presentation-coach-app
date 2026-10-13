import streamlit as st
import time
import random
import json
import fitz
import secrets
import io
import urllib.parse
from my_utils.pdf_utils import get_pdf_page_image
from my_utils.db_manager import get_reactions_by_slide, end_public_live, update_room_status, release_room, update_live_current_slide, update_live_slide, start_public_live, get_live_avatars
import streamlit.components.v1 as components
import json
from my_utils.db_manager import get_db

# 💡 本番開始時やページ読み込み時に、データベースから原稿（notes_json）を自動取得してセッションに格納する
if "scripts" not in st.session_state or not st.session_state.scripts:
    st.session_state.scripts = {}
    slide_title = st.session_state.get("slide_name") or st.session_state.get("selected_slide_name")
    
    # 💡 現在のユーザーを取得
    current_user = st.session_state.get("current_user", "default_user")
    
    if slide_title:
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                # 💡 修正：原稿を取得するときも、必ず自分の（username）データに絞る
                cursor.execute("SELECT notes_json FROM slide_assets WHERE title = ? AND username = ?", (slide_title, current_user))
                row = cursor.fetchone()
                if row and row[0]:
                    try:
                        # JSON形式の原稿データを取得してセット
                        loaded_notes = json.loads(row[0])
                        if isinstance(loaded_notes, dict):
                            st.session_state.scripts = loaded_notes
                        else:
                            st.session_state.scripts = {0: str(row[0])}
                    except:
                        st.session_state.scripts = {0: str(row[0])}
        except Exception:
            pass

def inject_firebase_analytics():
    # height=0 にして画面上には何も表示させない（裏側で動かす）
    components.html("""
        <script type="module">
          import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-app.js";
          import { getAnalytics } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-analytics.js";

          // ※ここにFirebaseコンソールで取得したご自身のConfigを貼り付けます
          const firebaseConfig = {
            apiKey: "AIzaSyCxoJRRA7WxuRU0ntQd4bo2yTaQ1INWxHk",
            authDomain: "presentation-app-1f735.firebaseapp.com",
            projectId: "presentation-app-1f735",
            storageBucket: "presentation-app-1f735.firebasestorage.app",
            messagingSenderId: "670107575770",
            appId: "1:670107575770:web:15b69dd5a6b26a0a528ce3",
            measurementId: "G-W0B2CKKVB3"
          };

          const app = initializeApp(firebaseConfig);
          const analytics = getAnalytics(app);
        </script>
    """, height=0)

# データベースから専用の音声URLを取り出す関数
def get_daily_url_for_room(room_token):
    import sqlite3
    try:
        conn = sqlite3.connect("presentation_app.db", timeout=20.0)
        cursor = conn.cursor()
        cursor.execute("SELECT daily_url FROM audio_rooms WHERE room_token = ?", (room_token,))
        row = cursor.fetchone()
        conn.close()
        if row: return row[0]
    except:
        pass
    return None

@st.fragment(run_every=3)
def show_live_reactions():
    room_id = st.session_state.get("booked_room") or st.session_state.get("room_url", "Unknown")
    current_slide = st.session_state.get("page_num", 0) + 1
    reactions = get_reactions_by_slide(room_id, current_slide)
    
    slide_ok = 0
    slide_ng = 0
    audio_ok = 0
    audio_ng = 0
    
    if reactions:
        # ※ データベースの検索条件（内部データ）は元のまま変更しません
        for r_type, count in reactions:
            if r_type == "スライド見えている": slide_ok = count
            elif r_type == "スライド見えない": slide_ng = count
            elif r_type == "音声聞こえる": audio_ok = count
            elif r_type == "音声聞こえない": audio_ng = count

    # 💡 解決策1: 文字が「...」と省略されず、綺麗に折り返されるようにするCSS
    st.markdown("""
        <style>
        [data-testid="stMetricLabel"] {
            white-space: normal !important;
            word-break: keep-all !important;
            font-size: 13px !important;
            line-height: 1.4 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("##### 視聴者配信状況")
    c1, c2, c3, c4 = st.columns(4)
    
    # 💡 解決策2: 画面上の表示だけを短く・シャープに変更（より洗練されたUIになります）
    c1.metric("映像 OK", f"{slide_ok}人")
    c2.metric("映像 NG", f"{slide_ng}人")
    c3.metric("音声 OK", f"{audio_ok}人")
    c4.metric("音声 NG", f"{audio_ng}人")

@st.fragment(run_every=3)
def render_panorama_audience():
    room_id = st.session_state.get("booked_room") or st.session_state.get("room_url", "B")
    
    avatars = get_live_avatars(room_id)
    if not avatars:
        strict_emojis = ["🤨", "🧐", "😐", "🥱", "🥶", "😒", "😑", "😠"]
        if "avatar_expressions" not in st.session_state:
            st.session_state.avatar_expressions = [random.choice(strict_emojis) for _ in range(5)]
        if random.random() < 0.3:  
            idx_to_change = random.randint(0, 4)
            st.session_state.avatar_expressions[idx_to_change] = random.choice(strict_emojis)
        avatars = st.session_state.avatar_expressions

    audience_html = """<div style="background: linear-gradient(135deg, #1e293b 0%, #334155 100%); border-radius: 12px; padding: 15px 10px; position: relative; border: 1px solid #475569; box-shadow: 0 4px 12px rgba(0,0,0,0.15); margin-bottom: 5px; text-align: center;">
    <div style="position: absolute; top: 12px; left: 18px; text-align: left;">
        <span style='color: #ef4444; font-weight: bold; font-size: 14px;'>[ LIVE ]</span> 
        <span style='color: #60a5fa; font-weight: bold; font-size: 14px; margin-left: 5px;'>視聴中: <span id='live-viewer-count'>50</span>人</span>
    </div>
    <div style="font-size: 26px; color: #a855f7; opacity: 0.6; letter-spacing: 2px; margin-bottom: 5px; height: 35px; line-height: 1;">
        👥👤👥👤👥👤👥👤👥👤👥
    </div>
    <div style="display: flex; justify-content: center; gap: 20px; align-items: center;">
        <div style="font-size: 26px;" title="役員A">{0}<br><span style="font-size: 11px; color: #94a3b8; font-weight: bold;">役員A</span></div>
        <div style="font-size: 26px;" title="役員B">{1}<br><span style="font-size: 11px; color: #94a3b8; font-weight: bold;">役員B</span></div>
        <div style="font-size: 26px;" title="委員長">{2}<br><span style="font-size: 11px; color: #94a3b8; font-weight: bold;">委員長</span></div>
        <div style="font-size: 26px;" title="同僚">{3}<br><span style="font-size: 11px; color: #94a3b8; font-weight: bold;">同僚</span></div>
        <div style="font-size: 26px;" title="部下">{4}<br><span style="font-size: 11px; color: #94a3b8; font-weight: bold;">監査</span></div>
    </div>
</div>""".format(avatars[0], avatars[1], avatars[2], avatars[3], avatars[4])
    st.markdown(audience_html, unsafe_allow_html=True)

def render():
    # 💡 修正箇所：画面の描画処理が始まる一番最初の場所でFirebaseを読み込みます
    inject_firebase_analytics()

    room_id = st.session_state.get("booked_room") or st.session_state.get("room_url", "B")
            
    if not st.session_state.get("is_live_registered"):
        token = st.session_state.get("room_token") or secrets.token_urlsafe(8)
        st.session_state.live_token = token
        slide_id = st.session_state.get("slide_id") 
        slide_title = st.session_state.get("slide_name", "名称未設定")
        target_min = st.session_state.get("live_target_minutes", 5)
        
        # 💡 完全機密モードのON/OFFを取得
        is_secure_flag = 1 if st.session_state.get("secure_mode", False) else 0
        
        import sqlite3
        try:
            conn = sqlite3.connect("presentation_app.db", timeout=20.0)
            cursor = conn.cursor()
            for table in ["reactions", "slide_reactions", "live_reactions"]:
                try: cursor.execute(f"DELETE FROM {table} WHERE room_id = ?", (room_id,))
                except: pass
                
            cursor.execute("CREATE TABLE IF NOT EXISTS live_slide_mapping (room_id TEXT PRIMARY KEY, slide_id TEXT)")
            if slide_id:
                cursor.execute("INSERT OR REPLACE INTO live_slide_mapping (room_id, slide_id) VALUES (?, ?)", (room_id, str(slide_id)))
                
            conn.commit()
            conn.close()
        except: pass
            
        st.session_state.stat_slide_ok = 0
        st.session_state.stat_slide_ng = 0
        st.session_state.stat_audio_ok = 0
        st.session_state.stat_audio_ng = 0
        
        # 💡 修正：最後に is_secure_flag を渡してデータベースに保存！
        start_public_live(room_id, slide_title, slide_id, token, target_min, is_secure=is_secure_flag)
        st.session_state.is_live_registered = True

    if st.session_state.get("trigger_exit_l", False):
        st.session_state.trigger_exit_l = False
        st.stop()
        
    with st.container():
        # 💡 CSSを使って、データの受け皿となる入力枠を画面から完全に消し去る
        st.markdown("""
            <style>
            div[data-testid="stTextInput"] {
                display: none !important;
            }
            </style>
        """, unsafe_allow_html=True)
        st.text_input("sync", key="js_sync_live_delivery_page", placeholder="sync_l_ph", label_visibility="hidden")

        col_dl_nav1, col_dl_nav2 = st.columns(2)
        with col_dl_nav1:
            st.markdown("<div class='nav-btn-container'>", unsafe_allow_html=True)
            if st.button("待機室に戻る", key="dl_nav_prev", use_container_width=True): 
                from my_utils.db_manager import release_room, end_public_live, cancel_booking
                release_room(room_id)
                end_public_live(room_id)
                
                token = st.session_state.get("room_token") or st.session_state.get("live_token")
                if token:
                    cancel_booking(token)
                    
                st.session_state.is_live_registered = False
                st.session_state.view = "delivery_waiting"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # 💡 右側（col_dl_nav2）に「ホーム」を配置し、ボタン名を変更
        with col_dl_nav2:
            st.markdown("<div class='nav-btn-container'>", unsafe_allow_html=True)
            if st.button("ホーム", key="dl_nav_home", use_container_width=True): 
                from my_utils.db_manager import release_room, end_public_live, cancel_booking
                release_room(room_id)
                end_public_live(room_id)
                
                token = st.session_state.get("room_token") or st.session_state.get("live_token")
                if token:
                    cancel_booking(token)
                    
                st.session_state.is_live_registered = False
                st.session_state.view = "home"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        render_panorama_audience()

        file_name = st.session_state.get("selected_slide_name") or st.session_state.get("slide_name") or ""
        is_pptx = file_name.lower().endswith(".pptx")
        pptx_data = None
        doc_len = 1
        
        if is_pptx:
            try:
                pptx_file = io.BytesIO(st.session_state.selected_pdf_bytes)
                pptx_data = extract_pptx_content(pptx_file)
                doc_len = len(pptx_data)
            except Exception as e:
                st.error(f"PowerPointの読み込みエラー: {e}")
        else:
            try: doc_len = fitz.open(stream=st.session_state.selected_pdf_bytes, filetype="pdf").page_count
            except: pass
        
        st.session_state.page_num = int(max(0, min(st.session_state.page_num, doc_len - 1)))

        p_left, p_right = st.columns([5, 3])
        
        with p_left:
            if is_pptx and pptx_data:
                current_slide_data = pptx_data[st.session_state.page_num]
                with st.container(border=True, height=450):
                    st.markdown("##### スライド内のテキスト")
                    if current_slide_data['text']: st.info(current_slide_data['text'])
                    else: st.caption("（このスライドにテキストはありません）")
            else:
                pdf_bytes = st.session_state.get("selected_pdf_bytes")
                img = get_pdf_page_image(pdf_bytes, st.session_state.get("page_num", 0))
                
                if img is not None:
                    st.image(img, use_container_width=True)
                else:
                    st.error("スライドデータがシステムから見つかりません。")
                    with st.container(border=True):
                        st.markdown("### 緊急レスキュー")
                        from my_utils.db_manager import get_all_slides, get_slide_by_id
                        
                        # 💡 修正：緊急レスキュー時も、必ず現在のユーザーの資料だけを呼び出す
                        current_user = st.session_state.get("current_user", "default_user")
                        slides = get_all_slides(username=current_user)
                        
                        if slides:
                            slide_options = {slide[1]: slide[0] for slide in slides}
                            selected_name = st.selectbox("使用する資料を選択", list(slide_options.keys()), key="emergency_slide_select")

                            if st.button("この資料で復旧する", type="primary", use_container_width=True):
                                slide_id = slide_options[selected_name]
                                # 💡 修正：レスキュー用の資料取得時もユーザーを指定
                                restored_bytes = get_slide_by_id(slide_id, username=current_user)
                                
                                if restored_bytes:
                                    st.session_state.selected_pdf_bytes = restored_bytes
                                    st.session_state.page_num = 0
                                    st.session_state.slide_id = slide_id
                                    st.session_state.slide_name = selected_name 
                                    
                                    # レスキュー時に原稿（notes_json）もデータベースから復旧する
                                    loaded_scripts = {}
                                    try:
                                        import sqlite3
                                        import json
                                        conn = sqlite3.connect("presentation_app.db", timeout=20.0)
                                        cursor = conn.cursor()
                                        # 💡 修正：原稿の復旧時もユーザーを指定
                                        cursor.execute("SELECT notes_json FROM slide_assets WHERE id = ? AND username = ?", (int(slide_id), current_user))
                                        row = cursor.fetchone()
                                        if row and row[0]:
                                            loaded_scripts = json.loads(row[0])
                                    except Exception:
                                        pass
                                    st.session_state.scripts = loaded_scripts 
                                    
                                    # 既存のライブ状態マッピング更新処理
                                    try:
                                        conn = sqlite3.connect("presentation_app.db", timeout=20.0)
                                        cursor = conn.cursor()
                                        cursor.execute("CREATE TABLE IF NOT EXISTS live_slide_mapping (room_id TEXT PRIMARY KEY, slide_id TEXT)")
                                        cursor.execute("INSERT OR REPLACE INTO live_slide_mapping (room_id, slide_id) VALUES (?, ?)", (room_id, str(slide_id)))
                                        conn.commit()
                                        conn.close()
                                    except: pass
                                        
                                    get_pdf_page_image.clear()
                                    st.rerun()
                                else:
                                    st.error("データの引き出しに失敗しました。")
                        else:
                            st.error("データベースに登録されているあなたの資料がありません。")

            st.markdown("<br>", unsafe_allow_html=True)
            c_prev, c_next = st.columns(2)
            is_secure = st.session_state.get("secure_mode", False)
            
            if c_prev.button("前のスライド", use_container_width=True) and st.session_state.page_num > 0: 
                st.session_state.page_num -= 1
                update_live_slide(room_id, st.session_state.page_num)
                st.rerun()
                
            if c_next.button("次のスライド", use_container_width=True) and st.session_state.page_num < doc_len - 1:
                if not is_secure:
                    elapsed = int(time.time() - st.session_state.get("time_last_changed", time.time()))
                    wpm = 300
                    if elapsed > 3:
                        script_text = st.session_state.scripts.get(st.session_state.page_num) or st.session_state.scripts.get(str(st.session_state.page_num)) or ""
                        if not script_text and is_pptx and pptx_data:
                            script_text = pptx_data[st.session_state.page_num]['notes']
                        char_count = len([c for c in script_text if c.strip()])
                        if char_count > 5: wpm = (char_count / elapsed) * 60
                    reaction = "完璧" if 260 <= wpm <= 350 else ("聞きやすい" if wpm < 260 else "テンポ注意")
                    comment = "素晴らしいテンポです。" if reaction == "完璧" else "聞き取りやすいです。"
                    if "live_timeline" not in st.session_state: st.session_state.live_timeline = []
                    st.session_state.live_timeline.append({"slide": st.session_state.page_num + 1, "reaction": reaction, "persona": random.choice(["役員", "同僚", "観客"]), "comment": comment})
                
                st.session_state.page_num += 1 
                st.session_state.time_last_changed = time.time()
                update_live_slide(room_id, st.session_state.page_num)
                st.rerun()
            
        with p_right:
            if "scripts" not in st.session_state: st.session_state.scripts = {}
            
            if "prompter_font_size" not in st.session_state:
                st.session_state.prompter_font_size = 16

            c_f1, c_f2 = st.columns([4, 6])
            with c_f1:
                st.markdown("<div style='color: #64748b; font-size: 14px; margin-top: 8px; font-weight: bold;'>🔍 原稿の文字サイズ:</div>", unsafe_allow_html=True)
            with c_f2:
                font_size = st.slider("文字サイズ", min_value=8, max_value=40, value=st.session_state.prompter_font_size, label_visibility="collapsed")
                st.session_state.prompter_font_size = font_size
                
            script = st.session_state.scripts.get(st.session_state.page_num) or st.session_state.scripts.get(str(st.session_state.page_num))
            if not script and is_pptx and pptx_data: script = pptx_data[st.session_state.page_num]['notes'] or "（原稿未登録）"
            elif not script: script = "（原稿未登録）"
                
            st.markdown(f"<div class='live-prompter' style='background-color: #000000; color: #ffffff; padding: 25px; border-radius: 12px; min-height: 280px; font-size: {font_size}px; font-weight: normal; line-height: 1.6;'>{script}</div>", unsafe_allow_html=True)
            
            daily_url = get_daily_url_for_room(st.session_state.get("room_token"))
            HOSTED_HTML_URL = "https://shimmering-panda-a0c284.netlify.app/"
            
            if daily_url:
                
                safe_daily_url = urllib.parse.quote(daily_url)
                iframe_src = f"{HOSTED_HTML_URL}?url={safe_daily_url}&role=presenter"
                
                st.markdown(f"""
                    <iframe 
                        src="{iframe_src}" 
                        style="width: 100%; height: 120px; border: none; overflow: hidden; margin-bottom: 5px;" 
                        allow="camera; microphone; autoplay; display-capture"
                    ></iframe>
                """, unsafe_allow_html=True)
            
            is_reset_js = "true" if st.session_state.get("reset_js_flag", False) else "false"
            st.session_state.reset_js_flag = False
        
        col_t1, col_t_timer, col_t2 = st.columns([12, 6, 5])
        
        with col_t1:
            show_live_reactions()
        with col_t_timer:
            st.components.v1.html(f"""
                <div id="live-timer-area" style="text-align: center; margin-top: 5px;">
                    <div style="font-size: 13px; color: #64748b; font-weight: bold; margin-bottom: 2px;">[ 発表時間 ]</div>
                    <div id="live-timer" style="font-size: 36px; font-family: monospace; font-weight: bold; color: #10b981; line-height: 1.1;">00:00</div>
                </div>
                <script>
                if({is_reset_js}) {{ 
                    localStorage.setItem('live_time', 0); 
                    localStorage.setItem('live_time_ee', 0); 
                    localStorage.setItem('live_time_ano', 0); 
                    localStorage.setItem('live_time_sono', 0); 
                }}
                let tSecs = parseInt(localStorage.getItem('live_time')||0);
                let targetSecs = {st.session_state.get('live_target_minutes', 5) * 60};
                
                let currentViewers = 50;
                
                function syncLive() {{
                    let input = window.parent.document.querySelector('input[placeholder="sync_l_ph"]');
                    if(input) {{
                        let setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        setter.call(input, JSON.stringify({{time: tSecs, fillers: 0}}));
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }}
                
                window.parent.document.addEventListener('mousedown', function() {{
                    syncLive();
                }}, true);

                window.parent.document.addEventListener('keydown', function(e) {{
                    if(e.key === 'Enter' || e.key === ' ') {{ syncLive(); }}
                }}, true);
                                
                setInterval(()=>{{ 
                    tSecs++; localStorage.setItem('live_time', tSecs);
                    let rem = targetSecs - tSecs;
                    let displayDiv = document.getElementById('live-timer');
                    
                    if(rem >= 0) {{
                        let m = Math.floor(rem/60); let s = rem%60;
                        displayDiv.innerText = (m<10?"0"+m:m) + ":" + (s<10?"0"+s:s);
                        displayDiv.style.color = "#10b981";
                    }} else {{
                        let over = Math.abs(rem); let m = Math.floor(over/60); let s = over%60;
                        displayDiv.innerText = "+ " + (m<10?"0"+m:m) + ":" + (s<10?"0"+s:s);
                        displayDiv.style.color = "#ef4444";
                    }}
                    
                    let change = Math.floor(Math.random() * 7) - 3; 
                    currentViewers += change;
                    if(currentViewers < 5) currentViewers = 5;
                    if(currentViewers > 100) currentViewers = 100;
                    let viewerSpan = window.parent.document.getElementById('live-viewer-count');
                    if(viewerSpan) viewerSpan.innerText = currentViewers;
                    
                }}, 1000);
                </script>
            """, height=90)    
            
        with col_t2:
            st.markdown("<div class='delivery-btn-container' style='margin-top: 15px;'>", unsafe_allow_html=True)
            if st.button("本番を終了する", type="primary", use_container_width=True):
                from my_utils.db_manager import release_room, end_public_live, cancel_booking
                
                val = st.session_state.get("js_sync_live_delivery_page")
                if val:
                    try:
                        import json
                        l_data = json.loads(val)
                        st.session_state.stopwatch_seconds = l_data.get("time", 0)
                        st.session_state.live_final_fillers = l_data.get("fillers", 0)
                    except: pass
                    
                release_room(room_id)
                end_public_live(room_id)
                
                token = st.session_state.get("room_token") or st.session_state.get("live_token")
                if token:
                    cancel_booking(token)
                    
                st.session_state.is_live_registered = False
                
                st.session_state.view = "delivery_result"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 15px 0px;'>", unsafe_allow_html=True)
        token = st.session_state.get("live_token", "")
        current_room = room_id if room_id and room_id != "Unknown" else st.session_state.get("booked_room", "A")
        base_url = "https://opulent-rotary-phone-5vqvvgq5qxjx37rvr-8501.app.github.dev"
        invite_link = f"{base_url}/?room={current_room}&token={token}"        
        st.info("[ 視聴者用の招待リンク ] このURLを知っている人のみが参加できます")
        st.code(invite_link, language="text")
        if is_secure: st.warning("[ 完全機密モードが有効です ] ホーム画面の一覧には表示されず、URLを知っている人のみ参加できます。")