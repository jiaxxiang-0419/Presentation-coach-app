import streamlit as st
import sqlite3
import datetime
import requests

# ==========================================
# ⚠️ DiscordでコピーしたWebhook URL
# ==========================================
DISCORD_WEBHOOK_URL = st.secrets["WEBHOOK_CONTACT"]

def send_to_discord(name, email, category, message):
    """DiscordのWebhookに問い合わせ内容を送信する関数"""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    email_text = email.strip() if email.strip() else "未入力"
    name_text = name.strip() if name.strip() else "名無しユーザー"

    discord_message = f"📬 **新しいお問い合わせが届きました！**\n" \
                      f"**【送信者】** {name_text}\n" \
                      f"**【連絡先】** {email_text}\n" \
                      f"**【種別】** {category}\n" \
                      f"**【内容】**\n{message}\n" \
                      f"*(送信日時: {now_str})*"

    payload = {
        "content": discord_message
    }
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"送信エラーが発生しました: {e}")
        return False

def render():
    # 上部ナビゲーション（ホームボタンのみ）
    if st.button("ホーム", key="contact_nav_home", use_container_width=True):
        st.session_state.view = "home"
        st.rerun()

    st.title(" お問い合わせ・サポート")
    # 👇 ここで文章を分けて、間に改行（st.markdown）を入れるのが一番綺麗に崩れず改行できます
    st.markdown("ご質問、バグの報告、機能のご要望などがございましたら、お気軽にお送りください。")
    st.markdown("お問い合わせ内容の確認・ご対応には **2〜3日程度** お時間をいただく場合がございます。")    

    # 入力欄をクリアするためのセッションステート初期化
    if "form_submitted" not in st.session_state:
        st.session_state.form_submitted = False

    # 送信完了後にリセットするため、一度セッションの値をクリア
    if st.session_state.form_submitted:
        st.success("🎉 お問い合わせを送信しました。貴重なご意見ありがとうございます！")
        st.session_state.form_submitted = False

    # お問い合わせ入力フォーム
    with st.form("contact_form"):
        name = st.text_input("お名前（またはニックネーム）")
        email = st.text_input("連絡先メールアドレス（返信用）")
        category = st.selectbox(
            "お問い合わせ種別",
            ["使い方について", "バグ・エラーの報告", "機能の要望", "その他"]
        )
        message = st.text_area("お問い合わせ内容", height=150, placeholder="詳細をご記入ください...")
        
        submitted = st.form_submit_button(" 送信する", use_container_width=True, type="primary")
        
        if submitted:
            if not message.strip():
                st.error(" お問い合わせ内容を入力してください。")
            else:
                with st.spinner("送信中..."):
                    success = send_to_discord(name, email, category, message)
                    
                if success:
                    # 送信成功フラグを立てて再読み込みし、入力欄をスッキリ消す
                    st.session_state.form_submitted = True
                    st.rerun()