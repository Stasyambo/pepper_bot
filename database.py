import sqlite3
import json
from datetime import datetime, timedelta  # Добавляем импорт timedelta

def init_db():
    conn = sqlite3.connect('pepper.db')
    cur = conn.cursor()
    # Таблица для пользователей
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            keywords TEXT
        )
    ''')
    # Таблица для отслеживания отправленных сделок
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sent_deals (
            deal_id TEXT PRIMARY KEY,
            deal_data TEXT,
            sent_time TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('pepper.db')
    cur = conn.cursor()
    # Добавляем пользователя, если его еще нет. keywords пока пустая строка.
    cur.execute('INSERT OR IGNORE INTO users (user_id, keywords) VALUES (?, ?)', (user_id, ''))
    conn.commit()
    conn.close()

def update_user_keywords(user_id, new_keywords):
    conn = sqlite3.connect('pepper.db')
    cur = conn.cursor()
    cur.execute('UPDATE users SET keywords = ? WHERE user_id = ?', (new_keywords, user_id))
    conn.commit()
    conn.close()

def get_user_keywords(user_id):
    conn = sqlite3.connect('pepper.db')
    cur = conn.cursor()
    cur.execute('SELECT keywords FROM users WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else ''

def get_all_subscriptions():
    """Получаем всех пользователей и их ключевые слова для рассылки"""
    conn = sqlite3.connect('pepper.db')
    cur = conn.cursor()
    cur.execute('SELECT user_id, keywords FROM users WHERE keywords != ""')
    result = cur.fetchall()
    conn.close()
    # Возвращаем словарь: {user_id: keywords, ...}
    return {row[0]: row[1] for row in result}

def add_sent_deal(deal_id, deal_data):
    """Добавляет сделку в список отправленных"""
    conn = sqlite3.connect('pepper.db')
    cur = conn.cursor()
    cur.execute(
        'INSERT OR REPLACE INTO sent_deals (deal_id, deal_data, sent_time) VALUES (?, ?, ?)',
        (deal_id, json.dumps(deal_data), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_sent_deal(deal_id):
    """Проверяет, была ли сделка уже отправлена"""
    conn = sqlite3.connect('pepper.db')
    cur = conn.cursor()
    cur.execute('SELECT deal_data FROM sent_deals WHERE deal_id = ?', (deal_id,))
    result = cur.fetchone()
    conn.close()
    return json.loads(result[0]) if result else None

def get_all_sent_deal_ids():
    """Возвращает ID всех отправленных сделок"""
    conn = sqlite3.connect('pepper.db')
    cur = conn.cursor()
    cur.execute('SELECT deal_id FROM sent_deals')
    result = [row[0] for row in cur.fetchall()]
    conn.close()
    return result

def cleanup_old_deals(days=7):
    """Очищает старые сделки (старше указанного количества дней)"""
    conn = sqlite3.connect('pepper.db')
    cur = conn.cursor()
    old_time = (datetime.now() - timedelta(days=days)).isoformat()
    cur.execute('DELETE FROM sent_deals WHERE sent_time < ?', (old_time,))
    deleted_count = cur.rowcount
    conn.commit()
    conn.close()
    print(f"Очищено {deleted_count} старых сделок")
