import sqlite3
import random
from datetime import datetime, timedelta

DATABASE = 'mindmetric.db'
# This matches your active session key 'user_id' from app.py
USERNAME_TO_SEED = 'Dev123'  

def seed_past_year_data():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Ensure the mood_logs table exists so we don't crash on an empty database file
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mood_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            mood_score INTEGER NOT NULL,
            thought_text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    print(f"Generating 365 days of localized telemetry logs for '{USERNAME_TO_SEED}'...")
    
    sample_thoughts = {
        5: ["Excellent productivity today, felt highly organized.", "Fantastic workout session, energy levels are peaked.", "Project milestones hitting on time, clear headspace."],
        4: ["Had a good conversation with the team.", "Steady day, task completion rate was solid.", "Relaxing evening, caught up on some rest."],
        3: ["Routine day. Nothing special to note.", "Standard workflow progression.", "Balanced energy, holding steady baseline."],
        2: ["Felt slightly burnt out during the afternoon shift.", "Rest was cut short, running on low reserves today.", "A bit distracted, struggling to find structural rhythm."],
        1: ["High pressure load today, feeling completely exhausted.", "Operational blockages causing heavy friction.", "Needed an intentional break, closing down all loops early."]
    }

    now = datetime.now()
    inserted_count = 0

    # Loop backward day by day for a full year
    for day_offset in range(365):
        target_date = now - timedelta(days=day_offset)
        formatted_timestamp = target_date.strftime('%Y-%m-%d %H:%M:%S')
        
        # Pull a random score distribution
        mood_score = random.choices([1, 2, 3, 4, 5], weights=[5, 15, 30, 35, 15])[0]
        thought_text = random.choice(sample_thoughts[mood_score])
        
        cursor.execute('''
            INSERT INTO mood_logs (username, mood_score, thought_text, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (USERNAME_TO_SEED, mood_score, thought_text, formatted_timestamp))
        
        inserted_count += 1

    conn.commit()
    conn.close()
    print(f"Success! Successfully injected {inserted_count} historical rows into 'mood_logs'.")

if __name__ == '__main__':
    seed_past_year_data()