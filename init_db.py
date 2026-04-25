import sqlite3

def init_db():
    with sqlite3.connect('mindmetric.db') as conn:
        # 1. Create mood_logs (The Data Table)
        conn.execute('''CREATE TABLE IF NOT EXISTS mood_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            mood_score INTEGER NOT NULL,
            thought_text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # 2. Create users (The Identity Table)
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )''')
    print("Database synced and ready!")

if __name__ == "__main__":
    init_db()