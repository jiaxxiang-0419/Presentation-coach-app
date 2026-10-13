import streamlit as st
import datetime
import zoneinfo
from my_utils.db_manager import (
    get_all_active_lives, cleanup_zombie_rooms, get_room_status, 
    cancel_booking, get_slide_bytes_by_title, get_all_slides
)

@st.fragment(run_every=10)
def render_schedule_area():
    rooms_status = get_room_status()
    current_user = st.session_state.get("current_user", "default_user")
    
    # 💡 追加：自分が登録している資料のタイトル一覧を取得
    my_slides = get_all_slides(username=current_user)
    my_slide_titles = [slide[1] for slide in my_slides] if my_slides else []

    booked_rooms = [r for r in rooms_status if r[1] == 'booked']
    
    if booked_rooms:
        tz_str = st.session_state.get("timezone", "Asia/Tokyo")
        local_tz = zoneinfo.ZoneInfo(tz_str)
        now = datetime.datetime.now(local_tz)
        current_date_str = str(now.date())

        expired_tokens = []
        my_bookings_count = 0
        
        for r_info in booked_rooms:
            room_id = r_info[0]
            booked_time = r_info[2]
            room_token = r_info[3]
            slide_title = r_info[4] if len(r_info) > 4 and r_info[4] else "名称未設定"
            booked_date = r_info[5] if len(r_info) > 5 and r_info[5] else current_date_str
            
            # 💡 追加：自分の資料名に含まれないもの（他人の予約）は表示せずにスキップ！
            if slide_title not in my_slide_titles and slide_title != "名称未設定":
                continue
                
            my_bookings_count += 1
            
            is_time_ready = False
            remain_mins_text = ""
            
            try:
                b_dt = datetime.datetime.strptime(f"{booked_date} {booked_time}", "%Y-%m-%d %H:%M").replace(tzinfo=local_tz)
                start_allowed_time = b_dt - datetime.timedelta(minutes=10)
                end_allowed_time = b_dt + datetime.timedelta(minutes=30)
                
                if now > end_allowed_time:
                    expired_tokens.append(room_token)
                    continue 
                
                if now >= start_allowed_time:
                    is_time_ready = True
                else:
                    is_time_ready = False
                    remain = int((start_allowed_time - now).total_seconds() / 60) + 1
                    remain_mins_text = f"開始まで {remain} 分"
            except Exception as e:
                is_time_ready = False

            with st.container(border=True):
                col_info, col_action1, col_action2, col_action3 = st.columns([2.5, 1, 1, 1])
                with col_info:
                    st.markdown(f"**Room {room_id} ｜ {slide_title}**")
                    st.caption(f"{booked_date} {booked_time}")
                
                with col_action1:
                    if is_time_ready:
                        if st.button("準備", key=f"start_live_{room_token}", type="primary", use_container_width=True):
                            current_user = st.session_state.get("current_user", "default_user")
                            slide_bytes = get_slide_bytes_by_title(slide_title, username=current_user)
                            
                            if slide_bytes:
                                st.session_state.selected_pdf_bytes = slide_bytes
                                
                            st.session_state.page_num = 0 
                            st.session_state.booked_room = room_id
                            st.session_state.booked_time = booked_time
                            st.session_state.booked_date = booked_date
                            st.session_state.room_token = room_token
                            st.session_state.booking_mode = "reserve" 
                            st.session_state.slide_name = slide_title
                            
                            if "view_history" not in st.session_state:
                                st.session_state.view_history = []
                            st.session_state.view_history.append("home")
                            
                            st.session_state.view = "delivery_waiting"
                            st.rerun()
                    else:
                        st.button(f"{remain_mins_text}", key=f"wait_live_{room_token}", disabled=True, use_container_width=True)
                
                with col_action2:
                    if st.button("編集", key=f"edit_book_{room_token}", use_container_width=True):
                        st.session_state.edit_room_id = room_id 
                        st.session_state.edit_room_token = room_token
                        st.session_state.booked_time = booked_time
                        st.session_state.booked_date = booked_date
                        
                        title_val = slide_title if slide_title != "名称未設定" else ""
                        st.session_state.edit_slide_title = title_val
                        st.session_state.setup_custom_title = title_val 
                        
                        st.session_state.booking_mode = "reserve"
                        st.session_state.view = "delivery_setup"
                        st.rerun()

                with col_action3:
                    if st.button("取消", key=f"cancel_book_{room_token}", use_container_width=True):
                        cancel_booking(room_token)
                        st.rerun()

        # 追加：他人の予約を弾いた結果、自分の予約が0件だった場合の表示
        if my_bookings_count == 0:
            st.write("あなたの予約はありません。")

        if expired_tokens:
            for r_token in expired_tokens:
                cancel_booking(r_token)
            st.rerun()

    else:
        st.write("予約はありません。")


