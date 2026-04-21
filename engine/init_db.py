import sqlite3

def init_sqlite_db():
    # This creates the database file 'mindmetric.db'
    conn = sqlite3.connect('mindmetric.db')
    print("Opened database successfully")

    # Create the table for mood logs
    conn.execute('''
        CREATE TABLE IF NOT EXISTS mood_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            mood_score INTEGER NOT NULL, -- 1 (Sad) to 5 (Happy)
            thought_text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("Table created successfully")
    conn.close()

if __name__ == "__main__":
    init_sqlite_db()
