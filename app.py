import sqlite3
import os
import datetime
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
        # Fetch BOTH password_hash AND name columns
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
    a1 = request.form.get('q1', '').lower().strip()
    a2 = request.form.get('q2', '').lower().strip()
    a3 = request.form.get('q3', '').lower().strip()
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    # Guard 1: Validate frontend matching parameters
    if new_password != confirm_password:
        flash("Passwords do not match! Please try again.", "danger")
        return redirect(url_for('forgot_password'))

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

    # Guard 2: Safety check to confirm user profile row exists
    if not user:
        flash("User profile data record not found.", "danger")
        return redirect(url_for('forgot_password'))

    # Guard 3: Authenticate security questions profile keys
    if user['q1_answer'] != a1 or user['q2_answer'] != a2 or user['q3_answer'] != a3:
        flash("Identity Verification Failed: Security question answers are incorrect!", "danger")
        return redirect(url_for('forgot_password'))

    # Success Loop: Questions passed, apply secure hash and update database
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
        full_name = request.form.get('full_name')  # Grab full name from form
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
    """Generates historical tracking metrics filtered by a specific year and month."""
    import datetime
    
    # Get parameters from frontend, defaulting to the current year and month
    now = datetime.datetime.now()
    year = request.args.get('year', str(now.year))
    month = request.args.get('month', f"{now.month:02d}") # Ensures 2-digit format '01' through '12'
    
    db = get_db()
    
    # Query logs matching the specified year and month (YYYY-MM-%)
    query = """
        SELECT timestamp, mood_score 
        FROM mood_logs 
        WHERE username = ? 
        AND strftime('%Y-%m', timestamp) = ?
        ORDER BY timestamp ASC
    """
        
    rows = db.execute(query, (username, f"{year}-{month}")).fetchall()
    
    return jsonify({
        "labels": [row[0] for row in rows],
        "data": [row[1] for row in rows],
        "current_year": int(year),
        "current_month": int(month)
    })

def seed_user_telemetry(username, year, month):
    """Generates mock telemetry logs for a user if they do not exist for the specified year/month."""
    import random
    import calendar
    db = get_db()
    
    # Check if any telemetry exists for this user in this year-month
    cursor = db.execute('''
        SELECT COUNT(*) FROM telemetry_logs 
        WHERE username = ? AND strftime('%Y-%m', timestamp) = ?
    ''', (username, f"{year}-{month}"))
    count = cursor.fetchone()[0]
    
    if count == 0:
        try:
            days_in_month = calendar.monthrange(int(year), int(month))[1]
            for day in range(1, days_in_month + 1):
                date_str = f"{year}-{month}-{day:02d}"
                
                # 1. Steps count: random 2000 to 12000
                steps_val = random.randint(2000, 12000)
                db.execute("""
                    INSERT INTO telemetry_logs (username, metric_type, value, timestamp) 
                    VALUES (?, 'steps', ?, ?)
                """, (username, steps_val, f"{date_str} 20:00:00"))
                
                # 2. Active execution hours: random 1.0 to 8.0
                active_val = round(random.uniform(1.0, 8.0), 1)
                db.execute("""
                    INSERT INTO telemetry_logs (username, metric_type, value, timestamp) 
                    VALUES (?, 'active_hours', ?, ?)
                """, (username, active_val, f"{date_str} 18:00:00"))
                
                # 3. Sleep cycles: random 4.5 to 9.0
                sleep_val = round(random.uniform(4.5, 9.0), 1)
                db.execute("""
                    INSERT INTO telemetry_logs (username, metric_type, value, timestamp) 
                    VALUES (?, 'sleep_cycles', ?, ?)
                """, (username, sleep_val, f"{date_str} 08:00:00"))
                
            db.commit()
            print(f"Lazy seeded telemetry logs for user {username} for {year}-{month}")
        except Exception as e:
            print(f"Error seeding telemetry: {e}")

