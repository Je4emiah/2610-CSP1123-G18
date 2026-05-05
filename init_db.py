import sqlite3

# 23 Aprl 21:29 UPDATE: New User Table for Security
def init_db():
    with sqlite3.connect('mindmetric.db') as conn:
    # Existing Mood Table
        conn.execute('''CREATE TABLE IF NOT EXISTS mood_logs (...)''')
    
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
    print("Databse initialized with User Table.")

if __name__ == "__main__":
    init_db()

# Update init_db() or add a migration
def add_display_name_column():
    with sqlite3.connect('mindmetric.db') as conn:
        try:
            conn.execute('ALTER TABLE users ADD COLUMN display_name TEXT')
            print("Added display_name column")
        except sqlite3.OperationalError:
            pass  # Column already exists