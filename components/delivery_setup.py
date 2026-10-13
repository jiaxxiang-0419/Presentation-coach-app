import streamlit as st
import datetime
import zoneinfo
import json
import streamlit.components.v1 as components
import os
from my_utils.db_manager import (
    get_all_slides, get_slide_by_id, get_combined_calendar_events, book_room_with_token, get_db
)
from my_utils.daily_api import create_daily_room

def save_audio_url(room_token, daily_url):
    if not daily_url: return
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS audio_rooms (room_token TEXT PRIMARY KEY, daily_url TEXT)")
        cursor.execute("REPLACE INTO audio_rooms (room_token, daily_url) VALUES (?, ?)", (room_token, daily_url))
        conn.commit()
    except:
        pass

def clear_setup_status():
    st.session_state.booking_saved = False
    st.session_state.setup_booking_error = None
    st.session_state.setup_datetime_error = None
    st.session_state.setup_datetime_success = None

def clear_edit_state():
    st.session_state.pop("edit_room_id", None)
    st.session_state.pop("edit_room_token", None)
    st.session_state.pop("edit_slide_title", None)
    st.session_state.pop("setup_custom_title", None)
    st.session_state.pop("booked_date", None)
    st.session_state.pop("booked_time", None)

def render_html_calendar():
    # 💡 現在のユーザーを取得して渡す
    current_user = st.session_state.get("current_user", "default_user")
    
    # 修正：ここでget_combined_calendar_eventsにユーザー名を渡す
    bookings = get_combined_calendar_events(username=current_user) or []
    bookings_json = json.dumps(bookings)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(base_dir, "templates", "booking_calendar.html")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            html = f.read()
        html = html.replace("/* DATA_PLACEHOLDER */", f"const bookings = {bookings_json};")
        components.html(html, height=750, scrolling=True)
    except FileNotFoundError:
        st.error(f"ファイルが見つかりません: {file_path}")
        
def is_room_booked_at(room_id, date_str, time_str, exclude_token=None):
    try:
        conn = get_db()
        cursor = conn.cursor()
        if exclude_token:
            cursor.execute(
                "SELECT count(*) FROM room_bookings WHERE room_id = ? AND booked_date = ? AND booked_time = ? AND room_token != ?",
                (str(room_id), str(date_str), str(time_str), exclude_token)
            )
        else:
            cursor.execute(
                "SELECT count(*) FROM room_bookings WHERE room_id = ? AND booked_date = ? AND booked_time = ?",
                (str(room_id), str(date_str), str(time_str))
            )
        return cursor.fetchone()[0] > 0
    except:
        return False

def verify_slide_exists(slide_id):
    if not slide_id:
        return False
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM slide_assets WHERE id = ?", (int(slide_id),))
        count = cursor.fetchone()[0]
        return count > 0
    except Exception:
        return False
        
