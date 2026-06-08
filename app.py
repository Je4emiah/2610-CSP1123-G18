import sqlite3
import os
import datetime
import calendar
import random
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

def seed_user_telemetry(username, year, month):
    """Generates mock telemetry logs for a user if they do not exist for the specified year/month."""
    db = get_db()
    
    # Check if any telemetry exists for this user in this year-month
    cursor = db.execute('''
        SELECT COUNT(*) FROM telemetry_logs 
        WHERE username = ? AND strftime('%Y-%m', timestamp) = ?
    ''', (username, f"{year}-{month.zfill(2)}"))
    count = cursor.fetchone()[0]
    
    if count == 0:
        try:
            days_in_month = calendar.monthrange(int(year), int(month))[1]
            for day in range(1, days_in_month + 1):
                date_str = f"{year}-{month.zfill(2)}-{day:02d}"
                
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
            print(f"Seeded mock telemetry logs for user {username} for {year}-{month}")
        except Exception as e:
            print(f"Error seeding telemetry: {e}")

# --- CONTEXT PROCESSOR ---
@app.context_processor
def inject_user():
    """Exposes session tracking states globally across all HTML templates."""
    return dict(current_user=session.get('name') if session.get('name') else session.get('user_id'))

# --- ROUTES ---
@app.route('/')
def index():
    competitors = [
        {"feature": "Automated Mood Analytics", "mindmetric": "✅ Advanced (Monthly/Yearly)", "competitor_a": "❌ Basic Only", "competitor_b": "⚠️ Premium Only"},
        {"feature": "Secure 3-Tier Account Recovery", "mindmetric": "✅ Yes", "competitor_a": "❌ Email Only", "competitor_b": "❌ Email Only"},
        {"feature": "Custom Profile Avatars & Personalization", "mindmetric": "✅ Yes", "competitor_a": "⚠️ Premium Only", "competitor_b": "❌ No"},
        {"feature": "Data Privacy & Localized Storage", "mindmetric": "✅ Full Encryption", "competitor_a": "⚠️ Shared Data", "competitor_b": "⚠️ Cloud Only"},
        {"feature": "Pricing", "mindmetric": "💎 100% Free", "competitor_a": "$9.99/mo", "competitor_b": "$4.99/mo"},
    ]
    return render_template('index.html', competitors=competitors)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember_me')
        
        db = get_db()
        cursor = db.execute("SELECT password_hash, name FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = username
            session['name'] = user['name']
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
        
        if user and user['q1_answer'] == a1 and user['q2_answer'] == a2 and user['q3_answer'] == a3:
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

    if new_password != confirm_password:
        flash("Passwords do not match! Please try again.", "danger")
        return redirect(url_for('forgot_password'))

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

    if not user:
        flash("User profile data record not found.", "danger")
        return redirect(url_for('forgot_password'))

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
        
        cursor = db.execute("SELECT profile_pic FROM users WHERE username = ?", (username,))
        user_row = cursor.fetchone()
        saved_pic_path = user_row['profile_pic'] if user_row else None
        
        file = request.files.get('profile_avatar')
        if file and file.filename != '':
            if allowed_file(file.filename):
                clean_filename = secure_filename(f"{username}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], clean_filename))
                saved_pic_path = f"uploads/profile_pics/{clean_filename}"
            else:
                flash("Invalid format! Please use PNG, JPG, JPEG, or GIF.", "danger")
                return redirect(url_for('profile'))
                
        db.execute("""
            UPDATE users 
            SET name = ?, gender = ?, profile_pic = ? 
            WHERE username = ?
        """, (updated_name, selected_gender, saved_pic_path, username))
        db.commit()
        
        session['name'] = updated_name
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))
        
    cursor = db.execute("SELECT username, name, gender, profile_pic FROM users WHERE username = ?", (username,))
    account_info = cursor.fetchone()
    
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
        db.execute("DELETE FROM telemetry_logs WHERE username = ?", (username,))
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
        full_name = request.form.get('full_name')
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
    
    if request.method == 'POST':
        mood_score = int(request.form['mood_score'])
        thought = request.form['thought']
        save_mood_entry(username, mood_score, thought)
        return redirect(url_for('dashboard'))

    # --- STREAK CALCULATOR ---
    date_rows = db.execute('''
        SELECT DISTINCT date(timestamp) as log_date 
        FROM mood_logs 
        WHERE username = ? 
        ORDER BY log_date DESC
    ''', (username,)).fetchall()

    streak = 0
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    log_dates = [row['log_date'] for row in date_rows]

    if today_str in log_dates or yesterday_str in log_dates:
        current_date = datetime.date.today() if today_str in log_dates else datetime.date.today() - datetime.timedelta(days=1)
        while current_date.strftime('%Y-%m-%d') in log_dates:
            streak += 1
            current_date -= datetime.timedelta(days=1)

    # 7-day window analytics
    row = db.execute('''
        SELECT COUNT(*) as entry_count, AVG(mood_score) as avg_score 
        FROM mood_logs 
        WHERE username = ? 
        AND timestamp >= datetime('now', '-7 days', 'localtime')
    ''', (username,)).fetchone()
    
    entry_count = row['entry_count'] if row['entry_count'] else 0
    avg_score = round(row['avg_score'], 1) if row['avg_score'] else 0.0

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
                           avg_score=avg_score,
                           streak=streak)

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    username = session['user_id']
    db = get_db()
    raw_logs = db.execute('''
        SELECT id, mood_score, thought_text, timestamp 
        FROM mood_logs 
        WHERE username = ? 
        ORDER BY timestamp DESC
    ''', (username,)).fetchall()
    
    logs = []
    for log in raw_logs:
        log_dict = dict(log)
        if not log_dict['thought_text'] or log_dict['thought_text'].strip() == "":
            log_dict['thought_text'] = "Logged entry without additional thoughts."
        logs.append(log_dict)
        
    return render_template('history.html', logs=logs)

