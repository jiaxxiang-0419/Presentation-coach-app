import streamlit as st
import time, datetime, random, sqlite3, json, uuid, fitz
from PIL import Image

DB_FILE = "presentation_app.db"

@st.cache_data(show_spinner=False)
def get_pdf_page_image(pdf_bytes, page_num):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(page_num)
    pix = page.get_pixmap()
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

def render():
    # ナビゲーション
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("🏠 ホームへ"): st.session_state.view = "home"; st.rerun()
    with col_nav2:
        if st.button("⬅️ 戻る"): st.session_state.view = "delivery_booking" if st.session_state.view == "delivery_setup" else "home"; st.rerun()

    # 1. 視聴者ペルソナ選択画面
    if st.session_state.view == "delivery_booking":
        st.title("🌍 プレゼン本番：視聴者入室")
        c1, c2, c3 = st.columns(3)
        if c1.button("🤨 辛口な役員"): st.session_state.persona="役員"; st.session_state.view="delivery_live"; st.rerun()
        if c2.button("😊 優しい同僚"): st.session_state.persona="同僚"; st.session_state.view="delivery_live"; st.rerun()
        if c3.button("👀 一般の観客"): st.session_state.persona="観客"; st.session_state.view="delivery_live"; st.rerun()

    # 2. 発表者準備室
    elif st.session_state.view == "delivery_setup":
        st.title("⚙️ 発表者：本番準備室")
        st.session_state.live_target_minutes = st.slider("目標時間(分)", 1, 15, st.session_state.live_target_minutes)
        if st.button("🔗 招待URL発行"): st.session_state.room_url = f"URL_{uuid.uuid4().hex[:6]}"
        st.write(f"招待リンク: {st.session_state.room_url}")
        if st.button("🚀 待機室へ進む"): st.session_state.view = "delivery_waiting"; st.rerun()

    # 3. 待機室（自動タイマー）
    elif st.session_state.view == "delivery_waiting":
        st.error("🔴 ON AIR STANDBY")
        st.components.v1.html("""
            <div id="wait-timer" style="font-size: 80px; color: red;">00:30</div>
            <script>
            let w=30; setInterval(()=>{ w--; document.getElementById('wait-timer').innerText="00:"+(w<10?"0"+w:w); }, 1000);
            </script>
        """, height=100)
        if st.button("⏱ 本番開始"): st.session_state.view = "delivery_live"; st.rerun()

    # 4. 本番ライブ（ペルソナリアクション＆タイマー）
    elif st.session_state.view == "delivery_live":
        st.markdown(f"**🔴 LIVE** | 視聴ペルソナ: **{st.session_state.persona}**")
        
        # 画面右：リアクション
        col_l, col_r = st.columns([2, 1])
        with col_r:
            st.markdown("#### 📣 視聴者リアクション")
            if st.button("📉 結論が見えない"): st.toast("指摘を送信しました")
            if st.button("👏 その調子！"): st.toast("応援を送信しました")
            st.markdown("#### 🎙️ 現在の発表原稿")
            st.info(st.session_state.scripts.get(st.session_state.page_num, "（原稿未登録）"))

        with col_l:
            img = get_pdf_page_image(st.session_state.selected_pdf_bytes, st.session_state.page_num)
            st.image(img, use_container_width=True)
            if st.button("次へ"): st.session_state.page_num += 1; st.rerun()
            
        # JSタイマー（Word版の仕様を継承し、超過時に赤文字変化）
        st.components.v1.html("""
            <div id="live-timer" style="font-size: 50px; color: #10b981;">00:00</div>
            <script>
            let t=0; setInterval(()=>{ 
                t++; let m=Math.floor(t/60), s=t%60; 
                document.getElementById('live-timer').innerText = (m<10?"0"+m:m)+":"+(s<10?"0"+s:s);
                if(t > 300) document.getElementById('live-timer').style.color = "red";
            }, 1000);
            </script>
        """, height=100)

    # 5. 結果画面（タイムライン集計）
    elif st.session_state.view == "delivery_result":
        st.success("🎉 本番終了！お疲れ様でした！")
        # (※Word版にある詳細な結果分析ロジックをここに展開)