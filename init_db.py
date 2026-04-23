import sqlite3

def init_db():
    with sqlite3.connect('mindmetric.db') as conn:
    # This creates the database file 'mindmetric.db' to prevent crashs
    conn.execute('''CREATE TABLE IF NOT EXISTS mood_logs (...)''')
    
    # 23 Aprl 21:29 NEW: User Table for Security
    conn.execute('''
                 CREATE TABLE IF NOT EXISTS users (
                     id INTERGER PRIMARY KEY AUTOINCREMENT,
                     username TEXT UNIQUE NOT NULL,
                     password_hash TEXT NOT NULL
                 )
    ''')

if __name__ == "__main__":
    init_sqlite_db()