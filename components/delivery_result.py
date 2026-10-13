import streamlit as st
import sqlite3
import datetime
import zoneinfo
import json
from collections import defaultdict, Counter
from my_utils.db_manager import get_all_reactions_for_result
DB_FILE = "presentation_app.db"

def render():
    # === 🌟 画面に一切何も表示せずにデータを保存する処理 ===
    if not st.session_state.get("result_data_saved", False):
        
        # 本番画面から引き継いだデータを回収（入力枠を通さず、直接セッションから拾います）
        last_sync_data = st.session_state.get("js_sync_live_delivery_page")
        if last_sync_data:
            try:
                l_data = json.loads(last_sync_data)
                st.session_state.stopwatch_seconds = l_data.get("time", 0)
                st.session_state.live_final_fillers = l_data.get("fillers", 0)
            except:
                pass
                
        # 💡 ユーザーのタイムゾーン設定を取得して正しい現在時刻を作成
        tz_str = st.session_state.get("timezone", "Asia/Tokyo")
        local_tz = zoneinfo.ZoneInfo(tz_str)
        current_time_str = datetime.datetime.now(local_tz).strftime("%Y-%m-%d %H:%M")

        # 💡 現在のユーザーを取得
        current_user = st.session_state.get("current_user", "default_user")

        # 画面を表示する前に、一瞬でデータベースへ保存
        with sqlite3.connect(DB_FILE, timeout=20.0) as conn:
            # 💡 修正：username カラムを含めてデータを保存
            conn.execute("""
                INSERT INTO practice_history (username, date, slide_name, duration, fillers, recorded, is_live) 
                VALUES (?, ?, ?, ?, ?, 0, 1)
            """, (
                current_user,
                current_time_str, 
                st.session_state.get("slide_name", "無題のプレゼン"), 
                st.session_state.get("stopwatch_seconds", 0), 
                st.session_state.get("live_final_fillers", 0)
            ))
        
        st.session_state.result_data_saved = True

    # ==========================================
    # ナビゲーション
    # ==========================================
    col_nav1, col_nav2 = st.columns(2)
    
    with col_nav1:
        if st.button("戻る", key="dr_nav_prev_top", use_container_width=True):
            st.session_state.pop("live_timeline", None)
            st.session_state.pop("result_data_saved", None)
            st.session_state.pop("js_sync_live_delivery_page", None)
            st.session_state.view = "delivery_live"
            st.rerun()
    with col_nav2:
        if st.button("ホーム", key="dr_nav_home_top", use_container_width=True):
            st.session_state.pop("live_timeline", None)
            st.session_state.pop("result_data_saved", None)
            st.session_state.pop("js_sync_live_delivery_page", None)
            st.session_state.view = "home"
            st.session_state.view_history = []
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.success("実戦本番シミュレーションが終了しました。お疲れ様でした。")

    # ルームIDを取得し、リアクションデータをDBから引っ張る
    room_id = st.session_state.get("booked_room", "Unknown")
    reactions = get_all_reactions_for_result(room_id)

    # リアクションを集計
    count_perf = sum(1 for r in reactions if "完璧" in r[1])
    count_good = sum(1 for r in reactions if "聞きやすい" in r[1])
    count_warn = sum(1 for r in reactions if "テンポ注意" in r[1])
    count_filler = sum(1 for r in reactions if "フィラー" in r[1])
    count_trouble = sum(1 for r in reactions if "見えない" in r[1] or "聞こえない" in r[1])
    
    # --- 画面上部のサマリー表示 ---
    st.markdown("### 最終スコア")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        m, s = divmod(st.session_state.get('stopwatch_seconds', 0), 60)
        col1.metric("発表タイム", f"{m:02d}:{s:02d}")
        col2.metric("不要語 (フィラー) 検出数", f"{st.session_state.get('live_final_fillers', 0)}回")

    # --- 審査員アバターからの総評 ---
    total_good = count_perf + count_good
    total_bad = count_warn + count_filler + count_trouble
    
    st.markdown("### 審査員からの総評")
    if total_good == 0 and total_bad == 0:
        judge_comment = "今回はリアクションが少なかったようですが、最後までやり切りましたね。お疲れ様でした。"
    elif total_good >= total_bad * 2:
        judge_comment = "素晴らしいプレゼンでした。聴衆も非常に聞きやすく、ポジティブな反応が多く寄せられています。自信を持ってください。"
    elif total_bad > total_good:
        judge_comment = "少し緊張してテンポが崩れたり、フィラーが多くなってしまったかもしれません。展開の詳細を見て、次回の改善点に繋げましょう。"
    else:
        judge_comment = "お疲れ様でした。良い点も課題点もバランスよく見つかりました。改善ポイントを復習すればさらに良くなります。"
        
    st.info(judge_comment)

    # --- 最も課題が多かったスライドの特定 ---
    warnings_per_slide = defaultdict(int)
    for slide_num, r_type, _ in reactions:
        if any(warn_word in r_type for warn_word in ["注意", "フィラー", "見えない", "聞こえない", "NG"]):
            warnings_per_slide[slide_num] += 1
            
    if warnings_per_slide:
        most_warned_slide = max(warnings_per_slide, key=warnings_per_slide.get)
        st.warning(f"**復習おすすめポイント**: スライド **{most_warned_slide}** でネガティブなリアクションやトラブルが最も多く発生しました。原稿のテンポや長さを確認してみましょう。")

    # --- 観客からの総リアクション ---
    st.markdown("### 観客から届いた総リアクション")
    with st.container(border=True):
        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
        col_r1.metric("完璧！", f"{count_perf}回")
        col_r2.metric("聞きやすい", f"{count_good}回")
        col_r3.metric("テンポ注意", f"{count_warn}回")
        col_r4.metric("フィラー過多", f"{count_filler}回")

    # --- スライドごとの詳細なリアクション内訳 ---
    with st.expander("スライドごとの詳細なリアクション内訳をみる"):
        if reactions:
            slide_summary = defaultdict(Counter)
            for slide_num, r_type, _ in reactions:
                slide_summary[slide_num][r_type] += 1
            
            for slide_num in sorted(slide_summary.keys()):
                st.markdown(f"**スライド {slide_num}**")
                
                reaction_texts = []
                for r_type, count in slide_summary[slide_num].items():
                    reaction_texts.append(f"{r_type}: **{count}**回")
                
                st.markdown(" ｜ ".join(reaction_texts))
                st.markdown("<hr style='margin: 10px 0px; border-top: 1px dashed #e2e8f0;'>", unsafe_allow_html=True)
        else: 
            st.write("リアクションデータがありません。")

    st.write("---")
    if st.button("過去の全履歴・分析データを確認する", key="res_dashboard", type="primary", use_container_width=True):
        st.session_state.pop("live_timeline", None)
        st.session_state.pop("result_data_saved", None)
        st.session_state.pop("js_sync_live_delivery_page", None)
        st.session_state.view = "dashboard"
        st.rerun()