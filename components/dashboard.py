import streamlit as st
import sqlite3
import pandas as pd

def format_duration(seconds):
    """秒数を「分:秒」のフォーマット（例: 02:05）に変換する関数"""
    try:
        sec = int(seconds)
        m = sec // 60
        s = sec % 60
        return f"{m:02d}:{s:02d}"
    except:
        return "00:00"

def render():
    # 💡 セッションから現在のユーザー名を取得（万が一ない場合は default_user）
    current_user = st.session_state.get("current_user", "default_user")

    # ナビゲーション（2カラムに変更）
    col_nav1, col_nav2 = st.columns([1, 1])
    with col_nav1:
        if st.button("ホーム", key="dash_nav_home", use_container_width=True): 
            st.session_state.view = "home"
            st.session_state.view_history = []
            st.rerun()
            
    with col_nav2:
        if st.button("履歴リセット", type="primary", use_container_width=True):
            with sqlite3.connect("presentation_app.db", timeout=20.0) as conn:
                cursor = conn.cursor()
                # 💡 修正：自分の履歴だけを削除するように条件を追加
                cursor.execute("DELETE FROM practice_history WHERE username = ?", (current_user,))
                conn.commit()
            st.rerun()

    st.title("履歴")
    # 💡 誰のダッシュボードか分かりやすく表示
    st.markdown(f"**👤 {current_user}** さんの練習および配信の蓄積データ分析")

    # データの読み込み
    with sqlite3.connect("presentation_app.db", timeout=20.0) as conn:
        # 💡 修正：自分の履歴データだけを抽出するようにSQL文に WHERE を追加
        df_all = pd.read_sql(
            "SELECT * FROM practice_history WHERE username = ? ORDER BY id DESC", 
            conn, 
            params=(current_user,)
        )

    if df_all.empty:
        st.write("履歴はありません。")
    else:
        # 個人練習 (is_live != 1) と 本番配信 (is_live == 1) に分割
        df_practice = df_all[df_all["is_live"] != 1] if "is_live" in df_all.columns else df_all
        df_live = df_all[df_all["is_live"] == 1] if "is_live" in df_all.columns else pd.DataFrame()

        # タブで切り替え
        tab_practice, tab_live = st.tabs(["個人練習", "本番配信"])

        with tab_practice:
            if df_practice.empty:
                st.write("個人練習の記録はありません。")
            else:
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.markdown("#### 練習履歴")
                    display_df = df_practice[["date", "duration", "fillers"]].copy()
                    # 💡 秒数を「分:秒」に変換
                    display_df["duration"] = display_df["duration"].apply(format_duration)
                    display_df.columns = ["日付", "録音時間", "フィラー回数"]
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                    
                with col2:
                    st.markdown("#### フィラー回数の推移")
                    chart_data = df_practice.sort_values("id").set_index("date")[["fillers"]]
                    st.line_chart(chart_data)

        with tab_live:
            if df_live.empty:
                st.write("本番配信の記録はありません。")
            else:
                st.markdown("#### 本番配信履歴")
                display_live_df = df_live[["date", "slide_name", "duration", "fillers"]].copy()
                # 💡 秒数を「分:秒」に変換
                display_live_df["duration"] = display_live_df["duration"].apply(format_duration)
                display_live_df.columns = ["日付", "タイトル", "発表時間", "フィラー回数"]
                st.dataframe(display_live_df, use_container_width=True, hide_index=True)