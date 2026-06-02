import sqlite3
import os
from flask import Flask, render_template, request, url_for, redirect, jsonify, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'mmu_project_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
DATABASE = 'mindmetric.db'
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'profile_pics')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Automatically create the profile picture folder structure if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- DATABASE HELPERS ---
def get_db():
    """Establishes a thread-safe database connection cached within the request context."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Automatically tears down and closes the database connection at the end of the request lifecycle."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def save_mood_entry(username, score, thought):
    """Inserts a single mood log record into the database."""
    try:
        db = get_db()
        db.execute('''
            INSERT INTO mood_logs (username, mood_score, thought_text, timestamp)
            VALUES (?, ?, ?, datetime('now', 'localtime'))
        ''', (username, score, thought))
        db.commit()
        return True
    except Exception as e:
        print(f"Database error in save_mood_entry: {e}")
        return False

def get_mood_trends(username):
    """Retrieves and aggregates chronological historical mood records for analytics rendering."""
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
    """Exposes session tracking states globally across all HTML templates."""
    return dict(current_user=session.get('name'))

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember_me')
        
        db = get_db()
        # FIXES INDEX ERROR: Fetch BOTH password_hash AND name columns
        cursor = db.execute("SELECT password_hash, name FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = username
            session['name'] = user['name']  # Caches display name globally
            if remember:
                session.permanent = True
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password.", "danger")
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username')
        a1 = request.form.get('q1', '').lower().strip()
        a2 = request.form.get('q2', '').lower().strip()
        a3 = request.form.get('q3', '').lower().strip()
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        # Verify 3-tier security answer strings
        if user and user['q1_answer'] == a1 and user['q2_answer'] == a2 and user['q3_answer'] == a3:
            # Pass answers through as hidden parameters to the next form step
            return render_template('forgot_password.html', user_found=True, username=username, q1=a1, q2=a2, q3=a3)
        else:
            flash("Incorrect answers or username not found.", "danger")
            return redirect(url_for('forgot_password'))
            
    return render_template('forgot_password.html', user_found=False)

@app.route('/reset_password', methods=['POST'])
def reset_password():
    username = request.form.get('username')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    # Guard 1: Validate matching parameters
    if new_password != confirm_password:
        flash("Passwords do not match! Please try again.", "danger")
        return redirect(url_for('forgot_password'))

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

    # Guard 2: Safety check to confirm user profile row exists
    if not user:
        flash("User profile data record not found.", "danger")
        return redirect(url_for('forgot_password'))

    # Success Loop: Apply secure hash and update database
    hashed_pw = generate_password_hash(new_password)
    db.execute('UPDATE users SET password_hash = ? WHERE username = ?', (hashed_pw, username))
    db.commit()
    
    flash("Account recovered successfully! You can now log in with your new password.", "success")
    return redirect(url_for('login'))
    

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    username = session['user_id']
    db = get_db()
    
    if request.method == 'POST':
        updated_name = request.form.get('full_name')
        selected_gender = request.form.get('gender')
        
        # Keep old profile picture if no new image is uploaded
        cursor = db.execute("SELECT profile_pic FROM users WHERE username = ?", (username,))
        user_row = cursor.fetchone()
        saved_pic_path = user_row['profile_pic'] if user_row else None
        
        # Process new image files safely
        file = request.files.get('profile_avatar')
        if file and file.filename != '':
            if allowed_file(file.filename):
                clean_filename = secure_filename(f"{username}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], clean_filename))
                saved_pic_path = f"uploads/profile_pics/{clean_filename}"
            else:
                flash("Invalid format! Please use PNG, JPG, JPEG, or GIF.", "danger")
                return redirect(url_for('profile'))
                
        # Commit name, gender choice, and image pointer to database
        db.execute("""
            UPDATE users 
            SET name = ?, gender = ?, profile_pic = ? 
            WHERE username = ?
        """, (updated_name, selected_gender, saved_pic_path, username))
        db.commit()
        
        # Keep global greeting matching immediately
        session['name'] = updated_name
        
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))
        
    # GET: Fetch account parameters to fill out interface forms
    cursor = db.execute("SELECT username, name, gender, profile_pic FROM users WHERE username = ?", (username,))
    account_info = cursor.fetchone()
    
    # Calculate telemetry entries length for summary statistics panels
    logs_cursor = db.execute("SELECT COUNT(*) as log_count, AVG(mood_score) as avg_score FROM mood_logs WHERE username = ?", (username,))
    stats = logs_cursor.fetchone()
    entry_count = stats['log_count'] if stats else 0
    avg_score = round(stats['avg_score'], 2) if stats and stats['avg_score'] else "0.00"
    
    return render_template('profile.html', user=account_info, entry_count=entry_count, avg_score=avg_score)

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
        db = get_db()
        db.execute("DELETE FROM mood_logs WHERE username = ?", (username,))
        db.execute("DELETE FROM users WHERE username = ?", (username,))
        db.commit()
        session.clear()
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error deleting account: {e}")
        return "Error deleting account", 500

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        full_name = request.form.get('full_name')  # 1. Grab full name from form
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        q1 = request.form.get('q1', '').lower().strip()
        q2 = request.form.get('q2', '').lower().strip()
        q3 = request.form.get('q3', '').lower().strip()
        
        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('register'))
        
        hashed_pw = generate_password_hash(password)
        
        try:
            db = get_db()
            # 2. Included 'name' column and its binding parameter '?'
            db.execute("""
                INSERT INTO users (username, name, password_hash, q1_answer, q2_answer, q3_answer) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, full_name, hashed_pw, q1, q2, q3))
            db.commit()
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists! Please choose a different one.", "danger")
            return redirect(url_for('register'))
                
    return render_template('register.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    username = session['user_id']
    db = get_db()
    
    # Process and commit newly submitted mood tracking forms
    if request.method == 'POST':
        mood_score = int(request.form['mood_score'])
        thought = request.form['thought']
        
        db.execute('''
            INSERT INTO mood_logs (username, mood_score, thought_text, timestamp)
            VALUES (?, ?, ?, datetime('now', 'localtime'))
        ''', (username, mood_score, thought))
        db.commit()
        return redirect(url_for('dashboard'))

    # Calculate tracking entry volume and mean scoring over a sliding 7-day window
    row = db.execute('''
        SELECT COUNT(*) as entry_count, AVG(mood_score) as avg_score 
        FROM mood_logs 
        WHERE username = ? 
        AND timestamp >= datetime('now', '-7 days', 'localtime')
    ''', (username,)).fetchone()
    
    entry_count = row['entry_count'] if row['entry_count'] else 0
    avg_score = round(row['avg_score'], 1) if row['avg_score'] else 0.0

    # Localized static dictionary containing evaluations based on rounded average scores
    insight_dictionary = {
        5: {"emoji": "🔥", "review": "Exceptional mental momentum! Your tracking signals display peak emotional clarity and highly optimal decompression behavior loops. Keep cruising here."},
        4: {"emoji": "😊", "review": "A highly positive, constructive horizon. Your tracking metrics indicate steady wellness and reliable stability. Maintain your current active choices!"},
        3: {"emoji": "😐", "review": "A balanced neutral baseline. Things are holding perfectly constant, but consider introducing mild pattern variations or taking a small physical break to feel fully energized."},
        2: {"emoji": "☹️", "review": "Your tracker highlights a subtle down-trending sequence. Energy metrics feel slightly strained. Make sure to schedule intentional downtime and get some rest today."},
        1: {"emoji": "😫", "review": "Telemetry suggests heavy processing loads and fatigue patterns. Prioritize absolute preservation right now. Close down non-essential loops and decompress."}
    }

    weekly_insight = {
        "emoji": "🤔",
        "review": "No recent metrics recorded this week yet. Submit your first mood log box above to generate your dynamic tracking insights!"
    }

    if entry_count > 0:
        score_key = max(1, min(5, int(round(avg_score))))
        weekly_insight = insight_dictionary[score_key]

    return render_template('dashboard.html', 
                           insight=weekly_insight, 
                           entry_count=entry_count, 
                           avg_score=avg_score)

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    username = session['user_id']
    db = get_db()
    logs = db.execute('''
        SELECT mood_score, thought_text, timestamp 
        FROM mood_logs 
        WHERE username = ? 
        ORDER BY timestamp DESC
    ''', (username,)).fetchall()
        
    return render_template('history.html', logs=logs)

# --- TELEMETRY AND DATA VISUALIZATION API ENDPOINTS ---

@app.route('/api/mood_data/<username>')
def api_mood_data(username):
    """Generates down-sampled historical tracking metrics configured for Chart.js rendering."""
    time_range = request.args.get('range', 'day')
    offset = int(request.args.get('offset', 0))
    
    ranges = {
        'day': '1 day',
        'week': '7 days'
    }
    
    db = get_db()
    
    if time_range in ranges:
        unit = ranges[time_range]
        start_time = f"datetime('now', '-{(offset + 1)} {unit}')"
        end_time = f"datetime('now', '-{offset} {unit}')"
        
        query = f"""
                    SELECT timestamp, mood_score 
                    FROM mood_logs 
                    WHERE username = ? 
                    AND datetime(timestamp) >= {start_time} 
                    AND datetime(timestamp) < {end_time} 
                    ORDER BY timestamp ASC
                """
    else:
        query = f"""
                    SELECT timestamp, mood_score
                    FROM mood_logs
                    WHERE username = ?
                    ORDER BY timestamp ASC
                """
        
    rows = db.execute(query, (username,)).fetchall()
    return jsonify({
        "labels": [row[0] for row in rows],
        "data": [row[1] for row in rows],
        "range_type": time_range
    })
    
@app.route('/api/log_mood', methods=['POST'])
def api_log_mood():
    """Standalone endpoint handling decoupled programmatic entry insertions."""
    data = request.json
    username = data.get('username')
    score = data.get('mood_score')
    thought = data.get('thought_text')
    success = save_mood_entry(username, score, thought)
    
    if success:
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 500

# --- DATABASE SCHEMAS DEFINITION AND INITIALIZATION ---

def init_db():
    """Initializes schema tables and parameters if the core relational file does not exist."""
    db = get_db()
    
    db.execute('''CREATE TABLE IF NOT EXISTS mood_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        mood_score INTEGER NOT NULL,
        thought_text TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # 3. Updated table schema parameters to include 'name' column
    db.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        gender TEXT,
        profile_pic TEXT,
        q1_answer TEXT,
        q2_answer TEXT,
        q3_answer TEXT
    )''')
    print("Database refreshed and ready with Full Name schema parameters!")

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)