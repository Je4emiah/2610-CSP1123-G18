import sqlite3
import random
from datetime import datetime, timedelta

DATABASE = 'mindmetric.db'
USERNAME = 'Dev123'

# Sample daily activities for the "thought_text" field
activities = [
    "Dapped up a friend at MMU", 
    "Finished a tough Calculus integration", 
    "Grinded some Magic Survival meta", 
    "Worked on the Analog Horror script", 
    "Had a great nasi lemak for lunch",
    "Struggled with C++ pointers for a bit",
    "Planned the exchange trip to Hof University",
    "Voice tuning sounded clean today",
    "Feeling a bit tired from the Cyberjaya heat",
    "Debugging Flask routes is finally paying off"
]

def seed_data():
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()

    print(f"🌱 Seeding 90 days of mood data for user: {USERNAME}...")

    # Clear existing logs for a fresh start
    cursor.execute("DELETE FROM mood_logs WHERE username = ?", (USERNAME,))

    # Start from 90 days ago
    start_date = datetime.now() - timedelta(days=90)

    for i in range(91):
        # Generate 1-2 entries per day for realism
        for _ in range(random.randint(1, 2)):
            current_time = start_date + timedelta(days=i, hours=random.randint(0, 23))
            timestamp = current_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Create a "trend" - slightly higher moods recently
            if i > 70:
                score = random.choices([4, 5, 3], weights=[50, 30, 20])[0]
            else:
                score = random.randint(2, 5)

            thought = random.choice(activities)
            
            cursor.execute('''
                INSERT INTO mood_logs (username, mood_score, thought_text, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (USERNAME, score, thought, timestamp))

    db.commit()
    db.close()
    print("✅ Database stimulated! Refresh your 'All' view to see the trends.")

if __name__ == '__main__':
    seed_data()