import sqlite3
from flask import Flask, render_template, request, url_for, redirect, jsonify, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'mmu_project_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
DATABASE = 'mindmetric.db'

# --- DATABASE HELPERS ---
def get_db():
    # Check if a database connection already exists for this request
    db = getattr(g, '_database', None)
    if db is None:
        # If not, create one and store it in 'g' for global object
        db = g._database = sqlite3.connect(DATABASE)
        # This allows us to access columns by name (e.g., row['username'])
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    # This automatically closes the databse when the user's request ends
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def save_mood_entry(username, score, thought):
    try:
        db = get_db() # Simplified: use the new helper get_db()
        db.execute('''
            INSERT INTO mood_logs (username, mood_score, thought_text, timestamp)
            VALUES (?, ?, ?, datetime('now', 'localtime'))
        ''', (username, score, thought))
        db.commit()
        return True
    except Exception as e:
        print(f"Database error: {e}")
        return False

def get_mood_trends(username):
    db = get_db()
    cursor = db.execute('''
            SELECT date(timestamp), AVG(mood_score) 
            FROM mood_logs 
            WHERE username = ? 
            GROUP BY date(timestamp)
            ORDER BY date(timestamp) ASC
    ''', (username,))
    rows = cursor.fetchall()
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

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember_me')
        
        db = get_db()
        db.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        user = db.fetchone()

        if user and check_password_hash(user[0], password):
            session['user_id'] = username
            
            if remember:
                session.permanent = True
                
            return redirect(url_for('dashboard'))
        else:
            return "Invalid username or password", 401
            
    return render_template('login.html')

# Forget password
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username')
        a1 = request.form.get('q1', '').lower().strip()
        a2 = request.form.get('q2', '').lower().strip()
        a3 = request.form.get('q3', '').lower().strip()
        
        db = get_db()
        db.row_factory = sqlite3.Row
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        # Security Verification
        if user and user['q1_answer'] == a1 and user['q2_answer'] == a2 and user['q3_answer'] == a3:
            return render_template('forgot_password.html', user_found=True, username=username)
        else:
            flash("Incorrect answers or username not found.", "danger")
            return redirect(url_for('forgot_password'))
            
    return render_template('forgot_password.html', user_found=False)

# Reset Password
@app.route('/reset_password', methods=['POST'])
def reset_password():
    username = request.form.get('username')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if new_password != confirm_password:
        return "Passwords do not match! <a href='/forgot_password'>Try again</a>"

    hashed_pw = generate_password_hash(new_password)

    db = get_db()
    db.execute('UPDATE users SET password_hash = ? WHERE username = ?',
               (hashed_pw, username))
    db.commit()

    return "<h2>Success!</h2><p>Password updated.</p><a href='/login'>Login now</a>"

# Profile
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    username = session['user_id']
    db = get_db()
    db.row_factory = sqlite3.Row
    # We query by username because that's what's stored in your session
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
    return render_template('profile.html', user=user)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Delete account
@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    username = session['user_id']
    try:
        db = get_db()
        db.execute("DELETE FROM mood_logs WHERE username = ?", (username,))
        db.execute("DELETE FROM users WHERE username = ?", (username,))
        db.commit()
        
        session.clear()
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error deleting account: {e}")
        return "Error deleting account", 500

# Register account
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
            db = get_db()
                # Updated SQL to include questions
            db.execute("""
                INSERT INTO users (username, password_hash, q1_answer, q2_answer, q3_answer) 
                VALUES (?, ?, ?, ?, ?)
            """, (username, hashed_pw, q1, q2, q3))
            db.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Username already exists!", 400
                
    return render_template('register.html')

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login')), 302
    return render_template('dashboard.html')

# History
@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    username = session['user_id']
    
    db = get_db()
    db.row_factory = sqlite3.Row
    # Requirement: Sort by date (Newest first)
    logs = db.execute('''
        SELECT mood_score, thought_text, timestamp 
        FROM mood_logs 
        WHERE username = ? 
        ORDER BY timestamp DESC
    ''', (username,)).fetchall()
        
    return render_template('history.html', logs=logs)

# API: Fetch data for the Chart
@app.route('/api/mood_data/<username>')
def api_mood_data(username):
    
    # Time range
    time_range = request.args.get('range', 'day')
    offset = int(request.args.get('offset', 0)) # 0 = current, 1 = previous, etc.
    
    # Define the jump size for each range
    ranges = {
        '6h': '6 hours',
        'day': '1 day',
        'week': '7 days',
        'month': '30 days',
    }
    
    unit = ranges.get(time_range, '1 day')
    
    # Logic:
    # Start point = now - (offset * 1 periods)
    # End point = now - (offset periods)
    start_time = f"datetime('now', '-{(offset + 1)} {unit}')"
    end_time = f"datetime('now', -{(offset)} {unit}')"

    db = get_db()
        
    if time_range in ranges:
        cursor = db.execute(f'''
            SELECT timestamp, mood_score
            FROM mood_logs
            WHERE username = ?
            AND timestamp >= {start_time}
            AND timestamp < {end_time}
            ORDER BY timestamp ASC
        ''', (username,))
    else:
        cursor = db.execute(f'''
            SELECT timestamp, mood_score
            FROM mood_logs
            WHERE username = ?
            ORDER BY timestamp ASC
        ''', (username,))
    
    rows = cursor.fetchall()
    print(f"DEBUG: Found {len(rows)} rows for {username} in range {time_range}") # Debug tool
    return jsonify({
        "labels": [row[0] for row in rows],
        "data": [row[1] for row in rows]
    })

# API: Save mood from the Dashboard
@app.route('/api/log_mood', methods=['POST'])
def api_log_mood():
    data = request.json
    username = data.get('username')
    score = data.get('mood_score')
    thought = data.get('thought_text')
    success = save_mood_entry(username, score, thought)
    
    if success:
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 500

# --- DATABASE INIT ---
def init_db():
    db = get_db()
    # 1. Mood Logs Table
    db.execute('''CREATE TABLE IF NOT EXISTS mood_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        mood_score INTEGER NOT NULL,
        thought_text TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # 2. Updated Users Table with Security Questions
    db.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        q1_answer TEXT,
        q2_answer TEXT,
        q3_answer TEXT
    )''')
    
    print("Database refreshed and ready with Security Questions!")

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)