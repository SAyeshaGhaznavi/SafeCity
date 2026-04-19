import sqlite3
import os
import time
from flask import Flask, request, render_template, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
from flask import url_for,  flash
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = "safe_city_secret_123"

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

DATABASE = "safecity.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        conn = get_db_connection()
        with open("schema.sql", "r") as f:
            conn.executescript(f.read())
        conn.close()

@app.route("/initdb")
def run_initdb():
    init_db()

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    table_data = {}
    for table in tables:
        table_name = table['name']
        
        cursor.execute(f"SELECT * FROM {table_name};")
        data = cursor.fetchall()
        table_data[table_name] = data
    
    conn.close()
    
    return render_template("initdb.html", table_data=table_data)

@app.route('/')
def splash():
    return render_template('splash.html')

@app.route('/viewdb')
def view_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    table_data = {}
    for table in tables:
        table_name = table['name']
        cursor.execute(f"SELECT * FROM {table_name};")
        data = cursor.fetchall()
        table_data[table_name] = data
    
    conn.close()
    
    return render_template("initdb.html", table_data=table_data)

@app.route('/portal')
def portal():
    return render_template('portal.html')

@app.route('/report', methods=['GET', 'POST'])
def report():
    if request.method == 'GET':
        return render_template('report.html')

    crime_type   = request.form.get('crime_type', 'Other').strip()
    description  = request.form.get('description', '').strip()
    location     = request.form.get('location', '').strip()
    full_name    = request.form.get('full_name', '').strip()
    cnic         = request.form.get('cnic', '').strip()
    is_anonymous = 'anonymous' in request.form
    evidence     = request.files.get('evidence')

    errors = []
    if not description:
        errors.append('Description is required.')
    if not location:
        errors.append('Location is required.')
    if not is_anonymous:
        if not full_name:
            errors.append('Full name is required (or check "Report Anonymously").')
        if not cnic:
            errors.append('CNIC is required (or check "Report Anonymously").')

    if errors:
        for e in errors:
            flash(e, 'error')
        return redirect(url_for('report'))

    db = get_db_connection()
    try:
        row = db.execute(
            'SELECT category_id FROM CrimeCategories WHERE name = ?',
            (crime_type,)
        ).fetchone()

        if row:
            category_id = row['category_id']
        else:
            cursor = db.execute(
                'INSERT INTO CrimeCategories (name) VALUES (?)',
                (crime_type,)
            )
            category_id = cursor.lastrowid

        user_id = session.get('user_id')

        if not is_anonymous:
            citizen = db.execute(
                'SELECT citizen_id FROM Citizens WHERE cnic = ?',
                (cnic,)
            ).fetchone()

            if citizen:
                user_id = citizen['citizen_id']
            else:
                cursor = db.execute(
                    'INSERT INTO Citizens (full_name, cnic) VALUES (?, ?)',
                    (full_name, cnic)
                )
                user_id = cursor.lastrowid
                session['user_id'] = user_id

        if is_anonymous:
            user_id = None

        cursor = db.execute(
            '''INSERT INTO Complaints
               (user_id, category_id, description, location, status)
               VALUES (?, ?, ?, ?, ?)''',
            (user_id, category_id, description, location, 'Pending')
        )
        complaint_id = cursor.lastrowid

        db.execute(
            'INSERT INTO Notifications (message) VALUES (?)',
            (f'New complaint #{complaint_id} ({crime_type}) reported at {location}.',)
        )

        PRIORITY_MAP = {
            'Assault':      'High',
            'Theft':        'Medium',
            'Fraud':        'Medium',
            'Cybercrime':   'Medium',
            'Vandalism':    'Low',
            'Other':      'Medium',
        }
        priority = PRIORITY_MAP.get(crime_type, 'Medium')

        officer = db.execute('''
            SELECT ap.personnel_id
            FROM AuthorizedPersonnel ap
            LEFT JOIN Cases cs ON ap.personnel_id = cs.assigned_police_id
                               AND cs.priority = 'High'
            WHERE ap.type = 'Police'
            GROUP BY ap.personnel_id
            ORDER BY COUNT(cs.case_id) ASC
            LIMIT 1
        ''').fetchone()

        assigned_police_id = officer['personnel_id'] if officer else None

        db.execute('''
            INSERT INTO Cases (complaint_id, assigned_police_id, priority, notes)
            VALUES (?, ?, ?, ?)
        ''', (complaint_id, assigned_police_id, priority,
              f'Auto-assigned | Priority: {priority}'))

        if evidence and evidence.filename:
            safe_name = secure_filename(evidence.filename)
            ext = safe_name.rsplit('.', 1)[-1] if '.' in safe_name else 'bin'
            stored_name = f"ev_{complaint_id}_{int(time.time())}.{ext}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_name)
            evidence.save(save_path)

            file_url = f"/uploads/{stored_name}"

            db.execute(
                'INSERT INTO Evidence (complaint_id, file_url) VALUES (?, ?)',
                (complaint_id, file_url)
            )

        db.commit()

    except Exception as exc:
        db.rollback()
        app.logger.error('Report submission failed: %s', exc)
        flash('Something went wrong. Please try again.', 'error')
        return redirect(url_for('report'))

    finally:
        db.close()

    flash('Thank you for reporting. Your complaint has been submitted successfully.', 'success')
    return redirect(url_for('report'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        badge_number = request.form.get('badge_number')

        conn = get_db_connection()

        user = conn.execute(
            "SELECT * FROM AuthorizedPersonnel WHERE email = ?",
            (email,)
        ).fetchone()

        conn.close()

        error = False

        if not user:
            flash("Email is incorrect", "email_error")
            error = True

        if user:

            if user['badge_number'] != badge_number:
                flash("Badge number is incorrect", "badge_error")
                error = True

            if user['password_hash'] != password:
                flash("Password is incorrect", "password_error")
                error = True

            if username and username != user['name']:
                flash("Username is incorrect", "username_error")
                error = True

        if error:
            return render_template("login.html")

        session['user_id'] = user['personnel_id']
        session['name'] = user['name']

        return redirect(url_for('police_dashboard'))

    return render_template("login.html")

@app.route('/register_badge', methods=['GET', 'POST'])
def register_badge():
    if request.method == 'POST':

        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        badgenumber = request.form.get('badgenumber', '').strip()

        if not name or not email or not password or not badgenumber:
            return render_template("register_badge.html", msg="Please fill in all fields ⚠️")

        conn = get_db_connection()

        existing = conn.execute(
            "SELECT * FROM AuthorizedPersonnel WHERE name = ? OR email = ?",
            (name, email)
        ).fetchone()

        if existing:
            conn.close()
            return render_template("register_badge.html", msg="Name or Email already exists ❌")
        
        conn.execute(
            "INSERT INTO AuthorizedPersonnel (name, email, password_hash, badge_number) VALUES (?, ?, ?, ?)",
            (name, email, password, badgenumber)
        )

        conn.commit()
        conn.close()

        flash("Registered Successfully ✅", "success")
        return redirect(url_for("splash"))

    return render_template("register_badge.html")

@app.route('/police_dashboard')
def police_dashboard():

    return render_template('police_dashboard.html')

def time_ago(dt_str):
    if not dt_str:
        return ''
    dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
    now = datetime.utcnow()
    diff = now - dt
    minutes = int(diff.total_seconds() // 60)
    if minutes < 1:
        return 'Just now'
    elif minutes < 60:
        return f'{minutes}m ago'
    elif minutes < 1440:
        return f'{minutes // 60}h ago'
    else:
        return f'{minutes // 1440}d ago'
    
@app.route('/citizen_dashboard')
def citizen_dashboard():
    db = get_db_connection()

    notifications = db.execute('''
        SELECT message, created_at
        FROM Notifications
        ORDER BY created_at DESC
        LIMIT 3
    ''').fetchall()

    now = datetime.utcnow()
    recent_notifications = []
    for n in notifications:
        dt = datetime.strptime(n['created_at'], '%Y-%m-%d %H:%M:%S')
        hours_ago = (now - dt).total_seconds() / 3600
        recent_notifications.append({
            'message': n['message'],
            'time_ago': time_ago(n['created_at']),
            'is_new': hours_ago < 24
        })

    reports = db.execute('''
        SELECT c.complaint_id, cc.name as category_name, c.location, c.status, c.created_at
        FROM Complaints c
        JOIN CrimeCategories cc ON c.category_id = cc.category_id
        ORDER BY c.created_at DESC
        LIMIT 3
    ''').fetchall()
    recent_reports = [dict(r, time_ago=time_ago(r['created_at'])) for r in reports]

    db.close()

    return render_template('citizen_dashboard.html',
        recent_notifications=recent_notifications,
        recent_reports=recent_reports
    )

@app.route('/case_tracking')
def case_tracking():
    db = get_db_connection()

    cases = db.execute('''
        SELECT c.complaint_id, cc.name as category_name, c.location, c.status, 
               cs.priority, c.created_at
        FROM Complaints c
        JOIN CrimeCategories cc ON c.category_id = cc.category_id
        LEFT JOIN Cases cs ON c.complaint_id = cs.complaint_id
        ORDER BY c.created_at DESC
    ''').fetchall()

    all_cases = []
    for c in cases:
        all_cases.append({
            'complaint_id': c['complaint_id'],
            'category_name': c['category_name'],
            'location': c['location'],
            'status': c['status'],
            'priority': c['priority'] if c['priority'] else 'Medium',
            'time_ago': time_ago(c['created_at'])
        })

    db.close()

    return render_template('case_tracking.html', cases=all_cases)

@app.route('/notifications')
def notifications():
    db = get_db_connection()

    all_notifications = db.execute('''
        SELECT message, created_at
        FROM Notifications
        ORDER BY created_at DESC
    ''').fetchall()

    now = datetime.utcnow()
    notifications_list = []
    for n in all_notifications:
        dt = datetime.strptime(n['created_at'], '%Y-%m-%d %H:%M:%S')
        hours_ago = (now - dt).total_seconds() / 3600
        notifications_list.append({
            'message': n['message'],
            'time_ago': time_ago(n['created_at']),
            'is_new': hours_ago < 24,
            'date': dt.strftime('%b %d, %Y · %I:%M %p')
        })

    db.close()

    return render_template('notifications.html', all_notifications=notifications_list)

@app.route('/case_detail/<int:case_id>')
def case_detail(case_id):
    db = get_db_connection()
    
    case = db.execute('''
        SELECT c.complaint_id, cc.name as category_name, c.description, 
               c.location, c.status, c.created_at,
               cs.priority, cs.notes,
               ap.name as officer_name, ap.badge_number as officer_badge
        FROM Complaints c
        JOIN CrimeCategories cc ON c.category_id = cc.category_id
        LEFT JOIN Cases cs ON c.complaint_id = cs.complaint_id
        LEFT JOIN AuthorizedPersonnel ap ON cs.assigned_police_id = ap.personnel_id
        WHERE c.complaint_id = ?
    ''', (case_id,)).fetchone()
    
    evidence_files = []
    if case:
        evidence = db.execute('''
            SELECT file_url
            FROM Evidence
            WHERE complaint_id = ?
        ''', (case_id,)).fetchall()
        
        for e in evidence:
            filename = e['file_url'].split('/')[-1] if e['file_url'] else 'Unknown file'
            evidence_files.append({
                'name': filename,
                'url': e['file_url']
            })
    

    timeline = []
    if case:
        timeline.append({
            'event': 'Case Filed',
            'date': case['created_at']
        })
        
        if case['status'] != 'Pending' and case['status']:
            timeline.append({
                'event': f"Status: {case['status']}",
                'date': case['created_at']
            })
            
        if case['officer_name']:
            timeline.append({
                'event': 'Officer Assigned',
                'date': case['created_at']
            })
    
    db.close()
    
    if not case:
        flash('Case not found', 'error')
        return redirect(url_for('case_tracking'))
    
    case_dict = dict(case)
    case_dict['evidence_files'] = evidence_files
    case_dict['timeline'] = timeline
    
    if case_dict['created_at']:
        try:
            dt = datetime.strptime(case_dict['created_at'], '%Y-%m-%d %H:%M:%S')
            case_dict['date_filed'] = dt.strftime('%B %d, %Y')
        except:
            case_dict['date_filed'] = case_dict['created_at']
    
    return render_template('case_detail.html', case=case_dict)

@app.route('/emergency_tracking')
def emergency_tracking():
    return render_template('emergency_tracking.html')

@app.route('/statistics_board')
def statistics_board():
    return render_template('statistics_board.html')

@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    role = session.get('role')

    if not user_id:
        return redirect(url_for('login'))
    conn = get_db_connection()

    if role == "personnel":
        user = conn.execute(
            "SELECT * FROM AuthorizedPersonnel WHERE personnel_id = ?",
            (user_id,)
        ).fetchone()

    elif role == "citizen":
        user = conn.execute(
            "SELECT * FROM Citizens WHERE citizen_id = ?",
            (user_id,)
        ).fetchone()

    else:
        conn.close()
        return redirect(url_for('login'))

    conn.close()

    return render_template("profile.html", user=user, role=role)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('portal'))

@app.route('/my_complaints')
def my_complaints():
    user_id = session.get('user_id')

    conn = get_db_connection()
    complaints = conn.execute(
        "SELECT * FROM Complaints WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    conn.close()

    return render_template("my_complaints.html", complaints=complaints)

@app.route('/update_status/<int:id>', methods=['POST'])
def update_status(id):
    status = request.form.get('status')

    conn = get_db_connection()
    conn.execute(
        "UPDATE Complaints SET status = ? WHERE complaint_id = ?",
        (status, id)
    )
    conn.commit()
    conn.close()

    return redirect(url_for('police_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)