@st.fragment(run_every=10)
def render_active_lives_area():
    st.markdown("### 配信中のプレゼン")
    
    # 💡 get_all_active_lives は「完全機密モード」がOFFの配信だけを取ってくるので、
    # そのまま表示させれば「公開配信」として視聴者が参加できるようになります。
    active_lives = get_all_active_lives()
    
    if active_lives:
        tz_str = st.session_state.get("timezone", "Asia/Tokyo")
        local_tz = zoneinfo.ZoneInfo(tz_str)
        
        for room_id, slide_title, started_at, target_minutes, token in active_lives:
            display_time = started_at
            try:
                dt = datetime.datetime.strptime(str(started_at).split(".")[0], "%Y-%m-%d %H:%M:%S")
                dt_utc = dt.replace(tzinfo=datetime.timezone.utc)
                local_dt = dt_utc.astimezone(local_tz)
                display_time = local_dt.strftime("%H:%M")
            except Exception:
                display_time = str(started_at)[:16]

            with st.container(border=True):
                l_col, r_col = st.columns([3, 1])
                with l_col:
                    st.markdown(f"**Room {room_id} ｜ {slide_title}**")
                    st.caption(f"開始: {display_time} ｜ 予定発表時間: {target_minutes or 5} 分")
                    
                with r_col:
                    st.markdown("<br>", unsafe_allow_html=True)
                    # 💡 視聴者がここから参加する！
                    if st.button("参加", key=f"join_{room_id}", type="primary", use_container_width=True): 
                        st.query_params["room"] = room_id
                        if token:
                            st.query_params["token"] = token
                        st.rerun()
                        
    else:
        st.write("配信中のセッションはありません。")

