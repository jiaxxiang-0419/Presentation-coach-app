import streamlit as st
import random
import time
import datetime
import zoneinfo
from my_utils.db_manager import init_db, get_room_by_token, register_user, verify_user

# ==========================================
# 0. ページ設定 & セッション初期化 (一番最初に実行する)
# ==========================================
st.set_page_config(page_title="Brave Speaker", layout="wide")

# データベース初期化
init_db()

def init_session_state():
    defaults = {
        "view": "home",
        "secure_mode": False,
        "page_num": 0,
        "stopwatch_active": False,
        "stopwatch_seconds": 0,
        "scripts": {},
        "selected_pdf_bytes": None,
        "slide_name": "新規プレゼン資料",
        "opt_filler": True,
        "opt_speed": True,
        "current_advice": random.choice(["結論から話しましょう", "1秒の沈黙を作りましょう", "ジェスチャーを大きく"]),
        "time_last_changed": 0.0,
        "last_wpm_value": None,
        "last_wpm_verdict": "",
        "last_evaluated_slide": 0,
        "reset_js_flag": False,
        "trigger_exit_p": False,
        "trigger_exit_l": False,
        "live_target_minutes": 5,
        "live_timeline": [],
        "live_final_fillers": 0,
        "room_url": "",
        "booked_time": "",
        "booked_room": "",
        "room_token": "",
        "current_user": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ルーティングよりも先に必ずセッションを初期化する
init_session_state()


# ==========================================
# 0.4 視聴者（ゲスト）の直接アクセス処理
# ==========================================
query_params = st.query_params

# ?room=XXX がある（かつ room_token は無い）場合は、視聴者（ゲスト）として無条件で通す！
if "room" in query_params and "room_token" not in query_params:
    st.session_state["current_user"] = "Guest_Viewer"
    from components import viewer_live
    viewer_live.render()
    st.stop()


# ==========================================
# 0.5 ログイン・認証チェック（未ログインならここでストップ）
# ==========================================
if st.session_state.get("current_user") is None or st.session_state.get("current_user") == "Guest_Viewer":
    st.markdown("""
        <div style="max-width: 500px; margin: 40px auto; text-align: center;">
            <h1 style="font-size: 2.5rem; font-weight: 800; color: #0f172a;">
                <span style="color: #3b82f6;">B</span>rave <span style="color: #ef4444;">S</span>peaker
            </h1>
            <p style="color: #64748b; font-size: 1.1rem; margin-bottom: 30px;">最高のプレゼンを、ここから。</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_register = st.tabs(["🔑 ログイン", "✨ 新規アカウント作成"])
        
        with tab_login:
            st.markdown("<br>", unsafe_allow_html=True)
            login_user = st.text_input("ユーザー名", key="login_username")
            login_pass = st.text_input("パスワード", type="password", key="login_password")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("ログインする", use_container_width=True, type="primary"):
                if verify_user(login_user, login_pass):
                    st.session_state["current_user"] = login_user.strip()
                    st.success(f"ようこそ、{login_user}さん！")
                    st.rerun()
                else:
                    st.error("ユーザー名またはパスワードが間違っています。")
                    
        with tab_register:
            st.markdown("<br>", unsafe_allow_html=True)
            reg_user = st.text_input("新しいユーザー名", key="reg_username")
            reg_pass = st.text_input("パスワード（半角英数）", type="password", key="reg_password")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("アカウントを作成して開始", use_container_width=True, type="primary"):
                if reg_user and reg_pass:
                    if register_user(reg_user, reg_pass):
                        st.session_state["current_user"] = reg_user.strip()
                        st.success("アカウントが作成され、ログインしました！")
                        st.rerun()
                    else:
                        st.error("そのユーザー名はすでに使われています。別の名前をお試しください。")
                else:
                    st.warning("ユーザー名とパスワードを入力してください。")
                    
    st.stop() # ログインが完了するまで、これより先のアプリ画面を表示させないためのガード


# ==========================================
# 1. 発表者用のアクセス割り込み処理 (?room_token=XXX)
# ==========================================
room_token = query_params.get("room_token")
if room_token:
    def check_room_access(booked_time_str, booked_date_str):
        if not booked_time_str or not booked_date_str:
            return "invalid"
        jst = zoneinfo.ZoneInfo("Asia/Tokyo")
        now = datetime.datetime.now(jst)
        
        try:
            target_dt = datetime.datetime.strptime(f"{booked_date_str} {booked_time_str}", "%Y-%m-%d %H:%M")
            start_time = target_dt.replace(tzinfo=jst)
        except ValueError:
            return "invalid"
            
        start_time_with_buffer = start_time - datetime.timedelta(minutes=5)
        end_time = start_time + datetime.timedelta(minutes=20)
        
        if start_time_with_buffer <= now <= end_time:
            return True
        elif now < start_time_with_buffer:
            return "yet"
        else:
            return "expired"

    room_data = get_room_by_token(room_token)
    
    if not room_data:
        st.error("❌ 無効なURL、または存在しない専用ルームです。")
    else:
        room_id, status, booked_time, _, booked_date = room_data
        access_status = check_room_access(booked_time, booked_date)
        
        if access_status == True:
            st.title(f"🎙️ 本番準備室（ルーム {room_id}）")
            st.success(f"予約時間内です。入室が許可されています。（予約枠: {booked_time}）")
            
            st.session_state["booked_room"] = room_id
            st.session_state["booked_time"] = booked_time
            
            from components import delivery_live
            delivery_live.render()
            
        elif access_status == "yet":
            st.warning(f"⏳ まだ予約時間になっていません。\n\n**入室可能時間**: {booked_time} の5分前から入室できます。")
        else:
            st.error("⏰ この予約の時間はすでに終了しているか、無効なURLです。")
            
    st.stop()


# ==========================================
# 2. テーマ別動的CSS（デザイン設定）
# ==========================================
if st.session_state.view in ["home", "setup", "practice", "dashboard"]:
    accent_color = "#3b82f6" 
    btn_color = "#3b82f6"
else:
    accent_color = "#ef4444" 
    btn_color = "#ef4444"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #f8fafc !important; color: #0f172a !important; }}
    
    /* 1. 同期用テキストボックスを非表示 */
    div[data-testid="stTextInput"]:has(input[placeholder="sync_p_ph"]),
    div[data-testid="stTextInput"]:has(input[placeholder="sync_l_ph"]) {{
        display: none !important;
    }}
    
    /* 2. ボタンの余白を消す */
    div[data-testid="stButton"] {{
        margin: 0 !important;
        padding: 0 !important;
    }}
    
    /* 3. ボタンの高さを揃えて段差を解消 */
    div.stButton > button {{
        height: 50px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 !important;
    }}
    
    /* 4. カラム内の要素を底辺で揃える */
    div[data-testid="column"] {{
        display: flex !important;
        align-items: flex-end !important;
    }}
    </style>
""", unsafe_allow_html=True)

# 隠したい入力欄
sync_p = st.text_input("sync_p", key="js_sync_practice", placeholder="sync_p_ph", label_visibility="collapsed")
sync_l = st.text_input("sync_l", key="js_sync_live", placeholder="sync_l_ph", label_visibility="collapsed")


# ==========================================
# 3. ルーティング（各画面への振り分け）
# ==========================================
@st.fragment
def show_page(view_name):
    query_params = st.query_params
    if "room" in query_params and "room_token" not in query_params:
        from components import viewer_live
        viewer_live.render()
        return 
    
    if view_name == "home":
        from components import home; home.render()
    elif view_name == "setup":
        from components import setup; setup.render()
    elif view_name == "practice":
        from components import practice; practice.render()
    elif view_name == "dashboard":
        from components import dashboard; dashboard.render()
    elif view_name == "delivery_booking":
        from components import delivery_booking; delivery_booking.render()
    elif view_name == "delivery_setup":
        from components import delivery_setup; delivery_setup.render()
    elif view_name == "delivery_waiting":
        from components import delivery_waiting; delivery_waiting.render()
    elif view_name == "delivery_live":
        from components import delivery_live; delivery_live.render()
    elif st.session_state.get("view") == "recommended_books":
        from components import recommended_books
        recommended_books.render()
    elif view_name == "delivery_result":
        from components import delivery_result; delivery_result.render()
    elif view_name == "contact_support":
        from components import contact_support; contact_support.render()
    elif view_name == "creator_cheer":
        from components import creator_cheer; creator_cheer.render()

show_page(st.session_state.view)