import fitz
from PIL import Image
import requests
import streamlit as st
import sqlite3
import base64

# --- 1. 定数設定 ---
DB_FILE = "presentation_app.db"

# --- 2. 画像化関数 ---
def get_pdf_page_image(pdf_bytes, page_num):
    """PDFの指定ページを画像に変換する関数"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(page_num)
    pix = page.get_pixmap()
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

# --- 3. Gemini API呼び出し関数（★音声データ対応版にパワーアップ） ---
def call_gemini_api(prompt, system_instruction="", audio_bytes=None):
    api_key = st.secrets.get("GEMINI_API_KEY")
    model_name = "models/gemini-2.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
    
    # 基本のテキストパーツを作成
    parts = [{"text": prompt}]
    
    # 🎤 音声データが渡された場合、base64に変換してパーツに追加
    if audio_bytes:
        encoded_audio = base64.b64encode(audio_bytes).decode("utf-8")
        parts.append({
            "inlineData": {
                "mimeType": "audio/wav",  # 録音データの形式
                "data": encoded_audio
            }
        })
    
    # 最新のAPI仕様に合わせた payload 構造
    payload = {
        "contents": [{"parts": parts}]
    }
    
    # system_instruction がある場合は追加
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    try:
        response = requests.post(url, json=payload, timeout=180) # 音声処理のためタイムアウトを少し長めに
        
        if response.status_code != 200:
            return f"❌ APIエラー: {response.status_code} - {response.text}"
            
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"❌ 通信エラー: {str(e)}"


# --- 4. データベース初期化関数 ---
def init_db():
    """データベースの初期化およびカラムの自動追加"""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS practice_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            slide_name TEXT,
            duration INTEGER,
            fillers INTEGER,
            recorded INTEGER,
            is_live INTEGER DEFAULT 0
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS slide_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            notes_json TEXT,
            file_bytes BLOB
        )
        """)
        try: cursor.execute("SELECT fillers FROM practice_history LIMIT 1")
        except sqlite3.OperationalError: cursor.execute("ALTER TABLE practice_history ADD COLUMN fillers INTEGER DEFAULT 0")
        try: cursor.execute("SELECT is_live FROM practice_history LIMIT 1")
        except sqlite3.OperationalError: cursor.execute("ALTER TABLE practice_history ADD COLUMN is_live INTEGER DEFAULT 0")
        conn.commit()

def list_available_models(api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    response = requests.get(url)
    return response.json()