# database.py - Робота з базою даних

import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

def init_db():
    """Створює таблиці в базі даних"""
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        chat_id INTEGER PRIMARY KEY,
        city TEXT DEFAULT 'Жмеринка',
        queue TEXT,
        notify INTEGER DEFAULT 1
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS outages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        queue TEXT,
        time_ranges TEXT,
        last_updated TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        queue TEXT,
        old_schedule TEXT,
        new_schedule TEXT,
        changed_at TEXT
    )
    """)
    
    conn.commit()
    print("✅ База даних ініціалізована")

def save_user(chat_id, city="Жмеринка", queue=None, notify=1):
    """Зберігає або оновлює дані користувача"""
    cursor.execute("""
    INSERT OR REPLACE INTO users (chat_id, city, queue, notify)
    VALUES (?, ?, ?, ?)
    """, (chat_id, city, queue, notify))
    conn.commit()

def get_user(chat_id):
    """Отримує дані користувача"""
    cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
    return cursor.fetchone()

def update_user_queue(chat_id, queue):
    """Оновлює чергу користувача"""
    cursor.execute("UPDATE users SET queue = ? WHERE chat_id = ?", (queue, chat_id))
    conn.commit()

def update_user_notify(chat_id, notify):
    """Увімкнути/вимкнути сповіщення"""
    cursor.execute("UPDATE users SET notify = ? WHERE chat_id = ?", (notify, chat_id))
    conn.commit()

def save_schedule(date, queue, time_ranges):
    """Зберігає графік відключень"""
    time_ranges_json = json.dumps(time_ranges, ensure_ascii=False)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
    SELECT time_ranges FROM outages 
    WHERE date = ? AND queue = ?
    """, (date, queue))
    
    old = cursor.fetchone()
    
    if old:
        if old[0] != time_ranges_json:
            cursor.execute("""
            INSERT INTO history (date, queue, old_schedule, new_schedule, changed_at)
            VALUES (?, ?, ?, ?, ?)
            """, (date, queue, old[0], time_ranges_json, now))
            
            cursor.execute("""
            UPDATE outages 
            SET time_ranges = ?, last_updated = ?
            WHERE date = ? AND queue = ?
            """, (time_ranges_json, now, date, queue))
            print(f"📝 Оновлено графік для черги {queue} на {date}")
    else:
        cursor.execute("""
        INSERT INTO outages (date, queue, time_ranges, last_updated)
        VALUES (?, ?, ?, ?)
        """, (date, queue, time_ranges_json, now))
        print(f"➕ Додано новий графік для черги {queue} на {date}")
    
    conn.commit()

def get_schedule(date, queue):
    """Отримує графік на певну дату для певної черги"""
    cursor.execute("""
    SELECT time_ranges FROM outages 
    WHERE date = ? AND queue = ?
    """, (date, queue))
    
    result = cursor.fetchone()
    if result:
        return json.loads(result[0])
    return None

def get_all_users_by_queue(queue):
    """Отримує всіх користувачів певної черги"""
    cursor.execute("""
    SELECT chat_id FROM users 
    WHERE queue = ? AND notify = 1
    """, (queue,))
    return [row[0] for row in cursor.fetchall()]

def get_recent_changes(limit=10):
    """Отримує останні зміни графіків"""
    cursor.execute("""
    SELECT * FROM history 
    ORDER BY changed_at DESC 
    LIMIT ?
    """, (limit,))
    return cursor.fetchall()