import requests
import streamlit as st

def call_gemini_api(prompt, system_instruction=""):
    """Gemini APIを呼び出してテキストを生成する"""
    if st.session_state.get("secure_mode", False):
        return "🔒 完全機密モードがオンのため、外部AI通信は遮断されています。"
        
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key: return "⚠️ APIキーが未設定です。"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    if system_instruction: 
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        
    try:
        response = requests.post(url, json=payload, timeout=15)
        
        # 💡 503エラー（混雑時）の場合の専用メッセージ
        if response.status_code == 503:
            return "⚠️️ ただいまAIサーバーが大変混み合っています。恐れ入りますが、少し時間をおいてもう一度お試しください。"
            
        if response.status_code == 200: 
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        else:
            return f"❌ APIエラー: {response.status_code} - {response.text}"
    except Exception as e:
        return f"❌ 通信エラーが発生しました: {str(e)}"