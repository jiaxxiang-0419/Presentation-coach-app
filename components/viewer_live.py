import streamlit as st
import datetime 
import zoneinfo
import urllib.parse
from my_utils.db_manager import add_reaction, get_active_live_info, update_live_avatars, get_slide_bytes_by_title
from my_utils.pdf_utils import get_pdf_page_image
import streamlit.components.v1 as components

def inject_firebase_analytics():
    components.html("""
        <script type="module">
          import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-app.js";
          import { getAnalytics } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-analytics.js";

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
def show_waiting_room(room_id, current_token):
    # 💡 部屋のステータスを取得して、「待機中」か「終了済み」かを見極める
    from my_utils.db_manager import get_room_status
    rooms_status = get_room_status()
    room_state = "unknown"
    for r in rooms_status:
        if str(r[0]) == str(room_id) and r[3] == current_token:
            room_state = r[1]
            break

    live_info = get_active_live_info(room_id)
    
    is_valid_live = False
    if live_info:
        correct_token = live_info[3] if len(live_info) > 3 else None
        if current_token == correct_token:
            is_valid_live = True

    if is_valid_live: 
        st.rerun()
    else:
        # 💡 ステータスによって表示する画面を完全に分ける
        if room_state == "booked":
            st.warning("配信はまだ開始されていません。")
            st.info("発表者が配信を開始すると、この画面から自動で切り替わります。このままお待ちください...")
            tz_str = st.session_state.get("timezone", "Asia/Tokyo")
            local_tz = zoneinfo.ZoneInfo(tz_str)
            st.caption(f"通信チェック: {datetime.datetime.now(local_tz).strftime('%H:%M:%S')} (自動更新中)")
            with st.spinner("待機中..."): pass
        else:
            # 💡 配信が終了している（または存在しない）場合
            st.error("このプレゼン配信は終了しました。")
            st.info("ご参加ありがとうございました。画面下部のボタンからホームへお戻りください。")
            
        st.write("---")
        if st.button("ホーム画面に戻る", use_container_width=True, key="wait_home_btn"):
            st.session_state.view = "home"
            st.query_params.clear() 
            st.session_state["current_user"] = None # 💡 ゲスト状態をリセットしてログイン画面に戻す
            st.rerun()
            
@st.fragment(run_every=2)
def viewer_sync_area(room_id, current_token):
    live_info = get_active_live_info(room_id)
    if not live_info:
        st.rerun()
        return
        
    # 💡 同期エリアでもトークンを再確認して不正な描画を防止
    correct_token = live_info[3] if len(live_info) > 3 else None
    if current_token != correct_token:
        st.rerun()
        return
    
    slide_title = live_info[0]
    current_slide = live_info[1]
    st.session_state.viewer_current_slide = current_slide
    st.markdown(f"**現在のスライド:** {current_slide + 1} ページ目")
    
    tz_str = st.session_state.get("timezone", "Asia/Tokyo")
    local_tz = zoneinfo.ZoneInfo(tz_str)
    st.caption(f"通信チェック: {datetime.datetime.now(local_tz).strftime('%H:%M:%S')} (自動更新中)")    
    
    import sqlite3
    pdf_bytes = None
    try:
        conn = sqlite3.connect("presentation_app.db", timeout=20.0)
        cursor = conn.cursor()
        
        s_id = None
        try:
            cursor.execute("CREATE TABLE IF NOT EXISTS live_slide_mapping (room_id TEXT PRIMARY KEY, slide_id TEXT)")
            cursor.execute("SELECT slide_id FROM live_slide_mapping WHERE room_id = ?", (room_id,))
            res = cursor.fetchone()
            if res and res[0]: s_id = res[0]
        except: pass
        
        if not s_id:
            try:
                cursor.execute("PRAGMA table_info(active_lives)")
                cols = [info[1] for info in cursor.fetchall()]
                if "slide_id" in cols:
                    cursor.execute("SELECT slide_id FROM active_lives WHERE room_id = ?", (room_id,))
                    res = cursor.fetchone()
                    if res and res[0]: s_id = res[0]
            except: pass
            
        if s_id:
            try:
                cursor.execute("SELECT file_bytes FROM slide_assets WHERE id = ?", (s_id,))
                row = cursor.fetchone()
                if row and row[0]: pdf_bytes = row[0]
            except: pass
            
        if not pdf_bytes and slide_title:
            try:
                cursor.execute("SELECT file_bytes FROM slide_assets WHERE title = ? ORDER BY id DESC LIMIT 1", (slide_title,))
                row = cursor.fetchone()
                if row and row[0]: pdf_bytes = row[0]
            except: pass
            
        conn.close()
    except: pass
        
    if not pdf_bytes:
        pdf_bytes = get_slide_bytes_by_title(slide_title)

    if pdf_bytes:
        with st.container(border=True):
            img = get_pdf_page_image(pdf_bytes, current_slide)
            if img is not None: 
                st.image(img, use_container_width=True)
            else: 
                st.error("スライド画像の生成に失敗しました。")
    else:
        st.error("発表者のスライドデータが正しく登録されていません。")
        st.info("発表者が緊急レスキューで資料を再設定すると、自動でここに表示されます。")

def render():
    inject_firebase_analytics()

    st.title("ライブ視聴中")
    params = st.query_params
    room_id = params.get("room") or st.session_state.get("room_url") or "Unknown"
    token = params.get("token", "")
    
    if room_id == "Unknown" or not token:
        st.warning("部屋IDまたはトークンが指定されていません。正しい招待リンクからアクセスしてください。")
        st.stop()

    live_info = get_active_live_info(room_id)
    
    # 💡 厳格な入室ブロック処理：本当に配信中であり、トークンが一致しているか
    is_valid_live = False
    if live_info:
        correct_token = live_info[3] if len(live_info) > 3 else None
        if token == correct_token:
            is_valid_live = True

    if not is_valid_live:
        # 配信中でない（待機室、またはすでに終了）場合は待機画面へ
        show_waiting_room(room_id, token)
        # 💡 ここで完全に処理を止めるため、下の音声機能やスライドは絶対に表示されません
        st.stop()
        
    # ==============================================================
    # 🔒 これ以降は、正しいトークンで完全に配信中の場合のみ実行されます
    # ==============================================================
    
    daily_url = get_daily_url_for_room(token)
    HOSTED_HTML_URL = "https://shimmering-panda-a0c284.netlify.app/"
    
    if daily_url:
        safe_daily_url = urllib.parse.quote(daily_url)
        iframe_src = f"{HOSTED_HTML_URL}?url={safe_daily_url}&role=viewer"
        
        st.components.v1.html(f"""
            <iframe 
                src="{iframe_src}" 
                style="width: 100%; height: 120px; border: none; overflow: hidden; margin-bottom: 5px;" 
                allow="microphone; autoplay"
            ></iframe>
        """, height=120)

    col_slide, col_actions = st.columns([6, 4])
    with col_slide:
        viewer_sync_area(room_id, token)
        
    with col_actions:
        c_slide = st.session_state.get("viewer_current_slide", 0) + 1

        st.markdown("### 即時報告")
        c_ok1, c_ok2 = st.columns(2)
        if c_ok1.button("スライド見えない", use_container_width=True):
            add_reaction(room_id, "スライド見えない", c_slide)
            st.toast("発表者に報告しました。")
            
        if c_ok2.button("音声聞こえない", use_container_width=True):
            add_reaction(room_id, "音声聞こえない", c_slide)
            st.toast("発表者に報告しました。")

        c_ng1, c_ng2 = st.columns(2)
        if c_ng1.button("スライド見えている", use_container_width=True):
            add_reaction(room_id, "スライド見えている", c_slide)
            st.toast("発表者に報告しました。")
            
        if c_ng2.button("音声聞こえる", use_container_width=True):
            add_reaction(room_id, "音声聞こえる", c_slide)
            st.toast("発表者に報告しました。")

        st.write("---")
        st.markdown("### 評価")
        c1, c2 = st.columns(2)
        if c1.button("完璧", use_container_width=True):
            add_reaction(room_id, "完璧", c_slide)
            update_live_avatars(room_id, ["🙂", "😊", "👏", "😌", "🙂"]) 
            st.toast("評価を送信しました。")
            
        if c1.button("テンポ注意", use_container_width=True):
            add_reaction(room_id, "テンポ注意", c_slide)
            update_live_avatars(room_id, ["🤨", "🧐", "🥱", "😒", "😐"])
            st.toast("フィードバックを送信しました。")
            
        if c2.button("聞きやすい", use_container_width=True):
            add_reaction(room_id, "聞きやすい", c_slide)
            update_live_avatars(room_id, ["🙂", "😊", "🙂", "😌", "👏"])
            st.toast("評価を送信しました。")
            
        if c2.button("フィラー多い", use_container_width=True):
            add_reaction(room_id, "フィラーが多い", c_slide)
            update_live_avatars(room_id, ["🙄", "🥱", "🤨", "😑", "🥶"])
            st.toast("フィードバックを送信しました。")
            
    st.write("---")
    if st.button("ホーム画面に戻る", use_container_width=True):
        st.session_state.view = "home"
        st.query_params.clear() 
        st.session_state["current_user"] = None # 💡 ゲスト状態をリセットしてログイン画面に戻す
        st.rerun()