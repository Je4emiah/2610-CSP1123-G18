import sqlite3
from flask import Flask, render_template, request, url_for, redirect, jsonify, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'mmu_project_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# --- DATABASE HELPERS ---

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

# --- CONTEXT PROCESSOR ---
@app.context_processor
def inject_user():
    return dict(current_user=session.get('user_id'))

# --- ROUTES ---

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

        if user and check_password_hash(user[0], password):
            session['user_id'] = username
            return redirect(url_for('dashboard'))
        else:
            return "Invalid username or password", 401
            
    return render_template('login.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username')
        a1 = request.form.get('q1', '').lower().strip()
        a2 = request.form.get('q2', '').lower().strip()
        a3 = request.form.get('q3', '').lower().strip()
        
        with sqlite3.connect('mindmetric.db') as conn:
            conn.row_factory = sqlite3.Row
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        # Security Verification
        if user and user['q1_answer'] == a1 and user['q2_answer'] == a2 and user['q3_answer'] == a3:
            return render_template('forgot_password.html', user_found=True, username=username)
        else:
            flash("Incorrect answers or username not found.", "danger")
            return redirect(url_for('forgot_password'))
            
    return render_template('forgot_password.html', user_found=False)

@app.route('/reset_password', methods=['POST'])
def reset_password():
    username = request.form.get('username')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if new_password != confirm_password:
        return "Passwords do not match! <a href='/forgot_password'>Try again</a>"

    hashed_pw = generate_password_hash(new_password)

    with sqlite3.connect('mindmetric.db') as conn:
        conn.execute('UPDATE users SET password_hash = ? WHERE username = ?', (hashed_pw, username))
        conn.commit()

    return "<h2>Success!</h2><p>Password updated.</p><a href='/login'>Login now</a>"

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    username = session['user_id']
    with sqlite3.connect('mindmetric.db') as conn:
        conn.row_factory = sqlite3.Row
        # We query by username because that's what's stored in your session
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
    return render_template('profile.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    username = session['user_id']
    try:
        with sqlite3.connect('mindmetric.db') as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM mood_logs WHERE username = ?", (username,))
            cur.execute("DELETE FROM users WHERE username = ?", (username,))
            conn.commit()
        
        session.clear()
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error deleting account: {e}")
        return "Error deleting account", 500

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Capture Security Answers
        q1 = request.form.get('q1', '').lower().strip()
        q2 = request.form.get('q2', '').lower().strip()
        q3 = request.form.get('q3', '').lower().strip()
        
        if password != confirm_password:
            return "Passwords do not match!", 400
        
        hashed_pw = generate_password_hash(password)
        
        try:
            with sqlite3.connect('mindmetric.db') as conn:
                cur = conn.cursor()
                # Updated SQL to include questions
                cur.execute("""
                    INSERT INTO users (username, password_hash, q1_answer, q2_answer, q3_answer) 
                    VALUES (?, ?, ?, ?, ?)
                """, (username, hashed_pw, q1, q2, q3))
                conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Username already exists!", 400
                
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login')), 302
    return render_template('dashboard.html')

# --- DATABASE INIT ---

def init_db():
    with sqlite3.connect('mindmetric.db') as conn:
        # 1. Mood Logs Table
        conn.execute('''CREATE TABLE IF NOT EXISTS mood_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            mood_score INTEGER NOT NULL,
            thought_text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # 2. Updated Users Table with Security Questions
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            q1_answer TEXT,
            q2_answer TEXT,
            q3_answer TEXT
        )''')
    print("Database refreshed and ready with Security Questions!")

if __name__ == '__main__':
    init_db()
    app.run(debug=True)