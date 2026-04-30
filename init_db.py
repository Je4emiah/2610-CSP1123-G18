import sqlite3

def init_db():
    with sqlite3.connect('mindmetric.db') as conn:
        # 1. Mood Logs Table
        conn.execute('''CREATE TABLE IF NOT EXISTS mood_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            mood_score INTEGER NOT NULL,
            thought_text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # 2. Updated Users Table with Security Questions
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            q1_answer TEXT,
            q2_answer TEXT,
            q3_answer TEXT
        )''')
    print("Database refreshed and ready with Security Questions!")

if __name__ == "__main__":
    init_db()