@app.route('/delete_entry/<int:log_id>', methods=['POST'])
def delete_entry(log_id):
    if 'user_id' not in session:
        return 'Unauthorized', 401
    try:
        db = get_db()
        db.execute("DELETE FROM mood_logs WHERE id = ? AND username = ?", (log_id, session['user_id']))
        db.commit()
        return '', 200
    except Exception as e:
        print(f"Error deleting log: {e}")
        return 'Database Error', 500

# --- TELEMETRY AND DATA VISUALIZATION API ENDPOINTS ---

@app.route('/api/telemetry_data/<username>')
def api_telemetry_data(username):
    """Generates combined mood and physical telemetry logs for analytics rendering, supporting privacy mode."""
    now = datetime.datetime.now()
    year = request.args.get('year', str(now.year))
    month = request.args.get('month', f"{now.month:02d}")
    metric_type = request.args.get('metric_type', 'steps')
    
    db = get_db()
    
    if username != 'global' and username != 'none':
        seed_user_telemetry(username, year, month)
    
    if username == 'global':
        mood_query = """
            SELECT date(timestamp) as log_date, AVG(mood_score) as avg_mood
            FROM mood_logs
            WHERE strftime('%Y-%m', timestamp) = ?
            GROUP BY log_date
        """
        mood_rows = db.execute(mood_query, (f"{year}-{month.zfill(2)}",)).fetchall()
        
        telemetry_query = """
            SELECT date(timestamp) as log_date, AVG(value) as avg_val
            FROM telemetry_logs
            WHERE metric_type = ? AND strftime('%Y-%m', timestamp) = ?
            GROUP BY log_date
        """
        telemetry_rows = db.execute(telemetry_query, (metric_type, f"{year}-{month.zfill(2)}")).fetchall()
    else:
        mood_query = """
            SELECT date(timestamp) as log_date, AVG(mood_score) as avg_mood
            FROM mood_logs
            WHERE username = ? AND strftime('%Y-%m', timestamp) = ?
            GROUP BY log_date
        """
        mood_rows = db.execute(mood_query, (username, f"{year}-{month.zfill(2)}")).fetchall()
        
        telemetry_query = """
            SELECT date(timestamp) as log_date, AVG(value) as avg_val
            FROM telemetry_logs
            WHERE username = ? AND metric_type = ? AND strftime('%Y-%m', timestamp) = ?
            GROUP BY log_date
        """
        telemetry_rows = db.execute(telemetry_query, (username, metric_type, f"{year}-{month.zfill(2)}")).fetchall()
        
    mood_map = {row['log_date']: row['avg_mood'] for row in mood_rows}
    telemetry_map = {row['log_date']: row['avg_val'] for row in telemetry_rows}
    
    try:
        days_in_month = calendar.monthrange(int(year), int(month))[1]
    except Exception:
        days_in_month = 30
        
    labels = []
    mood_data = []
    telemetry_data = []
    
    for day in range(1, days_in_month + 1):
        date_str = f"{year}-{month.zfill(2)}-{day:02d}"
        labels.append(date_str)
        
        if date_str in mood_map:
            mood_data.append(round(mood_map[date_str], 2))
        else:
            mood_data.append(None)
            
        if date_str in telemetry_map:
            telemetry_data.append(round(telemetry_map[date_str], 2))
        else:
            telemetry_data.append(0.0)
            
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
    db = get_db()
    db.execute('''CREATE TABLE IF NOT EXISTS mood_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        mood_score INTEGER NOT NULL,
        thought_text TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

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