def render():
    cleanup_zombie_rooms(minutes=30)
    
    col_logo, col_title, col_user = st.columns([0.6, 5, 2])
    with col_logo:
        try:
            st.image("logo_vol1.jpg", width=85) 
        except:
            st.write("🎙️")
    with col_title:
        st.markdown("""
            <div style="display: flex; align-items: flex-end; height: 100%; padding-bottom: 5px;">
                <h1 style="margin: 0; line-height: 1; font-size: 2.8rem; font-weight: 800; color: #0f172a;">
                    <span style="color: #3b82f6;">B</span>rave <span style="color: #ef4444;">S</span>peaker
                </h1>
            </div>
        """, unsafe_allow_html=True)
        
    with col_user:
        current_user = st.session_state.get("current_user", "")
        st.markdown(f"<div style='text-align: right; margin-top: 10px; font-weight: bold; color: #64748b;'>👤 {current_user} さん</div>", unsafe_allow_html=True)
        if st.button("ログアウト", use_container_width=True):
            st.session_state["current_user"] = None
            st.rerun()
    
    st.markdown("<p style='color: #64748b; margin-top: 5px; margin-bottom: 25px; font-size: 1.1rem;'>最高のプレゼンを、ここから。</p>", unsafe_allow_html=True)
    st.markdown("### スケジュール")
    render_schedule_area()

    render_active_lives_area()
    st.write("---")
    st.markdown("### シミュレーション")
    
    st.markdown("""
        <style>
        [data-testid="stVerticalBlock"] > div:has(div.stButton) {
            height: 100%;
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    
    with col1:
        with st.container(border=True):
            st.markdown("#### 個人練習")
            
            if st.button("練習設定", use_container_width=True): 
                if "view_history" not in st.session_state:
                    st.session_state.view_history = []
                st.session_state.view_history.append("home")
                
                st.session_state.view = "setup"
                st.rerun()
            
            import streamlit.components.v1 as components
            components.html("""
                <script>
                setTimeout(() => {
                    const buttons = window.parent.document.querySelectorAll('button');
                    buttons.forEach(btn => {
                        if (btn.innerText.trim() === '練習設定') {
                            btn.style.backgroundColor = '#3b82f6';
                            btn.style.color = 'white';
                            btn.style.borderColor = '#3b82f6';
                            btn.onmouseover = function() { this.style.backgroundColor = '#2563eb'; this.style.borderColor = '#2563eb'; }
                            btn.onmouseout = function() { this.style.backgroundColor = '#3b82f6'; this.style.borderColor = '#3b82f6'; }
                        }
                    });
                }, 100);
                </script>
            """, height=0, width=0)

    with col2:
        with st.container(border=True):
            st.markdown("#### 本番配信")
            
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("予約", use_container_width=True):
                    st.session_state.pop("edit_room_id", None)
                    st.session_state.pop("edit_room_token", None)
                    st.session_state.pop("edit_slide_title", None)
                    st.session_state.pop("setup_custom_title", None) 
                    st.session_state.pop("booked_date", None)
                    st.session_state.pop("booked_time", None)
                    st.session_state.booking_mode = "reserve"
                    st.session_state.view = "delivery_setup"
                    st.rerun()
            with c_btn2:
                if st.button("即時開始", type="primary", use_container_width=True):
                    st.session_state.pop("edit_room_id", None)
                    st.session_state.pop("edit_room_token", None)
                    st.session_state.pop("edit_slide_title", None)
                    st.session_state.pop("setup_custom_title", None) 
                    st.session_state.pop("booked_date", None)
                    st.session_state.pop("booked_time", None)
                    st.session_state.booking_mode = "immediate"
                    st.session_state.view = "delivery_setup"
                    st.rerun()
                    
    st.write("---")
   
    st.markdown("### コンテンツ・サポート")
    f_cols = st.columns(4)
    with f_cols[0]:
        if st.button("パワポカラオケ", use_container_width=True): 
            pass # 機能準備中
    with f_cols[1]:
        if st.button("作成者応援", use_container_width=True): 
            st.session_state.view = "creator_cheer"
            st.rerun()
    with f_cols[2]:
        if st.button("サポート", use_container_width=True): 
            st.session_state.view = "contact_support"
            st.rerun()
    with f_cols[3]:
        if st.button("推奨図書", use_container_width=True): 
            st.session_state.view = "recommended_books"
            st.rerun()
        
    if st.button("履歴", use_container_width=True): 
        st.session_state.view = "dashboard"
        st.rerun()

    st.markdown("### 環境設定")
    c1, c2 = st.columns(2)
    is_secure = c1.checkbox("完全機密モード", value=st.session_state.get("secure_mode", False))
    st.session_state.secure_mode = is_secure
    
    tz_options = {"Asia/Tokyo": "Asia/Tokyo", "Asia/Shanghai": "Asia/Shanghai", "UTC": "UTC", "America/New_York": "America/New_York"}
    current_tz = st.session_state.get("timezone", "Asia/Tokyo")
    default_idx = list(tz_options.values()).index(current_tz) if current_tz in tz_options.values() else 0
    selected_tz_label = c2.selectbox("タイムゾーン", options=list(tz_options.keys()), index=default_idx)
    st.session_state.timezone = tz_options[selected_tz_label]