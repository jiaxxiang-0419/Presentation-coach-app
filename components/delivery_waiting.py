import streamlit as st
import random
import zoneinfo
import time
from datetime import datetime, timedelta
from my_utils.db_manager import cancel_booking

ENCOURAGE_POOL = [
    "完璧な発表を目指さなくて大丈夫です。途中で言葉が詰まっても、一生懸命に伝えている人間味として聞き手に伝わります。",
    "会場の聞き手は味方です。まずは目の前のひとに語りかけるつもりで話しましょう。",
    "大きく息を吸い、それ以上にゆっくりと吐き出してください。体を落ち着かせることで、声の緊張が和らぎます。",
    "上手に話すことよりも、これまで準備してきた内容をそのまま届けることが大切です。",
    "頭が真っ白になったときは、3秒間ほど静かに間を取りましょう。それは効果的な沈黙（間）として機能します。",
    "このテーマについて、いまこの空間で最も詳しいのはあなた自身です。自信を持ちましょう。",
    "緊張しているのは、この発表に真剣に向き合っている証拠です。そのエネルギーをそのまま言葉に乗せてください。"
]

def render():
    booking_mode = st.session_state.get("booking_mode", "immediate")
    booked_time_str = st.session_state.get("booked_time", "12:00")
    
    tz_str = st.session_state.get("timezone", "Asia/Tokyo")
    local_tz = zoneinfo.ZoneInfo(tz_str)
    now = datetime.now(local_tz)
    
    booked_date_str = st.session_state.get("booked_date", str(now.date()))
    
    is_time_to_start = False
    remain_mins_text = ""

    if booking_mode == "immediate":
        is_time_to_start = True
        display_time_str = "今すぐ（即時開始）"
    else:
        display_time_str = f"{booked_date_str} {booked_time_str}"
        try:
            b_dt = datetime.strptime(f"{booked_date_str} {booked_time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=local_tz)
            start_allowed_time = b_dt - timedelta(minutes=10)
            end_allowed_time = b_dt + timedelta(minutes=30)
            
            if now > end_allowed_time:
                is_time_to_start = False
                remain_mins_text = "（予約時間が終了しました）"
            elif now >= start_allowed_time:
                is_time_to_start = True
            else:
                is_time_to_start = False
                remain = int((start_allowed_time - now).total_seconds() / 60) + 1
                remain_mins_text = f"（開始可能まであと {remain} 分）"
        except Exception as e:
            is_time_to_start = False

    with st.container():
        col_dw_nav1, col_dw_nav2 = st.columns(2)
        
        # 💡 左側（col_dw_nav1）に「戻る」を配置
        with col_dw_nav1:
            st.markdown("<div class='nav-btn-container'>", unsafe_allow_html=True)
            if st.button("戻る", key="dw_nav_prev", use_container_width=True):
                if booking_mode == "immediate":
                    cancel_booking(st.session_state.get("room_token")) 
                
                history = st.session_state.get("view_history", [])
                if history:
                    st.session_state.view = history.pop()
                else:
                    if booking_mode == "reserve":
                        st.session_state.view = "home"
                    else:
                        st.session_state.view = "delivery_setup"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # 💡 右側（col_dw_nav2）に「ホーム」を配置
        with col_dw_nav2:
            st.markdown("<div class='nav-btn-container'>", unsafe_allow_html=True)
            if st.button("ホーム", key="dw_nav_home", use_container_width=True):
                if booking_mode == "immediate":
                    cancel_booking(st.session_state.get("room_token")) 
                st.session_state.view = "home"
                st.session_state.view_history = [] 
                st.rerun()    
            st.markdown("</div>", unsafe_allow_html=True)
        st.info(f"待機室 - ルーム: {st.session_state.get('booked_room', 'Unknown')} | 予定: {display_time_str}")
        
        encourage_msg = random.choice(ENCOURAGE_POOL)
        st.markdown(f"<h3 style='text-align: center; color: #334155; padding: 20px; background: #f1f5f9; border-radius: 12px; margin: 20px 0;'>「{encourage_msg}」</h3>", unsafe_allow_html=True)

        if booking_mode == "reserve" and not is_time_to_start:
            if "終了しました" in remain_mins_text:
                st.warning("予定時間から30分以上経過したため、この予約枠は終了しました。ホーム画面に戻り、新しいスケジュールを予約してください。")
            else:
                st.warning(f"発表開始可能時間は {booked_time_str} の10分前からです。現在開始できません。{remain_mins_text}")

        st.markdown("準備が整ったら、下のボタンを押して本番を開始してください。")

        if st.button("本番を開始する", key="official_start_btn", type="primary", use_container_width=True, disabled=not is_time_to_start): 
            st.session_state.view = "delivery_live"
            st.session_state.time_last_changed = time.time()
            st.session_state.live_timeline = []
            st.session_state.reset_js_flag = True
            st.session_state.page_num = 0 
            st.rerun()