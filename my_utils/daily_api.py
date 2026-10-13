import requests
import streamlit as st
import time

def create_daily_room():
    """
    Daily.coのAPIを叩いて、新しい音声配信ルーム（URL）を自動作成する関数
    """
    # secrets.tomlからAPIキーを取得
    api_key = st.secrets.get("DAILY_API_KEY")
    if not api_key:
        st.error("APIキーが設定されていません。.streamlit/secrets.tomlを確認してください。")
        return None

    url = "https://api.daily.co/v1/rooms"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
# ルームの設定（カメラオフ、画面共有オフにして音声とデータだけを軽く飛ばす設定）
    payload = {
        "properties": {
            "start_video_off": True,      # 💡 修正: 最初からカメラをオフにする
            "enable_screenshare": False,  # 画面共有機能を使わない
            "exp": int(time.time()) + 86400 # 24時間後に消滅
        }
    }    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status() # エラーがあればここでキャッチ
        data = response.json()
        
        # 作成されたルームのURLを返す（例: https://presen-app.daily.co/xyz123）
        return data.get("url")
    except Exception as e:
        st.error(f"音声ルームの作成に失敗しました: {e}")
        return None