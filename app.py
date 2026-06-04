import sqlite3
import os
import urllib.request
import urllib.parse
import json
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

# Google OAuth2 Credentials & Constants Configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
OAUTH_SCOPES = 'https://www.googleapis.com/auth/fitness.activity.read'
AUTH_URI = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_URI = 'https://oauth2.googleapis.com/token'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- DATABASE HELPERS ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def save_mood_entry(username, score, thought):
    """Inserts a mood record and returns a tuple (Success Boolean, dict row data or None)"""
    try:
        db = get_db()
        cursor = db.cursor()
        # Save exact local execution timestamp tracking string
        timestamp_str = db.execute("SELECT datetime('now', 'localtime')").fetchone()[0]
        cursor.execute('''
            INSERT INTO mood_logs (username, mood_score, thought_text, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (username, score, thought, timestamp_str))
        db.commit()
        last_id = cursor.lastrowid
        return True, {"id": last_id, "timestamp": timestamp_str}
    except Exception as e:
        print(f"Database error in save_mood_entry: {e}")
        return False, None

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

@app.context_processor
def inject_user():
    return dict(current_user=session.get('name'))

# --- MAIN CORE WEB PATHWAYS ---
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
        user = db.execute("SELECT password_hash, name FROM users WHERE username = ?", (username,)).fetchone()

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

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for('index'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    username = session['user_id']
    if request.method == 'POST':
        # Handles standalone fallback form submissions if JS is deactivated
        score = request.form.get('mood_score')
        thought = request.form.get('thought')
        success, _ = save_mood_entry(username, int(score), thought)
        if success:
            flash("Entry cataloged successfully!", "success")
        else:
            flash("System issue recording entries.", "danger")
        return redirect(url_for('dashboard'))
        
    return render_template('dashboard.html')

# --- REFACTOR: NEW MINDMETRIC 2 ENDPOINTS ---

@app.route('/api/log_mood', methods=['POST'])
def api_log_mood():
    """Decoupled programmatic endpoint returning structural entry parameters mapping metadata definitions."""
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    data = request.json or {}
    username = session['user_id']
    score = data.get('mood_score')
    thought = data.get('thought_text') # Can pass explicitly empty/null mapping definitions for Blind Data Mode
    
    if score is None:
        return jsonify({"status": "error", "message": "Missing mood score parameter"}), 400
        
    success, entry_meta = save_mood_entry(username, int(score), thought)
    if success:
        return jsonify({
            "status": "success",
            "id": entry_meta["id"],
            "timestamp": entry_meta["timestamp"]
        })
    return jsonify({"status": "error", "message": "Database transaction failure"}), 500

@app.route('/api/mood_logs/<student_id>', methods=['GET'])
def api_get_mood_logs(student_id):
    """Provides complete list historical logs tracking parameters enabling granular client interface merging."""
    if 'user_id' not in session or session['user_id'] != student_id:
        return jsonify({"status": "error", "message": "Access restricted"}), 403
        
    db = get_db()
    cursor = db.execute('''
        SELECT id, mood_score, thought_text, timestamp 
        FROM mood_logs 
        WHERE username = ? 
        ORDER BY timestamp DESC
    ''', (student_id,))
    
    logs = []
    for row in cursor.fetchall():
        logs.append({
            "id": row["id"],
            "mood_score": row["mood_score"],
            "thought_text": row["thought_text"],
            "timestamp": row["timestamp"]
        })
    return jsonify({"status": "success", "logs": logs})

@app.route('/api/mood_trends_v2')
def api_mood_trends_v2():
    if 'user_id' not in session:
        return jsonify({"status": "error"}), 401
    return jsonify(get_mood_trends(session['user_id']))

# --- GOOGLE FIT API PROTO WORKFLOWS (OAUTH2 + INTERACTIVE MOCK SANDBOX) ---

@app.route('/fit/auth')
def fit_auth():
    """Redirects to standard cloud authorization system node or initializes immediate local validation overrides."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    # Validation fallback if live environment keys are unconfigured
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        # Route to Mock Authorization Sandbox Node Flow Directly
        session['fit_mock_handshake'] = True
        return redirect(url_for('fit_callback', code='sandbox_mock_handshake_activation_token'))
        
    redirect_uri = url_for('fit_callback', _external=True)
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': OAUTH_SCOPES,
        'access_type': 'offline',
        'prompt': 'consent'
    }
    url = f"{AUTH_URI}?{urllib.parse.urlencode(params)}"
    return redirect(url)

@app.route('/fit/callback')
def fit_callback():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    code = request.args.get('code')
    if not code:
        flash("Google Fit Authorization canceled.", "danger")
        return redirect(url_for('dashboard'))
        
    # Local Interactive Sandbox validation pathway
    if code == 'sandbox_mock_handshake_activation_token' or session.get('fit_mock_handshake'):
        session['fit_access_token'] = 'mock_sandbox_access_token_signature_string'
        session['fit_is_mock'] = True
        flash("Connected to Google Fit Interactive Mock Sandbox Hub!", "success")
        return redirect(url_for('dashboard'))
        
    # Standard server payload resolution infrastructure
    redirect_uri = url_for('fit_callback', _external=True)
    payload = urllib.parse.urlencode({
        'code': code,
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }).encode('utf-8')
    
    try:
        req = urllib.request.Request(TOKEN_URI, data=payload, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            session['fit_access_token'] = res_data.get('access_token')
            session['fit_is_mock'] = False
            flash("Google Fit API production link successfully authorized!", "success")
    except Exception as e:
        print(f"Token parsing exception: {e}")
        flash("OAuth configuration parameters incorrect. Reverting to sandbox parameters.", "warning")
        session['fit_access_token'] = 'mock_sandbox_access_token_signature_string'
        session['fit_is_mock'] = True
        
    return redirect(url_for('dashboard'))

@app.route('/api/fit/data')
def api_fit_data():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    token = session.get('fit_access_token')
    if not token:
        return jsonify({"status": "error", "message": "No active Google Fit token link established"}), 400
        
    # Return Mock Sandbox telemetry metrics simulation payloads
    if session.get('fit_is_mock') or token == 'mock_sandbox_access_token_signature_string':
        mock_payload = {
            "status": "Sandbox Mock Stream Verified",
            "dataSourceId": "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps",
            "dataTypeName": "com.google.step_count.delta",
            "aggregatedDailyMetrics": {
                "stepCountDeltaSum": 8432,
                "activeWalkingDurationSeconds": 4120,
                "approximateCaloriesBurnedKcal": 345.8
            },
            "rawPayloadMetadata": {
                "pipelineSource": "MindMetric OAuth2 UI Interactive Sandbox Framework",
                "deviceCarrierNode": "Virtual Emulator Sandbox",
                "simulatedResponseLatencyMs": 42
            }
        }
        return jsonify(mock_payload)
        
    # Production extraction node stream handling
    fit_api_endpoint = "https://www.googleapis.com/fitness/v1/users/me/dataSources"
    try:
        req = urllib.request.Request(fit_api_endpoint, headers={
            'Authorization': f'Bearer {token}',
            'User-Agent': 'Mozilla/5.0'
        })
        with urllib.request.urlopen(req) as response:
            raw_payload = json.loads(response.read().decode('utf-8'))
            return jsonify(raw_payload)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Cloud fetching exception: {str(e)}"}), 500

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
            UPDATE users SET name = ?, gender = ?, profile_pic = ? WHERE username = ?
        """, (updated_name, selected_gender, saved_pic_path, username))
        db.commit()
        session['name'] = updated_name
        flash("Profile parameters successfully adjusted!", "success")
        return redirect(url_for('profile'))
        
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    return render_template('profile.html', user=user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        full_name = request.form.get('full_name')
        password = request.form.get('password')
        gender = request.form.get('gender')
        
        a1 = request.form.get('q1', '').lower().strip()
        a2 = request.form.get('q2', '').lower().strip()
        a3 = request.form.get('q3', '').lower().strip()
        
        db = get_db()
        try:
            hashed_pw = generate_password_hash(password)
            db.execute('''
                INSERT INTO users (username, name, password_hash, gender, q1_answer, q2_answer, q3_answer)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (username, full_name, hashed_pw, gender, a1, a2, a3))
            db.commit()
            flash("Registration successful! Access your analytics portal below.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists inside the system register registry.", "danger")
            return redirect(url_for('register'))
            
    return render_template('register.html')

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    username = session['user_id']
    db = get_db()
    db.execute('DELETE FROM users WHERE username = ?', (username,))
    db.execute('DELETE FROM mood_logs WHERE username = ?', (username,))
    db.commit()
    session.clear()
    return redirect(url_for('index'))

# --- REFACTOR: INITIALIZATION ENTRY ROUTE MODIFIER ---
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
    print("Database refreshed and ready with Full Name schema parameters!")

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)