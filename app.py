import sqlite3
import os
import datetime
import calendar
from flask import Flask, render_template, request, url_for, redirect, jsonify, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import timedelta
from google.genai import Client

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

def is_password_complex(password):
    """Enforces uniform application complexity parameters: 6+ chars, upper, lower, digit, and special char."""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one numeric digit."
        
    # 🛡️ FIX: Force a special character check in the backend
    special_characters = "!@#$%^&*(),.?\":{}|<>/\\-+=_~`[]';"
    if not any(c in special_characters for c in password):
        return False, "Password must contain at least one special character (e.g., !, @, #, $, %, *)."
        
    return True, ""

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

def get_monthly_mood_data(username, year, month):
    """Retrieves specific time-delimited telemetry signals for chart injection."""
    db = get_db()
    query = """
        SELECT timestamp, mood_score 
        FROM mood_logs 
        WHERE username = ? 
        AND strftime('%Y-%m', timestamp) = ?
        ORDER BY timestamp ASC
    """
    return db.execute(query, (username, f"{year}-{month}")).fetchall()

MILESTONE_BADGES = [
    {"days": 3, "label": "First Spark", "emoji": "🌱", "description": "You have started building the habit."},
    {"days": 7, "label": "One Week", "emoji": "⚡", "description": "A full week of consistency."},
    {"days": 14, "label": "Two Weeks", "emoji": "🔥", "description": "Your streak is gaining momentum."},
    {"days": 30, "label": "One Month", "emoji": "🏆", "description": "A major milestone worth celebrating."},
]


def calculate_current_streak_dates(log_dates):
    log_date_set = set(log_dates)
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    if today.strftime('%Y-%m-%d') in log_date_set:
        current_date = today
    elif yesterday.strftime('%Y-%m-%d') in log_date_set:
        current_date = yesterday
    else:
        return []

    streak_dates = []
    while current_date.strftime('%Y-%m-%d') in log_date_set:
        streak_dates.append(current_date.strftime('%Y-%m-%d'))
        current_date -= datetime.timedelta(days=1)

    return streak_dates


def build_milestone_progress(streak_dates):
    streak = len(streak_dates)
    earned_badges = []

    for badge in MILESTONE_BADGES:
        if streak >= badge["days"]:
            earned_badges.append({
                **badge,
                "unlocked": True,
                "achievement_date": streak_dates[badge["days"] - 1],
            })

    next_badge = next((badge for badge in MILESTONE_BADGES if streak < badge["days"]), None)
    if next_badge:
        next_badge = {
            **next_badge,
            "days_remaining": next_badge["days"] - streak,
        }

    upcoming_badges = [
        {
            **badge,
            "days_remaining": badge["days"] - streak,
        }
        for badge in MILESTONE_BADGES
        if streak < badge["days"]
    ]

    milestone_markers = [
        {
            "date": badge["achievement_date"],
            "days": badge["days"],
            "label": badge["label"],
            "emoji": badge["emoji"],
        }
        for badge in earned_badges
    ]

    return streak, earned_badges, next_badge, milestone_markers, upcoming_badges


def build_weekly_insight_prompt(recent_logs):
    logs_summary = ""
    for log in recent_logs:
        logs_summary += f"- Date: {log['timestamp']}, Mood Score: {log['mood_score']}/5, Note: \"{log['thought_text']}\"\n"

    return f"""
            You are an empathetic wellness assistant built into the MindMetric web app.
            Analyze the following mood diary data points from the user's last few entries:

            {logs_summary}

            Provide your response in two parts separated by a vertical pipe character (|).
            Part 1: Exactly ONE emoji that perfectly represents the user's overall emotional trend or vibe from their notes (e.g., 🌟, 🌿, 🔋, 🌦️, ☕).
            Part 2: A short, comforting, 2-sentence analytical insight highlighting patterns and giving a gentle, actionable recommendation. Keep the tone warm and professional. Do not use any markdown formatting or asterisks.

            Example format: 🌿|Your mood shows a steady improvement over the last few days. Try to maintain this momentum by keeping up your evening walking habit.
            """


