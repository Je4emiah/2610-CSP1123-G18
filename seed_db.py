# This is a data insertion program, use with caution, only for data-related testing!

import sqlite3
import random
from datetime import datetime, timedelta

def seed_dev_user():
    # Using the path from your error log
    db_path = "mindmetric.db"
    
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()

        # Ensure the table matches your insert statement
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                q1 TEXT,
                q2 TEXT,
                q3 TEXT
            )
        ''')

        # Create mood_logs if missing
        cur.execute('''
            CREATE TABLE IF NOT EXISTS mood_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                mood_score INTEGER,
                thought_text TEXT,
                timestamp DATETIME
            )
        ''')

        # Insert Dev123
        cur.execute('''
            INSERT OR IGNORE INTO users (username, password, q1, q2, q3)
            VALUES (?, ?, ?, ?, ?)
        ''', ('Dev123', '112233', 'a', 'b', 'c'))

        print("Planting 365 days of moods for Dev123...")
        start_date = datetime.now() - timedelta(days=365)

        for i in range(366):
            current_date = start_date + timedelta(days=i)
            timestamp = current_date.strftime('%Y-%m-%d %H:%M:%S')
            mood_score = random.randint(1, 5)
            
            cur.execute('''
                INSERT INTO mood_logs (username, mood_score, thought_text, timestamp)
                VALUES (?, ?, ?, ?)
            ''', ('Dev123', mood_score, f"Testing day {i}", timestamp))

        conn.commit()
        print("Success! Database re-aligned and seeded.")

if __name__ == "__main__":
    seed_dev_user()