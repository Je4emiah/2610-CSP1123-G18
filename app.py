import sqlite3
from flask import Flask, render_template, request, url_for, redirect, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'mmu_project_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# --- DATABASE HELPERS (Put them here) ---

def save_mood_entry(username, score, thought):
    try:
        with sqlite3.connect('mindmetric.db') as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO mood_logs (username, mood_score, thought_text) VALUES (?, ?, ?)",
                (username, score, thought)
            )
            conn.commit()
            return True
    except Exception as e:
        print(f"Database error: {e}")
        return False

def get_mood_trends(username):
    with sqlite3.connect('mindmetric.db') as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT date(timestamp), AVG(mood_score) 
            FROM mood_logs 
            WHERE username = ? 
            GROUP BY date(timestamp)
            ORDER BY date(timestamp) ASC
        ''', (username,))
        rows = cur.fetchall()
        return {
            "labels": [row[0] for row in rows],
            "data": [row[1] for row in rows]
        }

# --- ROUTES (The bridges between HTML and Python) ---
@app.context_processor
def inject_user():
    # This pulls the username from the session and 
    # makes 'current_user' available to ALL HTML files
    return dict(current_user=session.get('user_id'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        with sqlite3.connect('mindmetric.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
            user = cur.fetchone()

        # Check password and move on - NO loops here
        if user and check_password_hash(user[0], password):
            session['user_id'] = username
            return redirect(url_for('dashboard')) # Go straight to dashboard
        else:
            return "Invalid username or password", 401
            
    # If it's a GET request, just show the page
    return render_template('login.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        username = request.form.get('username')
        new_password = request.form.get('new_password')
        hashed_pw = generate_password_hash(new_password)
        
        with sqlite3.connect('mindmetric.db') as conn:
            cur = conn.cursor()
            # This updates the password for the existing user
            cur.execute("UPDATE users SET password_hash = ? WHERE username = ?", (hashed_pw, username))
            conn.commit()
        return redirect(url_for('login'))
    return render_template('reset_password.html')

@app.route('/logout')
def logout():
    session.clear() # Deletes all session data when user logs out
    return redirect(url_for('login'))

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    username = session['user_id']
    try:
        with sqlite3.connect('mindmetric.db') as conn:
            cur = conn.cursor()
            # 1. Clear their logs first
            cur.execute("DELETE FROM mood_logs WHERE username = ?", (username,))
            # 2. Delete the user profile
            cur.execute("DELETE FROM users WHERE username = ?", (username,))
            conn.commit()
        
        session.clear() # Log them out after deleting
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error deleting account: {e}")
        return "Error deleting account", 500

@app.route('/register.html', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            return "Passwords do not match!", 400
        
        # 1. Hash the password
        hashed_pw = generate_password_hash(password)
        
        try:
            with sqlite3.connect('mindmetric.db') as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed_pw))
                conn.commit()
            return redirect(url_for('login')) # If success then go to login
        except sqlite3.IntegrityError:
            return "Username already exists!", 400
                
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    # Check if the user is actually logged in via session
    if 'user_id' not in session:
        return redirect(url_for('login')), 302
        
    return render_template('dashboard.html')

@app.route('/api/log_mood', methods=['POST'])
def log_mood_route():
    data = request.json
    success = save_mood_entry(
        data.get('username'), 
        data.get('mood_score'), 
        data.get('thought_text')
    )
    return jsonify({"status": "success" if success else "error"})

@app.route('/api/mood_data/<username>')
def mood_data_route(username):
    # This sends the trends directly to Chart.js
    trends = get_mood_trends(username)
    return jsonify(trends)

def init_db():
    with sqlite3.connect('mindmetric.db') as conn:
        # Create mood_logs
        conn.execute('''CREATE TABLE IF NOT EXISTS mood_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            mood_score INTEGER NOT NULL,
            thought_text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Create users
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )''')
    print("Database refreshed and ready!")

if __name__ == '__main__':
    init_db()
    app.run(debug=True)