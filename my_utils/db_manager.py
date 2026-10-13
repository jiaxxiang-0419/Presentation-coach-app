import datetime
import sqlite3
import json
import secrets
import hashlib
from functools import lru_cache
import zoneinfo
import streamlit as st

DB_FILE = "presentation_app.db"

@lru_cache(maxsize=1)
def get_db():
    # 💡 タイムアウトを20秒に延長し、同時読み書きを可能にする「WALモード」を有効化
    conn = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def _add_column_if_not_exists(cursor, table_name, column_name, column_definition):
    try:
        cursor.execute(f"SELECT {column_name} FROM {table_name} LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # 💡 1. ユーザー認証用テーブルの作成
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS practice_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL DEFAULT 'default_user',
            date TEXT,
            slide_name TEXT,
            duration INTEGER,
            fillers INTEGER DEFAULT 0,
            recorded INTEGER,
            is_live INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS live_reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT,
            reaction_type TEXT,
            slide_num INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS slide_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL DEFAULT 'default_user',
            title TEXT,
            notes_json TEXT,
            file_bytes BLOB
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_lives (
            room_id TEXT PRIMARY KEY,
            slide_title TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            current_slide INTEGER DEFAULT 0,
            slide_id INTEGER,
            token TEXT,
            target_minutes INTEGER DEFAULT 5,
            avatars_json TEXT,
            is_secure INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id TEXT PRIMARY KEY,
            status TEXT DEFAULT 'free',
            booked_time TEXT,
            room_token TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS room_bookings (
            room_token TEXT PRIMARY KEY,
            room_id TEXT,
            booked_date TEXT,
            booked_time TEXT,
            slide_title TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS live_slide_mapping (
            room_id TEXT PRIMARY KEY,
            slide_id INTEGER
        )
    """)
    
    cursor.execute("SELECT count(*) FROM room_bookings")
    if cursor.fetchone()[0] == 0:
        try:
            cursor.execute("SELECT id, booked_time, room_token, slide_title, booked_date FROM rooms WHERE status = 'booked' AND room_token IS NOT NULL")
            old_bookings = cursor.fetchall()
            for ob in old_bookings:
                cursor.execute("INSERT OR IGNORE INTO room_bookings (room_id, booked_time, room_token, slide_title, booked_date) VALUES (?, ?, ?, ?, ?)", (ob[0], ob[1], ob[2], ob[3], ob[4]))
            cursor.execute("UPDATE rooms SET status = 'free', booked_time = NULL, room_token = NULL, slide_title = NULL, booked_date = NULL")
        except:
            pass

    for r in ["A", "B", "C"]:
        cursor.execute("INSERT OR IGNORE INTO rooms (id, status) VALUES (?, 'free')", (r,))
    
    _add_column_if_not_exists(cursor, "rooms", "room_token", "TEXT")
    _add_column_if_not_exists(cursor, "active_lives", "avatars_json", "TEXT")
    _add_column_if_not_exists(cursor, "active_lives", "current_slide", "INTEGER DEFAULT 0")
    _add_column_if_not_exists(cursor, "active_lives", "slide_id", "INTEGER")
    _add_column_if_not_exists(cursor, "active_lives", "token", "TEXT")
    _add_column_if_not_exists(cursor, "active_lives", "target_minutes", "INTEGER DEFAULT 5")
    _add_column_if_not_exists(cursor, "active_lives", "is_secure", "INTEGER DEFAULT 0")    
    _add_column_if_not_exists(cursor, "practice_history", "fillers", "INTEGER DEFAULT 0")
    _add_column_if_not_exists(cursor, "practice_history", "is_live", "INTEGER DEFAULT 0")
    _add_column_if_not_exists(cursor, "practice_history", "username", "TEXT DEFAULT 'default_user'")
    _add_column_if_not_exists(cursor, "rooms", "slide_title", "TEXT DEFAULT '予約済'")
    _add_column_if_not_exists(cursor, "rooms", "booked_date", "TEXT")
    _add_column_if_not_exists(cursor, "slide_assets", "username", "TEXT DEFAULT 'default_user'")
    conn.commit()


# ==========================================
# 認証・ユーザー管理用関数（新規追加）
# ==========================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username.strip(), hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # すでに存在するユーザー名

def verify_user(username, password):
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username.strip(),))
    row = cursor.fetchone()
    if row and row[0] == hash_password(password):
        return True
    return False


# ==========================================
# ルーム管理用関数
# ==========================================
def get_room_by_token(token):
    init_db()
    cursor = get_db().cursor()
    cursor.execute("SELECT room_id, 'booked', booked_time, room_token, booked_date FROM room_bookings WHERE room_token = ?", (token,))
    return cursor.fetchone()

def update_room_status(room_id, status, booked_time=None):
    pass

def set_room_token(room_id, token):
    pass

def get_room_status():
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT room_id, 'booked', booked_time, room_token, slide_title, booked_date FROM room_bookings ORDER BY booked_date, booked_time")
    return cursor.fetchall()

def book_room_with_token(room_id, booked_time, slide_title=None, booked_date=None, edit_token=None):
    init_db()
    import uuid
    conn = get_db()
    cursor = conn.cursor()
    
    if edit_token:
        room_token = edit_token
        cursor.execute("""
            UPDATE room_bookings 
            SET room_id = ?, booked_time = ?, slide_title = ?, booked_date = ?
            WHERE room_token = ?
        """, (str(room_id), booked_time, slide_title, booked_date, room_token))
    else:
        room_token = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO room_bookings (room_token, room_id, booked_date, booked_time, slide_title)
            VALUES (?, ?, ?, ?, ?)
        """, (room_token, str(room_id), booked_date, booked_time, slide_title))
        
    conn.commit()
    return room_token

def cancel_booking(identifier):
    if not identifier: return
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM room_bookings WHERE room_token = ?", (str(identifier),))
    if cursor.rowcount == 0:
        cursor.execute("SELECT token FROM active_lives WHERE room_id = ?", (str(identifier),))
        row = cursor.fetchone()
        if row and row[0]:
            cursor.execute("DELETE FROM room_bookings WHERE room_token = ?", (row[0],))
    conn.commit()

def release_room(room_token):
    cancel_booking(room_token)

def get_combined_calendar_events(username="default_user"):
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    
    # 💡 誰が予約したかを判別するため、ユーザーが関連付けられている可能性がある情報で絞り込む
    # 現在のテーブル構造では room_bookings に直接 username はないため、
    # 一旦全ての予約を取得し、後で「そのユーザーが持っているスライドのタイトル」と一致するかどうかで
    # 簡易的に「自分の予約」とみなす処理を行います。（※より厳密にするにはテーブルにusername追加が必要ですが、現状の構造でのベストエフォートです）
    
    cursor.execute("SELECT title FROM slide_assets WHERE username = ?", (username,))
    my_slide_titles = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT room_id, booked_time, slide_title, booked_date, room_token FROM room_bookings")
    rows = cursor.fetchall()
    
    events = []
    import datetime
    
    for r_id, b_time, s_title, b_date, r_token in rows:
        title = s_title if s_title else "名称未設定"
        
        # 💡 他人の予約はカレンダーに一切追加しない！（スキップする）
        if title not in my_slide_titles and title != "名称未設定":
            continue

        date_str = b_date if b_date else str(datetime.date.today())
        start_datetime = f"{date_str}T{b_time}:00"
        
        try:
            start_dt_obj = datetime.datetime.strptime(f"{date_str} {b_time}", "%Y-%m-%d %H:%M")
            end_dt_obj = start_dt_obj + datetime.timedelta(minutes=20)
            end_datetime = end_dt_obj.strftime("%Y-%m-%dT%H:%M:00")
        except:
            end_datetime = start_datetime
        
        events.append({
            "id": r_token,
            "title": f"ルーム{r_id}: {title}",
            "start": start_datetime,
            "end": end_datetime,
            "resourceId": str(r_id),
            "backgroundColor": "rgba(239, 68, 68, 0.85)", 
            "borderColor": "#dc2626",
            "textColor": "#ffffff"
        })
        
    try:
        # 過去の履歴の表示（practice_historyにはusernameカラムがあるため正確に絞り込み可能）
        cursor.execute("SELECT id, date, slide_name, duration FROM practice_history WHERE is_live = 1 AND username = ?", (username,))
        history_rows = cursor.fetchall()
        for h_id, h_date, h_title, h_dur in history_rows:
            title = h_title if h_title else "名称未設定"
            
            try:
                dt_obj = datetime.datetime.strptime(h_date, "%Y-%m-%d %H:%M:%S")
                start_datetime = dt_obj.strftime("%Y-%m-%dT%H:%M:00")
                dur_seconds = h_dur if h_dur else 1200
                end_dt_obj = dt_obj + datetime.timedelta(seconds=dur_seconds)
                end_datetime = end_dt_obj.strftime("%Y-%m-%dT%H:%M:00")
            except:
                start_datetime = str(h_date).replace(" ", "T")
                end_datetime = start_datetime
                
            events.append({
                "id": f"history_{h_id}",
                "title": f"[完了] {title}",
                "start": start_datetime,
                "end": end_datetime,
                "backgroundColor": "#94a3b8", 
                "borderColor": "#64748b",
                "textColor": "#ffffff"
            })
    except:
        pass
        
    return events

def get_all_bookings():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT date, slide_name FROM practice_history WHERE is_live = 1")
    rows = cursor.fetchall()
    events = []
    for row in rows:
        events.append({"title": row[1], "start": row[0], "end": row[0]})
    return events

def get_calendar_data_for_html(username="default_user"):
    return json.dumps(get_combined_calendar_events(username))

# ==========================================
# ライブ管理用関数
# ==========================================
# 💡 引数の最後に is_secure=0 を追加
def start_public_live(room_id, slide_title, slide_id=None, token=None, target_minutes=5, is_secure=0):
    conn = get_db()
    cursor = conn.cursor()
    
    room_id = str(room_id).strip().upper()
    cursor.execute("DELETE FROM active_lives WHERE room_id = ?", (room_id,))
    started_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    s_id_int = int(slide_id) if slide_id is not None and str(slide_id).isdigit() else None

    # 💡 VALUES の最後を 0 ではなく ? に変更し、is_secure を保存する
    cursor.execute("""
        INSERT INTO active_lives 
        (room_id, slide_title, started_at, current_slide, token, target_minutes, slide_id, is_secure) 
        VALUES (?, ?, ?, 0, ?, ?, ?, ?)
    """, (room_id, slide_title, started_at, token, target_minutes, s_id_int, int(is_secure)))
    
    if s_id_int is not None:
        cursor.execute("INSERT OR REPLACE INTO live_slide_mapping (room_id, slide_id) VALUES (?, ?)", (room_id, s_id_int))

    conn.commit()
    
def end_public_live(room_id):
    room_id = str(room_id).strip().upper()
    conn = get_db()
    conn.execute("DELETE FROM active_lives WHERE room_id = ?", (room_id,))
    conn.execute("DELETE FROM live_slide_mapping WHERE room_id = ?", (room_id,))
    conn.commit()

def get_all_active_lives():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT room_id, slide_title, started_at, target_minutes, token FROM active_lives WHERE is_secure = 0 ORDER BY started_at DESC")
    return cursor.fetchall()

def update_live_slide(room_id, slide_num):
    room_id = str(room_id).strip().upper()
    conn = get_db()
    conn.execute("UPDATE active_lives SET current_slide = ? WHERE room_id = ?", (slide_num, room_id))
    conn.commit()

def update_live_current_slide(room_id, slide_num):
    update_live_slide(room_id, slide_num)

def get_active_live_info(room_id):
    room_id = str(room_id).strip().upper()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT slide_title, current_slide, started_at, token, slide_id FROM active_lives WHERE room_id = ?", (room_id,))
    res = cursor.fetchone()
    return res

def cleanup_zombie_rooms(minutes=30):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT room_id FROM active_lives WHERE datetime(started_at, '+{minutes} minutes') < CURRENT_TIMESTAMP")
    zombies = cursor.fetchall()
    for (r_id,) in zombies:
        cursor.execute("DELETE FROM active_lives WHERE room_id = ?", (r_id,))
        cursor.execute("DELETE FROM live_slide_mapping WHERE room_id = ?", (r_id,))
    conn.commit()


# ==========================================
# 視聴者リアクション用関数
# ==========================================
def add_reaction(room_id, reaction_type, slide_num):
    room_id = str(room_id).strip().upper()
    conn = get_db()
    conn.execute("INSERT INTO live_reactions (room_id, reaction_type, slide_num) VALUES (?, ?, ?)", (room_id, reaction_type, slide_num))
    conn.commit()

def get_reactions_by_slide(room_id, slide_num):
    room_id = str(room_id).strip().upper()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT reaction_type, COUNT(*) FROM live_reactions WHERE room_id = ? AND slide_num = ? GROUP BY reaction_type", (room_id, slide_num))
    return cursor.fetchall()

def get_all_reactions_for_result(room_id):
    room_id = str(room_id).strip().upper()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT slide_num, reaction_type, created_at FROM live_reactions WHERE room_id = ? ORDER BY slide_num, created_at", (room_id,))
    return cursor.fetchall()


# ==========================================
# 資料管理用関数（ユーザーごとの隔離対応）
# ==========================================
def save_slide_to_db(username, title, file_bytes):
    conn = get_db()
    conn.execute("INSERT INTO slide_assets (username, title, file_bytes) VALUES (?, ?, ?)", (username, title, file_bytes))
    conn.commit()
    st.cache_data.clear()

def get_latest_slide(username="default_user"):
    cursor = get_db().cursor()
    cursor.execute("SELECT file_bytes FROM slide_assets WHERE username = ? ORDER BY id DESC LIMIT 1", (username,))
    row = cursor.fetchone()
    return row[0] if row else None

def get_all_slides(username="default_user"):
    cursor = get_db().cursor()
    cursor.execute("SELECT id, title FROM slide_assets WHERE username = ? ORDER BY id DESC", (username,))
    return cursor.fetchall()

def get_slide_by_id(slide_id, username="default_user"):
    if slide_id is None: return None
    cursor = get_db().cursor()
    try:
        s_id = int(slide_id)
    except:
        return None
    cursor.execute("SELECT file_bytes FROM slide_assets WHERE id = ? AND username = ?", (s_id, username))
    row = cursor.fetchone()
    return row[0] if row else None

def delete_slide_by_id(slide_id, username="default_user"):
    if slide_id is None: return
    try:
        s_id = int(slide_id)
    except ValueError:
        return
        
    conn = get_db()
    cursor = conn.cursor() # 💡 cursorを使って確実に実行する
    cursor.execute("DELETE FROM slide_assets WHERE id = ? AND username = ?", (s_id, username))
    conn.commit()
    st.cache_data.clear()

def get_slide_bytes_by_title(title, username="default_user"):
    cursor = get_db().cursor()
    cursor.execute("SELECT file_bytes FROM slide_assets WHERE title = ? AND username = ? ORDER BY id DESC LIMIT 1", (title, username))
    row = cursor.fetchone()
    return row[0] if row else None

def update_slide_notes_by_title(title, notes_text, username="default_user"):
    conn = get_db()
    conn.execute("UPDATE slide_assets SET notes_json = ? WHERE title = ? AND username = ?", (notes_text, title, username))
    conn.commit()
    st.cache_data.clear()

def rename_slide(old_title, new_title, username="default_user"):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM slide_assets WHERE title = ? AND username = ?", (new_title, username))
    if cursor.fetchone(): return False
    cursor.execute("UPDATE slide_assets SET title = ? WHERE title = ? AND username = ?", (new_title, old_title, username))
    conn.commit()
    st.cache_data.clear()
    return True


# ==========================================
# アバター同期用関数
# ==========================================
def update_live_avatars(room_id, avatars_list):
    room_id = str(room_id).strip().upper()
    conn = get_db()
    avatars_json = json.dumps(avatars_list, ensure_ascii=False)
    conn.execute("UPDATE active_lives SET avatars_json = ? WHERE room_id = ?", (avatars_json, room_id))
    conn.commit()

def get_live_avatars(room_id):
    room_id = str(room_id).strip().upper()
    cursor = get_db().cursor()
    cursor.execute("SELECT avatars_json FROM active_lives WHERE room_id = ?", (room_id,))
    row = cursor.fetchone()
    if row and row[0]:
        try:
            return json.loads(row[0])
        except:
            pass
    return None