import streamlit as st
import sqlite3
import datetime
import requests

DISCORD_WEBHOOK_URL = st.secrets["WEBHOOK_BOOKS"]

def send_book_to_discord(title, author, category, reason, contributor):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    author_text = author.strip() if author.strip() else "不明"
    category_text = category.strip() if category.strip() else "未指定"
    contributor_text = contributor.strip() if contributor.strip() else "名無し"

    discord_message = f"**新着の推薦図書**\n" \
                      f"タイトル: {title}\n" \
                      f"著者: {author_text}\n" \
                      f"カテゴリ: {category_text}\n" \
                      f"おすすめ理由:\n{reason}\n" \
                      f"推薦者: {contributor_text}\n" \
                      f"({now_str})"

    payload = {"content": discord_message}
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException:
        return False

def init_db():
    conn = sqlite3.connect("books.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommended_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT,
            affiliate_url TEXT NOT NULL,
            reason TEXT NOT NULL,
            contributor TEXT NOT NULL,
            created_at TEXT
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM recommended_books")
    if cursor.fetchone()[0] == 0:
        default_books = [
            ("伝え方が9割", "佐々木 圭一", "話し方", "https://www.amazon.co.jp/dp/4478017212", "「ノー」を「イエス」に変える技術や、心に響く言葉づくりのノウハウ。", "運営"),
            ("1分で話せ", "伊藤 羊一", "プレゼン", "https://www.amazon.co.jp/dp/4797395230", "結論をシンプルにまとめ、聞き手を惹きつけるフレームワーク。", "運営"),
            ("FACTFULNESS", "ハンス・ロスリング 他", "データ", "https://www.amazon.co.jp/dp/4822289605", "思い込みを外し、客観的なファクトに基づいて物事を捉える力。", "運営"),
            ("スティーブ・ジョブズ 驚異のプレゼン", "カーマイン・ガロ", "構成力", "https://www.amazon.co.jp/dp/482224816X", "聴衆を魅了するストーリーテリングの手法。", "運営"),
            ("人を動かす", "D・カーネギー", "コミュニケーション", "https://www.amazon.co.jp/dp/442210098X", "人間関係の原則と、相手の心を開く本質。", "運営"),
            ("イシューからはじめよ", "安宅 和人", "生産性", "https://www.amazon.co.jp/dp/4862760856", "本質的な問題（イシュー）を見極め、生産性を高める思考法。", "運営")
        ]
        cursor.executemany("""
            INSERT INTO recommended_books (title, author, category, affiliate_url, reason, contributor, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """, default_books)
        conn.commit()
    conn.close()

def render():
    init_db()

# ナビゲーション
    if st.button("ホーム", key="books_nav_home", use_container_width=True):
        st.session_state.view = "home"
        st.rerun()
    st.title("推奨図書")
    st.markdown("プレゼンテーションおよびスキルアップのための厳選書籍")

    # 💡 綺麗に高さを揃えるためのCSS（タイトル用とメタ情報用の領域をピタッと固定）
    st.markdown("""
        <style>
        .book-title {
            font-size: 1.1rem;
            font-weight: 700;
            height: 4rem;
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            margin-bottom: 0px;
        }
        .book-meta {
            height: 3rem;
            overflow: hidden;
            margin-bottom: 8px;
        }
        .book-reason {
            height: 7.5rem;
            overflow: hidden;
        }
        </style>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["ライブラリ", "書籍を推薦する"])

    # ----------------------------------------------------
    # タブ1：ライブラリ
    # ----------------------------------------------------
    with tab1:
        st.markdown("#### おすすめ図書一覧")
        
        conn = sqlite3.connect("books.db")
        cursor = conn.cursor()
        cursor.execute("SELECT title, author, category, affiliate_url, reason, contributor FROM recommended_books ORDER BY id DESC")
        books = cursor.fetchall()
        conn.close()

        if not books:
            st.write("登録されている書籍はありません。")
        else:
            for i in range(0, len(books), 3):
                row_books = books[i:i+3]
                cols = st.columns(3)
                
                for idx, book in enumerate(row_books):
                    title, author, category, url, reason, contributor = book
                    with cols[idx]:
                        with st.container(border=True, height=315):
                            cat_text = f" / {category}" if category else ""
                            
                            # 2行分のスペースを確保したタイトルとメタ情報
                            st.markdown(f'<div class="book-title">{title}</div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="book-meta"><span style="font-size: 0.8rem; color: #64748b;">{author}{cat_text} ｜ 推薦: {contributor}</span></div>', unsafe_allow_html=True)
                            
                            st.markdown(f'<div class="book-reason">{reason}</div>', unsafe_allow_html=True)
                            
                            if url:
                                st.link_button("Amazonで詳細を見る", url, use_container_width=True)
                            else:
                                st.caption("準備中")

    # ----------------------------------------------------
    # タブ2：推薦フォーム ＆ 管理者メニュー
    # ----------------------------------------------------
    with tab2:
        st.markdown("#### 新しい書籍の追加・推薦")
        
        with st.form("book_form"):
            b_title = st.text_input("タイトル")
            b_author = st.text_input("著者名")
            b_category = st.text_input("カテゴリ（例: プレゼン、思考法）")
            b_reason = st.text_area("推薦理由", height=120)
            b_contributor = st.text_input("推薦者名", value="名無し")
            
            submitted = st.form_submit_button("送信", use_container_width=True, type="primary")

            if submitted:
                if not b_title.strip() or not b_reason.strip():
                    st.warning("タイトルと推薦理由は必須です。")
                else:
                    success = send_book_to_discord(b_title, b_author, b_category, b_reason, b_contributor)
                    if success:
                        st.write("送信が完了しました。")

        st.write("---")
        
        # 管理者専用エリア
        with st.expander("管理者メニュー"):
            admin_pass = st.text_input("パスワード", type="password", key="admin_pass")
            
            if admin_pass == st.secrets["ADMIN_PASSWORD"]:
                admin_tab_add, admin_tab_del = st.tabs(["追加", "削除"])
                
                # --- 追加 ---
                with admin_tab_add:
                    with st.form("admin_add_book_form"):
                        a_title = st.text_input("タイトル")
                        a_author = st.text_input("著者名")
                        a_category = st.text_input("カテゴリ")
                        a_url = st.text_input("URL")
                        a_reason = st.text_area("推薦理由")
                        a_contributor = st.text_input("推薦者名")
                        
                        submit_admin = st.form_submit_button("登録", type="primary")
                        
                        if submit_admin:
                            if not a_title or not a_url:
                                st.warning("タイトルとURLは必須です。")
                            else:
                                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                                conn = sqlite3.connect("books.db")
                                cursor = conn.cursor()
                                cursor.execute("""
                                    INSERT INTO recommended_books (title, author, category, affiliate_url, reason, contributor, created_at)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, (a_title, a_author, a_category, a_url, a_reason, a_contributor, now_str))
                                conn.commit()
                                conn.close()
                                st.rerun()
                
                # --- 削除 ---
                with admin_tab_del:
                    conn = sqlite3.connect("books.db")
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, title, author FROM recommended_books ORDER BY id DESC")
                    all_books = cursor.fetchall()
                    
                    if not all_books:
                        st.write("登録されている書籍はありません。")
                    else:
                        for b_id, b_title, b_author in all_books:
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"{b_title} ({b_author})")
                            with col2:
                                if st.button("削除", key=f"del_{b_id}", use_container_width=True):
                                    cursor.execute("DELETE FROM recommended_books WHERE id = ?", (b_id,))
                                    conn.commit()
                                    st.rerun()
                    conn.close()