def get_daily_weekly_insight(username, recent_logs, entry_count):
    current_date = datetime.date.today().isoformat()
    db = get_db()
    cached_row = db.execute('''
        SELECT emoji, review, cached_date, generated_at
        FROM ai_insight_cache
        WHERE username = ? AND cached_date = ?
    ''', (username, current_date)).fetchone()

    if cached_row:
        return {
            "emoji": cached_row["emoji"],
            "review": cached_row["review"],
            "cached_date": cached_row["cached_date"],
            "generated_at": cached_row["generated_at"],
            "cache_status": "cached",
        }

    weekly_insight = {
        "emoji": "🤔",
        "review": "No recent metrics recorded this week yet. Submit your first mood log box above to see your dynamic tracking insights!",
        "cached_date": current_date,
        "generated_at": datetime.datetime.now().isoformat(timespec='seconds'),
        "cache_status": "default",
    }

    if entry_count > 0:
        try:
            client = Client()
            ai_prompt = build_weekly_insight_prompt(recent_logs)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=ai_prompt
            )

            if response.text and "|" in response.text:
                parts = response.text.strip().split("|", 1)
                weekly_insight = {
                    "emoji": parts[0].strip(),
                    "review": parts[1].strip(),
                    "cached_date": current_date,
                    "generated_at": datetime.datetime.now().isoformat(timespec='seconds'),
                    "cache_status": "fresh",
                }
            elif response.text:
                weekly_insight = {
                    "emoji": "✨",
                    "review": response.text.strip(),
                    "cached_date": current_date,
                    "generated_at": datetime.datetime.now().isoformat(timespec='seconds'),
                    "cache_status": "fresh",
                }
        except Exception as e:
            print(f"⚠️ Gemini API Call Failed: {e}")
            weekly_insight = {
                "emoji": "⚠️",
                "review": "Unable to sync with live AI generation channels. Displaying local telemetry matrices.",
                "cached_date": current_date,
                "generated_at": datetime.datetime.now().isoformat(timespec='seconds'),
                "cache_status": "fallback",
            }

    db.execute('''
        INSERT OR REPLACE INTO ai_insight_cache (username, cached_date, emoji, review, generated_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        username,
        weekly_insight["cached_date"],
        weekly_insight["emoji"],
        weekly_insight["review"],
        weekly_insight["generated_at"],
    ))
    db.commit()

    return weekly_insight

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

    # 🛡️ Recovery Flow Guard Activation
    is_valid, error_msg = is_password_complex(new_password)
    if not is_valid:
        flash(f"Reset Error: {error_msg}", "danger")
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
        
        # 🔑 Extract the password update form data fields
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        cursor = db.execute("SELECT password_hash, profile_pic FROM users WHERE username = ?", (username,))
        user_row = cursor.fetchone()
        saved_pic_path = user_row['profile_pic'] if user_row else None
        current_db_hash = user_row['password_hash'] if user_row else None
        
        file = request.files.get('profile_avatar')
        if file and file.filename != '':
            if allowed_file(file.filename):
                clean_filename = secure_filename(f"{username}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], clean_filename))
                saved_pic_path = f"uploads/profile_pics/{clean_filename}"
            else:
                flash("Invalid format! Please use PNG, JPG, JPEG, or GIF.", "danger")
                return redirect(url_for('profile'))
                
        # 🛡️ Password Modification Security Processing Pipeline
        if new_password and new_password.strip() != "":
            # 1. Verify that the user knows their current password
            if not current_db_hash or not check_password_hash(current_db_hash, current_password):
                flash("Security Error: Your current password verification failed.", "danger")
                return redirect(url_for('profile'))
                
            # 2. Check if the matching verification confirm box matches
            if new_password != confirm_password:
                flash("Verification Error: Your new password fields do not match.", "danger")
                return redirect(url_for('profile'))
                
            # 3. Check complexity using your existing function framework
            is_valid, error_msg = is_password_complex(new_password)
            if not is_valid:
                flash(f"Security Error: {error_msg}", "danger")
                return redirect(url_for('profile')) # 💡 STAYS on profile and shows error!
                
            # If valid, overwrite our hash update variable targets
            current_db_hash = generate_password_hash(new_password)
        
        # Save updates back into our user registry schema structure
        db.execute("""
            UPDATE users 
            SET name = ?, gender = ?, profile_pic = ?, password_hash = ? 
            WHERE username = ?
        """, (updated_name, selected_gender, saved_pic_path, current_db_hash, username))
        db.commit()
        
        session['name'] = updated_name
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))
        
    cursor = db.execute("SELECT username, name, gender, profile_pic FROM users WHERE username = ?", (username,))
    account_info = cursor.fetchone()

    date_rows = db.execute('''
        SELECT DISTINCT date(timestamp) as log_date
        FROM mood_logs
        WHERE username = ?
        ORDER BY log_date DESC
    ''', (username,)).fetchall()
    log_dates = [row['log_date'] for row in date_rows]
    streak_dates = calculate_current_streak_dates(log_dates)
    streak, milestone_badges, next_milestone, milestone_markers, upcoming_badges = build_milestone_progress(streak_dates)
    
    logs_cursor = db.execute("SELECT COUNT(*) as log_count, AVG(mood_score) as avg_score FROM mood_logs WHERE username = ?", (username,))
    stats = logs_cursor.fetchone()
    entry_count = stats['log_count'] if stats else 0
    avg_score = round(stats['avg_score'], 2) if stats and stats['avg_score'] else "0.00"
    
    return render_template('profile.html', user=account_info, entry_count=entry_count, avg_score=avg_score, streak=streak, milestone_badges=milestone_badges, next_milestone=next_milestone)


@app.route('/api/daily_insight')
def api_daily_insight():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    username = session['user_id']
    db = get_db()
    row = db.execute('''
        SELECT COUNT(*) as entry_count
        FROM mood_logs
        WHERE username = ?
        AND timestamp >= datetime('now', '-7 days', 'localtime')
    ''', (username,)).fetchone()
    entry_count = row['entry_count'] if row and row['entry_count'] else 0

    recent_logs = db.execute('''
        SELECT timestamp, mood_score, thought_text
        FROM mood_logs
        WHERE username = ?
        AND timestamp >= datetime('now', '-7 days', 'localtime')
        ORDER BY timestamp DESC
    ''', (username,)).fetchall()

    insight = get_daily_weekly_insight(username, recent_logs, entry_count)
    return jsonify(insight)

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
        full_name = request.form.get('full_name')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        q1 = request.form.get('q1', '').lower().strip()
        q2 = request.form.get('q2', '').lower().strip()
        q3 = request.form.get('q3', '').lower().strip()
        
        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('register'))
            
        # 🛡️ Backend Guard Activation
        is_valid, error_msg = is_password_complex(password)
        if not is_valid:
            flash(f"Registration Error: {error_msg}", "danger")
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
        
        # FIX: Unified to use standard database transaction helper
        save_mood_entry(username, mood_score, thought)
        return redirect(url_for('dashboard'))

    # --- STREAK CALCULATOR ---
    date_rows = db.execute('''
        SELECT DISTINCT date(timestamp) as log_date 
        FROM mood_logs 
        WHERE username = ? 
        ORDER BY log_date DESC
    ''', (username,)).fetchall()
    log_dates = [row['log_date'] for row in date_rows]
    streak_dates = calculate_current_streak_dates(log_dates)
    streak, milestone_badges, next_milestone, milestone_markers, upcoming_badges = build_milestone_progress(streak_dates)

    # Calculate metrics over a sliding 7-day window
    row = db.execute('''
        SELECT COUNT(*) as entry_count, AVG(mood_score) as avg_score 
        FROM mood_logs 
        WHERE username = ? 
        AND timestamp >= datetime('now', '-7 days', 'localtime')
    ''', (username,)).fetchone()
    
    entry_count = row['entry_count'] if row['entry_count'] else 0
    avg_score = round(row['avg_score'], 1) if row['avg_score'] else 0.0

    # Fetch the actual log text notes to give to Gemini
    recent_logs = db.execute('''
        SELECT timestamp, mood_score, thought_text 
        FROM mood_logs 
        WHERE username = ? 
        AND timestamp >= datetime('now', '-7 days', 'localtime')
        ORDER BY timestamp DESC
    ''', (username,)).fetchall()

    weekly_insight = get_daily_weekly_insight(username, recent_logs, entry_count)

    return render_template('dashboard.html', 
                           insight=weekly_insight, 
                           entry_count=entry_count, 
                           avg_score=avg_score,
                           streak=streak,
                           milestone_badges=milestone_badges,
                           next_milestone=next_milestone,
                           milestone_markers=milestone_markers,
                           upcoming_badges=upcoming_badges)

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
    """Returns one data point per calendar day (null for missing days) so the
    dashboard chart's gaps/counters line up correctly. Supports username='global'
    for Privacy Mode, which averages across all users."""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    now = datetime.datetime.now()
    try:
        year = int(request.args.get('year', now.year))
        month = int(request.args.get('month', now.month))
    except ValueError:
        return jsonify({"error": "Invalid year/month"}), 400

    metric_type = request.args.get('metric_type', 'none')
    month_str = f"{year}-{month:02d}"
    days_in_month = calendar.monthrange(year, month)[1]

    db = get_db()
    is_global = (username == 'global')

    # --- Mood data, averaged per day ---
    if is_global:
        mood_rows = db.execute('''
            SELECT date(timestamp) as day, AVG(mood_score) as avg_score
            FROM mood_logs
            WHERE strftime('%Y-%m', timestamp) = ?
            GROUP BY day
        ''', (month_str,)).fetchall()
    else:
        mood_rows = db.execute('''
            SELECT date(timestamp) as day, AVG(mood_score) as avg_score
            FROM mood_logs
            WHERE username = ? AND strftime('%Y-%m', timestamp) = ?
            GROUP BY day
        ''', (username, month_str)).fetchall()

    mood_by_day = {row['day']: row['avg_score'] for row in mood_rows}

    # --- Telemetry data (steps / active_hours / sleep_cycles), averaged per day ---
    telemetry_by_day = {}
    if metric_type != 'none':
        if is_global:
            telemetry_rows = db.execute('''
                SELECT date(timestamp) as day, AVG(value) as avg_value
                FROM telemetry_logs
                WHERE metric_type = ? AND strftime('%Y-%m', timestamp) = ?
                GROUP BY day
            ''', (metric_type, month_str)).fetchall()
        else:
            telemetry_rows = db.execute('''
                SELECT date(timestamp) as day, AVG(value) as avg_value
                FROM telemetry_logs
                WHERE username = ? AND metric_type = ? AND strftime('%Y-%m', timestamp) = ?
                GROUP BY day
            ''', (username, metric_type, month_str)).fetchall()

        telemetry_by_day = {row['day']: row['avg_value'] for row in telemetry_rows}

    labels = []
    mood_data = []
    telemetry_data = []
    for day_num in range(1, days_in_month + 1):
        day_str = f"{year}-{month:02d}-{day_num:02d}"
        labels.append(day_str)

        mood_val = mood_by_day.get(day_str)
        mood_data.append(round(mood_val, 2) if mood_val is not None else None)

        if metric_type != 'none':
            tele_val = telemetry_by_day.get(day_str)
            telemetry_data.append(round(tele_val, 2) if tele_val is not None else None)

    response_data = {
        "labels": labels,
        "mood_data": mood_data,
    }
    if metric_type != 'none':
        response_data["telemetry_data"] = telemetry_data

    return jsonify(response_data)

@app.route('/api/mood_data/<username>')
def api_mood_data(username):
    now = datetime.datetime.now()
    year = request.args.get('year', str(now.year))
    month = request.args.get('month', f"{now.month:02d}")
    metric = request.args.get('metric', 'none') # Capture the new metric
    
    rows = get_monthly_mood_data(username, year, month)
    
    response_data = {
        "labels": [row['timestamp'] for row in rows],
        "data": [row['mood_score'] for row in rows],
        "current_year": int(year),
        "current_month": int(month)
    }
    
    if metric != 'none':
        db = get_db()
        telemetry = db.execute('''
            SELECT value, timestamp 
            FROM telemetry_logs 
            WHERE username = ? AND metric_type = ? 
            AND strftime('%Y-%m', timestamp) = ?
            ORDER BY timestamp ASC
        ''', (username, metric, f"{year}-{month}")).fetchall()
        
        response_data['telemetry'] = [row['value'] for row in telemetry]
        response_data['telemetry_labels'] = [row['timestamp'] for row in telemetry]
        
    return jsonify(response_data)
    
@app.route('/api/log_mood', methods=['POST'])
def api_log_mood():
    data = request.json
    username = data.get('username')
    score = data.get('mood_score')
    thought = data.get('thought_text')
    
    # Intentionally honors transactional design logic architectures
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

    db.execute('''CREATE TABLE IF NOT EXISTS ai_insight_cache (
        username TEXT NOT NULL,
        cached_date TEXT NOT NULL,
        emoji TEXT NOT NULL,
        review TEXT NOT NULL,
        generated_at TEXT NOT NULL,
        PRIMARY KEY (username, cached_date)
    )''')
    
    print("Database refreshed and ready with Full Name schema parameters & Security Questions!")

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)