@app.route('/api/telemetry_data/<username>')
def api_telemetry_data(username):
    """Generates combined mood and physical telemetry logs for analytics rendering, supporting privacy mode."""
    import datetime
    import calendar
    
    now = datetime.datetime.now()
    year = request.args.get('year', str(now.year))
    month = request.args.get('month', f"{now.month:02d}")
    metric_type = request.args.get('metric_type', 'steps')
    
    db = get_db()
    
    # Lazy seed data for visualization if it's a specific user (not 'global')
    if username != 'global' and username != 'none':
        seed_user_telemetry(username, year, month)
    
    # Branch queries based on username being 'global' or a specific user
    if username == 'global':
        # Global mood tracking (average of all users per day)
        mood_query = """
            SELECT date(timestamp) as log_date, AVG(mood_score) as avg_mood
            FROM mood_logs
            WHERE strftime('%Y-%m', timestamp) = ?
            GROUP BY log_date
        """
        mood_rows = db.execute(mood_query, (f"{year}-{month}",)).fetchall()
        
        # Global physical telemetry tracking (average of all users per day)
        telemetry_query = """
            SELECT date(timestamp) as log_date, AVG(value) as avg_val
            FROM telemetry_logs
            WHERE metric_type = ? AND strftime('%Y-%m', timestamp) = ?
            GROUP BY log_date
        """
        telemetry_rows = db.execute(telemetry_query, (metric_type, f"{year}-{month}")).fetchall()
    else:
        # Localized/Personal mood tracking (average per day for the specific user)
        mood_query = """
            SELECT date(timestamp) as log_date, AVG(mood_score) as avg_mood
            FROM mood_logs
            WHERE username = ? AND strftime('%Y-%m', timestamp) = ?
            GROUP BY log_date
        """
        mood_rows = db.execute(mood_query, (username, f"{year}-{month}")).fetchall()
        
        # Localized/Personal physical telemetry tracking
        telemetry_query = """
            SELECT date(timestamp) as log_date, AVG(value) as avg_val
            FROM telemetry_logs
            WHERE username = ? AND metric_type = ? AND strftime('%Y-%m', timestamp) = ?
            GROUP BY log_date
        """
        telemetry_rows = db.execute(telemetry_query, (username, metric_type, f"{year}-{month}")).fetchall()
        
    mood_map = {row['log_date']: row['avg_mood'] for row in mood_rows}
    telemetry_map = {row['log_date']: row['avg_val'] for row in telemetry_rows}
    
    # Build complete linear arrays for all days of the selected month
    try:
        days_in_month = calendar.monthrange(int(year), int(month))[1]
    except Exception:
        days_in_month = 30
        
    labels = []
    mood_data = []
    telemetry_data = []
    
    for day in range(1, days_in_month + 1):
        date_str = f"{year}-{month}-{day:02d}"
        labels.append(date_str)
        
        # Map user's chronological mood index (or None if no entry)
        if date_str in mood_map:
            mood_data.append(round(mood_map[date_str], 2))
        else:
            mood_data.append(None)
            
        # Standardize fallback for telemetry to prevent breaking linear line arrays
        if date_str in telemetry_map:
            telemetry_data.append(round(telemetry_map[date_str], 2))
        else:
            telemetry_data.append(0.0) # Dynamic fallback for days lacking telemetry logs
            
    return jsonify({
        "labels": labels,
        "mood_data": mood_data,
        "telemetry_data": telemetry_data,
        "current_year": int(year),
        "current_month": int(month),
        "metric_type": metric_type,
        "privacy": "global" if username == 'global' else "local"
    })

@app.route('/api/mood_blind_summary')
def api_mood_blind_summary():
    """Privacy-first anonymous mood summary endpoint."""
    year = request.args.get('year')
    month = request.args.get('month')
    db = get_db()

    if year and month:
        date_filter = f"{year}-{month.zfill(2)}"
        summary = db.execute('''
            SELECT COUNT(*) as total_entries, AVG(mood_score) as avg_score
            FROM mood_logs
            WHERE strftime('%Y-%m', timestamp) = ?
        ''', (date_filter,)).fetchone()

        distribution = db.execute('''
            SELECT mood_score, COUNT(*) as count
            FROM mood_logs
            WHERE strftime('%Y-%m', timestamp) = ?
            GROUP BY mood_score
            ORDER BY mood_score DESC
        ''', (date_filter,)).fetchall()
    else:
        summary = db.execute('''
            SELECT COUNT(*) as total_entries, AVG(mood_score) as avg_score
            FROM mood_logs
        ''').fetchone()

        distribution = db.execute('''
            SELECT mood_score, COUNT(*) as count
            FROM mood_logs
            GROUP BY mood_score
            ORDER BY mood_score DESC
        ''').fetchall()

    return jsonify({
        "total_entries": summary['total_entries'] if summary else 0,
        "avg_score": round(summary['avg_score'], 2) if summary and summary['avg_score'] is not None else None,
        "distribution": [{"mood_score": row['mood_score'], "count": row['count']} for row in distribution],
        "year": int(year) if year else None,
        "month": int(month) if month else None,
        "privacy": "Aggregated mood metrics only. No user identifiers returned."
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

    # Combined table parameters: Contains security strings, names, profile pics, and gender options
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

    db.execute('''CREATE TABLE IF NOT EXISTS telemetry_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        metric_type TEXT NOT NULL,
        value REAL NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    print("Database refreshed and ready with fully unified schema configuration parameters!")

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)