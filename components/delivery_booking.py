import streamlit as st
import datetime
import secrets
import zoneinfo
from my_utils.db_manager import get_room_status, book_room_with_token

def clear_booking_status():
    st.session_state.booking_completed = False
    st.session_state.booking_error = None

def render():
    with st.container():
        # 💡 「戻る」を廃止し、「ホーム」ボタンのみを配置
        if st.button("ホーム", key="book_nav_home"): 
            clear_booking_status()
            st.session_state.view = "home"
            st.rerun()
        
        st.title("日時・部屋の予約")
        if st.session_state.get("secure_mode", False):
            st.error("完全機密モード：URL招待限定のセッションが発行されます。")

        st.markdown("**タイムゾーン**")
        tz_options = {
            "日本標準時 (JST)": "Asia/Tokyo",
            "中国標準時 (CST)": "Asia/Shanghai",
            "協定世界時 (UTC)": "UTC",
            "米国東部時間 (EST/EDT)": "America/New_York",
            "米国太平洋時間 (PST/PDT)": "America/Los_Angeles",
            "欧州中央時間 (CET/CEST)": "Europe/Paris"
        }
        
        current_tz = st.session_state.get("timezone", "Asia/Tokyo")
        default_label = "日本標準時 (JST)"
        for label, tz_name in tz_options.items():
            if tz_name == current_tz:
                default_label = label
                break
                
        selected_tz_label = st.selectbox(
            "タイムゾーン", 
            list(tz_options.keys()), 
            index=list(tz_options.keys()).index(default_label), 
            label_visibility="collapsed",
            on_change=clear_booking_status
        )
        selected_tz = tz_options[selected_tz_label]
        st.session_state.timezone = selected_tz

        tz = zoneinfo.ZoneInfo(selected_tz)
        now = datetime.datetime.now(tz)
        today = now.date()
        
        st.caption(f"現在の選択地域時刻: {now.strftime('%Y-%m-%d %H:%M')}")
            
        st.markdown("**1. 日程選択**")
        book_date = st.date_input(
            "日付", 
            value=today, 
            min_value=today, 
            label_visibility="collapsed",
            on_change=clear_booking_status
        )
    
        st.markdown("**2. 時間帯と部屋の選択**")
        rooms = get_room_status()
        
        col_time, col_room = st.columns(2)
        with col_time:
            time_choice = st.selectbox(
                "時間帯", 
                ["10:00", "13:00", "15:00", "19:00"],
                on_change=clear_booking_status
            )
        with col_room:
            base_rooms = ["A", "B", "C"]
            room_choice_label = st.selectbox(
                "部屋", 
                [f"ルーム{r}" for r in base_rooms],
                on_change=clear_booking_status
            )
            selected_room_id = room_choice_label.replace("ルーム", "")
            
            is_busy = False
            for r in rooms:
                if len(r) >= 6:
                    r_id, _, r_time, _, _, r_date = r
                    if str(r_id).strip().upper() == str(selected_room_id).strip().upper() and r_date == str(book_date) and r_time == time_choice:
                        is_busy = True
                        break

        selected_hour, selected_minute = map(int, time_choice.split(':'))
        selected_time_obj = datetime.time(selected_hour, selected_minute)
        
        selected_dt = datetime.datetime.combine(book_date, selected_time_obj).replace(tzinfo=tz)
        is_past = selected_dt < now

        st.markdown("<br><div class='delivery-btn-container'>", unsafe_allow_html=True)
        
        if "booking_error" not in st.session_state:
            st.session_state.booking_error = None

        if st.button("予約を確定する", type="primary", use_container_width=True):
            if is_past:
                st.session_state.booking_error = "過去の時間は指定できません。未来の日時を選択してください。"
                st.session_state.booking_completed = False
            elif is_busy:
                st.session_state.booking_error = "選択した日時の部屋はすでに埋まっています。別の時間または部屋を選択してください。"
                st.session_state.booking_completed = False
            else:
                st.session_state.booking_error = None
                slide_title = st.session_state.get("selected_slide_name") or st.session_state.get("slide_name") or "名称未設定"
                token = book_room_with_token(selected_room_id, time_choice, slide_title, str(book_date))
                
                st.session_state.booked_time = time_choice
                st.session_state.booked_room = selected_room_id
                st.session_state.room_token = token
                st.session_state.booking_completed = True
                st.rerun()

        if st.session_state.booking_error:
            st.error(st.session_state.booking_error)

        if st.session_state.get("booking_completed", False):
            st.success("予約が完了しました。")
            
            room_id = st.session_state.booked_room
            token = st.session_state.room_token
            
            base_url = "https://opulent-rotary-phone-5vqvvgq5qxjx37rvr-8501.app.github.dev"
            invite_link = f"{base_url}/?room={room_id}&token={token}"
            
            st.markdown("**視聴者用 招待リンク**")
            st.code(invite_link, language="text")
            
            if st.button("準備室へ進む", type="primary", use_container_width=True):
                st.session_state.booking_completed = False
                st.session_state.view = "delivery_setup"
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)