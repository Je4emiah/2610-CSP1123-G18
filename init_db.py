import sqlite3

# 23 Aprl 21:29 UPDATE: New User Table for Security
def init_db():
    with sqlite3.connect('mindmetric.db') as conn:
    # Existing Mood Table
        conn.execute('''CREATE TABLE IF NOT EXISTS mood_logs (...)''')
    
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTERGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
    print("Databse initialized with User Table.")

if __name__ == "__main__":
    init_db()