import streamlit as st

def render():
    # 上部ナビゲーション（ホームボタンのみ）
    if st.button("ホーム", key="cheer_nav_home", use_container_width=True):
        st.session_state.view = "home"
        st.rerun()

    st.title("開発ストーリー")
    st.markdown("アプリに込めた想いと開発背景")
    st.write("---")

    # --- 1. アプリを作ろうと思った理由（開発秘話） ---
    st.markdown("### 開発背景")
    
    with st.container(border=True):
        st.markdown("""
        **「なぜ、部屋で一人で練習するときは完璧なのに、本番になると頭が真っ白になってしまうのか？」**

        このプレゼン練習アプリの開発は、私自身のどうしようもない悔しさと、過去の失敗経験からスタートしました。

        私は元々、人前に立って話す際に極度に緊張してしまうタイプでした。本番前には入念に台本を作り、ストップウォッチを片手に、部屋の壁に向かって何度も練習を繰り返しました。その時は全く緊張せず、時間通りに流暢に話すことができます。しかし、いざ本番を迎え、マイクを握って大勢の視線を浴びた瞬間、心拍数は跳ね上がり、声は上ずり、練習の成果の半分も発揮できないのです。

        ここで私は一つの事実に気づきました。それは、**「緊張しない安全な場所」での練習は、本番のプレッシャーの前では無力である**ということです。この致命的なギャップを克服しない限り、本当の意味でのプレゼン力は身につかないと痛感しました。

        そこで私は、心地よく練習をサポートするだけのツールではなく、「徹底的に緊張する要素を詰め込んだアプリ」を作ることを決意しました。あえてユーザーにプレッシャーを与える環境です。

        中でも最もこだわったのが、「目の前に人がいて、自分を見ている」という要素の導入でした。画面上に仮想の聴衆を配置し、無数の視線が常にこちらに向いている状態を作り出しました。タイマーの無機質な数字を眺めるだけでなく、「人に見られている」という生々しいプレッシャーを視覚的に再現することで、本番特有の緊張感を、日々の練習の中に強制的に引き起こそうと考えたのです。

        ---

        #### プレッシャーのかかる仕様にする理由
        それは、プレゼンにおいて「本番を想定した練習」が何よりも大事だと考えているからです。

        準備不足や不安を抱えたまま前に出ると、本番特有の空気に呑まれてしまいます。そしてその焦りは、言葉以上に聞き手へと伝播し、「大丈夫かな？」と思われた瞬間にメッセージは届かなくなります。プレゼンを成功させるには、緊張する環境に身を置き、場数を踏むしかありません。

        このアプリは、そのプレッシャーに慣れるために生まれました。視線を感じながら言葉を紡ぎ続ける。その地道な練習の積み重ねが、本番での震えを止め、自信を持って思いを伝えるための最大の武器になるはずです。
        """)

    st.write("---")

    # --- 2. 投げ銭（応援サポート）セクション ---
    st.markdown("### サポート")
    st.markdown("広告は一切導入していません。継続的なサーバー維持や今後の機能開発の励みとなりますので、ご支援いただけますと幸いです。")

    col_sup1, col_sup2, col_sup3, col_sup4 = st.columns(4)
    
    with col_sup1:
        with st.container(border=True):
            st.markdown("**100円の応援**")
            st.markdown("### 100円")
            st.link_button(
                "支援する", 
                "https://buy.stripe.com/test_fZu7sL56H9e2fhM5B54F200", 
                use_container_width=True
            )

    with col_sup2:
        with st.container(border=True):
            st.markdown("**コーヒー一杯**")
            st.markdown("### 500円")
            st.link_button(
                "支援する", 
                "https://buy.stripe.com/test_bJe9ATar1bma7PkaVp4F203", 
                use_container_width=True
            )

    with col_sup3:
        with st.container(border=True):
            st.markdown("**サーバー応援**")
            st.markdown("### 1,000円")
            st.link_button(
                "支援する", 
                "https://buy.stripe.com/test_bJedR956H9e2glQ7Jd4F202", 
                use_container_width=True
            )

    with col_sup4:
        with st.container(border=True):
            st.markdown("**スポンサー**")
            st.markdown("### 自由金額")
            st.link_button(
                "支援する", 
                "https://buy.stripe.com/test_bJecN58iTeym3z46F94F201", 
                use_container_width=True
            )

    st.caption("決済ボタンを押すと、Stripe社の安全な決済ページへ移動します。")