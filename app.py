import sqlite3
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# --- DATABASE HELPERS (Put them here) ---

def save_mood_entry(student_id, score, thought):
    try:
        with sqlite3.connect('mindmetric.db') as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO mood_logs (student_id, mood_score, thought_text) VALUES (?, ?, ?)",
                (student_id, score, thought)
            )
            conn.commit()
            return True
    except Exception as e:
        print(f"Database error: {e}")
        return False

def get_mood_trends(student_id):
    with sqlite3.connect('mindmetric.db') as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT date(timestamp), AVG(mood_score) 
            FROM mood_logs 
            WHERE student_id = ? 
            GROUP BY date(timestamp)
            ORDER BY date(timestamp) ASC
        ''', (student_id,))
        rows = cur.fetchall()
        return {
            "labels": [row[0] for row in rows],
            "data": [row[1] for row in rows]
        }

# --- ROUTES (The bridges between HTML and Python) ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/log_mood', methods=['POST'])
def log_mood_route():
    data = request.json
    success = save_mood_entry(
        data.get('student_id'), 
        data.get('mood_score'), 
        data.get('thought_text')
    )
    return jsonify({"status": "success" if success else "error"})

@app.route('/api/mood_data/<student_id>')
def mood_data_route(student_id):
    # This sends the trends directly to Chart.js
    trends = get_mood_trends(student_id)
    return jsonify(trends)

def init_db():
    with sqlite3.connect('mindmetric.db') as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS mood_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                mood_score INTEGER NOT NULL,
                thought_text TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    print("Database initialized!")

if __name__ == '__main__':
    init_db()
    app.run(debug=True)