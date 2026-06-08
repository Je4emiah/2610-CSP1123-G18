import sqlite3
from datetime import datetime

DATABASE = 'mindmetric.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def insert_entry(user_id, rating, note):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO entries (user_id, rating, note) VALUES (?, ?, ?)",
        (user_id, rating, note)
    )
    conn.commit()
    conn.close()

def get_user_entries(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Fetch entries sorted by date so the trend visualization reads left-to-right correctly
    cursor.execute(
        "SELECT rating, note, created_at FROM entries WHERE user_id = ? ORDER BY created_at ASC",
        (user_id,)
    )
    entries = cursor.fetchall()
    conn.close()
    return entries