def render():
    st.markdown("""
        <style>
        .stCalendar { background: #f8fafc; border-radius: 12px; padding: 10px; }
        .fc-event { font-size: 0.8rem; cursor: pointer; }
        </style>
    """, unsafe_allow_html=True)

    if st.button("ホーム", key="setup_nav_home", use_container_width=True): 
        clear_setup_status(); clear_edit_state()
        st.session_state.view = "home"; st.session_state.view_history = []; st.rerun()

    st.title("スケジュール予約・準備室")
    mode = st.session_state.get("booking_mode", "immediate")

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown("### 1. 日時と部屋の選択")
        tz_str = st.session_state.get("timezone", "Asia/Tokyo")
        local_tz = zoneinfo.ZoneInfo(tz_str)
        now = datetime.datetime.now(local_tz)
        today = now.date()
        if mode == "reserve":
            calc_h = now.hour
            if now.minute < 20: 
                calc_m = 20
            elif now.minute < 40: 
                calc_m = 40
            else: 
                calc_m = 0
                calc_h = (calc_h + 1) % 24
                
            default_date = today
            if calc_h == 0 and now.hour == 23:
                default_date = today + datetime.timedelta(days=1)

            if st.session_state.get("booked_date"):
                try:
                    loaded_date = datetime.datetime.strptime(st.session_state.booked_date, "%Y-%m-%d").date()
                    if loaded_date >= today: default_date = loaded_date
                except: pass
            
            default_hour_idx = calc_h
            default_minute_idx = 0 if calc_m == 0 else 1 if calc_m == 20 else 2

            if st.session_state.get("booked_time"):
                try:
                    h_str, m_str = st.session_state.booked_time.split(":")
                    default_hour_idx = int(h_str)
                    default_minute_idx = ["00", "20", "40"].index(m_str)
                except: pass

            book_date = st.date_input("日付", value=default_date, min_value=today, key="setup_book_date", on_change=clear_setup_status)
            c_hr, c_min = st.columns(2)
            with c_hr: selected_hour = st.selectbox("時間（時）", [f"{i:02d}" for i in range(24)], index=default_hour_idx, key="setup_select_hour", on_change=clear_setup_status)
            with c_min: selected_minute = st.selectbox("（分）", ["00", "20", "40"], index=default_minute_idx, key="setup_select_minute", on_change=clear_setup_status)
            time_choice = f"{selected_hour}:{selected_minute}"
            selected_time_obj = datetime.time(int(selected_hour), int(selected_minute))
            selected_dt = datetime.datetime.combine(book_date, selected_time_obj).replace(tzinfo=local_tz)

        else:
            book_date = today
            if now.minute < 20: target_h, target_m = now.hour, 20
            elif now.minute < 40: target_h, target_m = now.hour, 40
            else: target_h, target_m = (now.hour + 1) % 24, 0

            time_options = []
            calc_time = datetime.datetime(now.year, now.month, now.day, target_h, target_m)
            for _ in range(3):
                time_options.append(calc_time.strftime("%H:%M"))
                calc_time += datetime.timedelta(minutes=20)

            time_choice = st.radio("適用時間枠", options=time_options, index=0, key="setup_radio_slot", on_change=clear_setup_status)
            sel_h, sel_m = map(int, time_choice.split(":"))
            selected_time_obj = datetime.time(sel_h, sel_m)
            selected_dt = datetime.datetime.combine(book_date, selected_time_obj).replace(tzinfo=local_tz)

        is_past = selected_dt < now

        st.markdown("#### 部屋の選択")
        editing_token = st.session_state.get("edit_room_token")
        date_str = str(book_date)
        
        room_options = {}
        booked_room_ids = []
        for r_id in ["A", "B", "C"]:
            busy = is_room_booked_at(r_id, date_str, time_choice, exclude_token=editing_token)
            if busy:
                booked_room_ids.append(r_id)
            status_text = "使用中" if busy else "空き"
            label = f"ルーム{r_id} ({status_text})"
            room_options[label] = r_id
            
        editing_room_id = st.session_state.get("edit_room_id")
        default_room_idx = ["A", "B", "C"].index(editing_room_id) if editing_room_id in ["A", "B", "C"] else 0

        selected_room_label = st.selectbox("使用する部屋", list(room_options.keys()), index=default_room_idx, key="setup_select_room", on_change=clear_setup_status)
        selected_room_id = room_options[selected_room_label]
        
        actual_is_busy = is_room_booked_at(selected_room_id, date_str, time_choice, exclude_token=editing_token)

        if st.button("日時・部屋を確定する", key="setup_confirm_datetime_btn"):
            if is_past:
                st.session_state.setup_datetime_error = f"指定された時間（{time_choice}）は現在の時刻を過ぎています。未来の時間帯を選択してください。"
                st.session_state.setup_datetime_success = None
            elif actual_is_busy:
                st.session_state.setup_datetime_error = f"ルーム{selected_room_id}の指定時間帯（{time_choice}）はすでに予約されています。別の部屋をお選びください。"
                st.session_state.setup_datetime_success = None
            else:
                st.session_state.setup_datetime_error = None
                st.session_state.setup_datetime_success = f"日時・部屋を確定しました。\n- 予約日時: {book_date.strftime('%Y/%m/%d')} {time_choice}\n- 使用部屋: ルーム{selected_room_id}"

        if st.session_state.get("setup_datetime_error"): st.error(st.session_state.setup_datetime_error)
        elif st.session_state.get("setup_datetime_success"): st.success(st.session_state.setup_datetime_success)

        st.write("---")

        st.markdown("### 2. 発表資料と設定")
        target_min = st.number_input("目標の発表時間（分）", min_value=1, max_value=20, value=st.session_state.get("live_target_minutes", 5), step=1, key="setup_target_min")
        st.session_state.live_target_minutes = target_min
        
        custom_title = st.text_input("発表のタイトル（任意）", placeholder="例: Q3新規事業提案", key="setup_custom_title")
        is_public_choice = st.radio("公開設定", ["一般公開（ホーム画面に表示）", "非公開（URLを知っている人のみ）"], index=0, key="setup_public_radio")
        is_secure_mode = ("非公開" in is_public_choice)

        # 💡 修正箇所：現在のユーザーの資料だけを取得する
        current_user = st.session_state.get("current_user", "default_user")
        slides = get_all_slides(username=current_user)
        
        if slides:
            slide_options = {slide[1]: slide[0] for slide in slides}
            selected_name = st.selectbox("資料を選択", list(slide_options.keys()), key="setup_select_slide", on_change=clear_setup_status)
            
            if st.button("設定・資料を確定する", key="setup_confirm_slide_btn"):
                final_title = custom_title.strip() if custom_title.strip() else selected_name
                slide_id_val = slide_options[selected_name]
                
                loaded_scripts = {}
                try:
                    conn = get_db()
                    cursor = conn.cursor()
                    # 💡 念のため原稿データ取得時も username で絞り込み（別人が同IDを引かないようにガード）
                    cursor.execute("SELECT notes_json FROM slide_assets WHERE id = ? AND username = ?", (int(slide_id_val), current_user))
                    row = cursor.fetchone()
                    if row and row[0]:
                        loaded_scripts = json.loads(row[0])
                except Exception:
                    pass

                st.session_state.update({
                    # 💡 修正箇所：PDFデータも現在のユーザー名を指定して取得
                    "selected_pdf_bytes": get_slide_by_id(slide_id_val, username=current_user), 
                    "slide_name": final_title,  
                    "slide_id": slide_id_val,
                    "secure_mode": is_secure_mode,
                    "scripts": loaded_scripts 
                })
                mode_text = "非公開（URL限定）" if is_secure_mode else "一般公開"
                st.success(f"確定しました。\n- タイトル: {final_title}\n- 公開設定: {mode_text}\n- 目標時間: {target_min}分")
        else:
            st.error("登録されている資料がありません。練習画面から資料を追加してください。")

    with col_right:
        st.markdown("#### 予約状況カレンダー")
        render_html_calendar()

    st.write("---")

    st.markdown("### 3. 開始・登録")
    
    if "setup_booking_error" not in st.session_state: st.session_state.setup_booking_error = None

    if mode == "immediate":
        if st.button("待機室へ進む", type="primary", use_container_width=True, key="setup_go_waiting_btn", disabled=is_past or actual_is_busy):
            slide_title = st.session_state.get("slide_name", "名称未設定")
            
            if not st.session_state.get("selected_pdf_bytes"): 
                st.error("「設定・資料を確定する」ボタンを押して資料を確定してください。")
            elif not verify_slide_exists(st.session_state.get("slide_id")):
                st.error("指定された資料が見つかりません。資料を選び直して再度確定してください。")
            else:
                with st.spinner("音声配信の準備中..."):
                    daily_url = create_daily_room()
                    
                if not daily_url:
                    st.stop()
                    
                room_token = book_room_with_token(selected_room_id, time_choice, slide_title, str(book_date))
                save_audio_url(room_token, daily_url)
                
                st.session_state.booked_room = selected_room_id
                st.session_state.booked_time = time_choice
                st.session_state.room_token = room_token
                st.session_state.view = "delivery_waiting"
                st.rerun()
    else:
        if not st.session_state.get("booking_saved", False):
            if st.button("スケジュールに登録して招待リンクを発行する", type="primary", use_container_width=True, key="setup_book_action_btn", disabled=is_past or actual_is_busy):
                slide_title = st.session_state.get("slide_name", "名称未設定")
                
                if not st.session_state.get("selected_pdf_bytes"): 
                    st.session_state.setup_booking_error = "先に「設定・資料を確定する」ボタンを押して資料を確定してください。"
                    st.session_state.booking_saved = False
                elif is_past:
                    st.session_state.setup_booking_error = "指定時間が現在時刻を過ぎています。未来の時刻を選択してください。"
                    st.session_state.booking_saved = False
                elif actual_is_busy:
                    st.session_state.setup_booking_error = "選択した部屋の指定時間帯はすでに予約されています。"
                    st.session_state.booking_saved = False
                elif not verify_slide_exists(st.session_state.get("slide_id")):
                    st.session_state.setup_booking_error = "指定された資料が見つかりません。資料を選び直して再度確定してください。"
                    st.session_state.booking_saved = False
                else:
                    st.session_state.setup_booking_error = None
                    with st.spinner("音声配信のスケジュールを登録中..."):
                        daily_url = create_daily_room()
                        
                    room_token = book_room_with_token(selected_room_id, time_choice, slide_title, str(book_date), editing_token)
                    save_audio_url(room_token, daily_url)
                    
                    st.session_state.update({
                        "booked_time": time_choice, 
                        "booked_room": selected_room_id, 
                        "room_token": room_token,
                        "booking_saved": True
                    })
                    st.rerun()

        if st.session_state.get("setup_booking_error"): 
            st.error(st.session_state.setup_booking_error)
        
        current_token = st.session_state.get("room_token")
        if current_token and st.session_state.get("booking_saved", False):
            st.success("予約スケジュールと音声配信ルームが登録されました。")
            current_room = st.session_state.get("booked_room", "A")
            base_url = "https://opulent-rotary-phone-5vqvvgq5qxjx37rvr-8501.app.github.dev"
            entry_url = f"{base_url}/?room={current_room}&token={current_token}"
            
            st.markdown("**視聴者用 招待リンク**")
            st.info("ホーム画面の予約一覧から、設定時間になったら本番を開始できます。")
            st.code(entry_url, language="text")
            
            if st.button("ホーム画面に戻る", type="primary", use_container_width=True, key="setup_back_home_btn"):
                clear_edit_state()
                st.session_state.booking_saved = False
                st.session_state.view = "home"
                st.rerun()