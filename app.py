import sqlite3
import os
import time
import random
from flask import Flask, request, render_template, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
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
        # Ensure schema.sql exists in the same directory
        if os.path.exists("schema.sql"):
            with open("schema.sql", "r") as f:
                conn.executescript(f.read())
        conn.commit()
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
def splashscreenindex():
    return render_template('splashscreenindex.html')


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


@app.route('/splash')
def splash():
    return render_template('splash.html')


@app.route('/portal')
def portal():
    return render_template('portal.html')


@app.route('/personnel_select')
def personnel_select():
    """Renders the page where users select Police, Detective, Operator, or Volunteer."""
    return render_template('personnel_select.html')


@app.route('/report', methods=['GET', 'POST'])
def report():
    if request.method == 'GET':
        return render_template('report.html')

    crime_type = request.form.get('crime_type', 'Other').strip()
    description = request.form.get('description', '').strip()
    location = request.form.get('location', '').strip()
    full_name = request.form.get('full_name', '').strip()
    cnic = request.form.get('cnic', '').strip()
    is_anonymous = 'anonymous' in request.form
    evidence = request.files.get('evidence')

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
            'Murder': 'High', 'Assault': 'High', 'Accident': 'High', 'Kidnapping': 'High',
            'Drug Offense': 'High', 'Domestic Violence': 'High', 'Robbery': 'High',
            'Theft': 'Medium', 'Fraud': 'Medium', 'Cybercrime': 'Medium', 'Burglary': 'Medium',
            'Extortion': 'Medium', 'Other': 'Medium', 'Vandalism': 'Low',
            'Noise Complaint': 'Low', 'Traffic Violation': 'Low',
        }
        priority = PRIORITY_MAP.get(crime_type, 'Medium')

        db.execute('''
            INSERT INTO Cases (complaint_id, assigned_police_id, assigned_detective_id, assigned_volunteer_id, priority, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (complaint_id, None, None, None, priority, f'Priority: {priority}'))

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


@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    valid_roles = ['Police', 'Detective', 'Operator', 'Admin', 'Volunteer']
    if role not in valid_roles:
        return redirect(url_for('portal'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        badge_number = request.form.get('badge_number').strip().upper()

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

            if user['type'] != role:
                flash(f"This account is registered as '{user['type']}', not '{role}'.", "role_error")
                error = True

        if error:
            return render_template("login.html", role=role)

        session['user_id'] = user['personnel_id']
        session['name'] = user['name']
        session['role'] = user['type']

        # CORRECTED REDIRECTION LOGIC
        if user['type'] == 'Police':
            return redirect(url_for('police_dashboard'))
        elif user['type'] == 'Detective':
            return redirect(url_for('detective_dashboard'))
        elif user['type'] == 'Volunteer':
            return redirect(url_for('volunteer_dashboard'))
        elif user['type'] == 'Operator':
            return redirect(url_for('operator_dashboard'))
        elif user['type'] == 'Admin':
            return redirect(url_for('admin_dashboard'))

    return render_template("login.html", role=role)


@app.route('/register_badge', methods=['GET', 'POST'])
def register_badge():
    if request.method == 'POST':

        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        badgenumber = request.form.get('badgenumber', '').strip().upper()
        role_type = request.form.get('type', '').strip()

        if not name or not email or not password or not badgenumber or not role_type:
            return render_template("register_badge.html", msg="Please fill in all fields ⚠️")

        if role_type not in ('Police', 'Detective', 'Operator', 'Volunteer'):
            return render_template("register_badge.html", msg="Invalid personnel type ⚠️")

        conn = get_db_connection()

        existing = conn.execute(
            "SELECT * FROM AuthorizedPersonnel WHERE name = ? OR email = ? OR badge_number = ?",
            (name, email, badgenumber)
        ).fetchone()

        if existing:
            conn.close()
            field = 'Name' if existing['name'] == name else 'Email' if existing['email'] == email else 'Badge number'
            return render_template("register_badge.html", msg=f"{field} already exists ❌")

        try:
            conn.execute(
                "INSERT INTO AuthorizedPersonnel (name, email, password_hash, badge_number, type) VALUES (?, ?, ?, ?, ?)",
                (name, email, password, badgenumber, role_type)
            )
            conn.commit()
        except Exception:
            conn.rollback()
            conn.close()
            return render_template("register_badge.html", msg="Registration failed. Please try again. ❌")

        conn.close()
        flash("Registered Successfully ", "success")
        return redirect(url_for("splash"))

    return render_template("register_badge.html")


@app.route('/my_assigned_cases')
def my_assigned_cases():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    db = get_db_connection()
    cases = db.execute('''
        SELECT c.complaint_id, cc.name as category_name, c.location, c.status,
               cs.priority, c.created_at
        FROM Complaints c
        JOIN CrimeCategories cc ON c.category_id = cc.category_id
        JOIN Cases cs ON c.complaint_id = cs.complaint_id
        WHERE cs.assigned_police_id = ?
        ORDER BY c.created_at DESC
    ''', (session['user_id'],)).fetchall()

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
    return render_template('case_tracking.html', cases=all_cases, filter_type='assigned', viewer_role='police')


@app.route('/police_dashboard')
def police_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    pending = conn.execute('''
        SELECT COUNT(*) FROM Complaints c
        JOIN Cases cs ON c.complaint_id = cs.complaint_id
        WHERE cs.assigned_police_id = ? AND c.status = 'Pending'
    ''', (session.get('user_id'),)).fetchone()[0]

    in_progress = conn.execute('''
        SELECT COUNT(*) FROM Complaints c
        JOIN Cases cs ON c.complaint_id = cs.complaint_id
        WHERE cs.assigned_police_id = ? AND c.status = 'In Progress'
    ''', (session.get('user_id'),)).fetchone()[0]

    resolved = conn.execute('''
        SELECT COUNT(*) FROM Complaints c
        JOIN Cases cs ON c.complaint_id = cs.complaint_id
        WHERE cs.assigned_police_id = ? AND c.status = 'Resolved'
    ''', (session.get('user_id'),)).fetchone()[0]

    high_priority = conn.execute("""
        SELECT  c.complaint_id,
                cc.name            AS category,
                c.description,
                c.location,
                c.status,
                cs.priority,
                cs.assigned_police_id
        FROM    Complaints c
        JOIN    Cases cs  ON c.complaint_id = cs.complaint_id
        JOIN    CrimeCategories cc ON c.category_id = cc.category_id
        WHERE   cs.priority = 'High'
        ORDER   BY c.created_at DESC
        LIMIT   4
    """).fetchall()

    all_complaints = conn.execute("""
        SELECT  c.complaint_id,
                cc.name                        AS category,
                c.location,
                c.status,
                COALESCE(cs.priority, 'Medium') AS priority
        FROM    Complaints c
        LEFT JOIN Cases cs  ON c.complaint_id = cs.complaint_id
        JOIN    CrimeCategories cc ON c.category_id = cc.category_id
        ORDER   BY c.created_at DESC
    """).fetchall()

    notifications_raw = conn.execute("""
        SELECT message, created_at
        FROM Notifications
        ORDER BY created_at DESC
        LIMIT 10
    """).fetchall()

    conn.close()

    now = datetime.utcnow()
    notifications = []
    for n in notifications_raw:
        dt = datetime.strptime(n['created_at'], '%Y-%m-%d %H:%M:%S')
        notifications.append({
            'message': n['message'],
            'time_ago': time_ago(n['created_at']),
            'is_new': (now - dt).total_seconds() / 3600 < 24
        })

    return render_template(
        'police_dashboard.html',
        pending=pending,
        in_progress=in_progress,
        resolved=resolved,
        high_priority=high_priority,
        all_complaints=all_complaints,
        notifications=notifications,
    )


@app.route('/assign_case/<int:complaint_id>', methods=['POST'])
def assign_case(complaint_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    case = conn.execute(
        "SELECT case_id FROM Cases WHERE complaint_id = ?", (complaint_id,)
    ).fetchone()

    if case:
        conn.execute(
            "UPDATE Cases SET assigned_police_id = ?, last_updated = CURRENT_TIMESTAMP "
            "WHERE complaint_id = ?",
            (session['user_id'], complaint_id),
        )
        conn.execute(
            "UPDATE Complaints SET status = 'In Progress' WHERE complaint_id = ?",
            (complaint_id,),
        )
        conn.execute(
            "INSERT INTO Logs (user_id, action) VALUES (?, ?)",
            (session['user_id'], f"Assigned case #{complaint_id}"),
        )
        conn.commit()
        flash(f'Case #{complaint_id} assigned to you.', 'success')
    else:
        flash(f'No case record found for complaint #{complaint_id}.', 'error')

    conn.close()
    return redirect(url_for('police_dashboard'))


@app.route('/resolve_case/<int:complaint_id>', methods=['POST'])
def resolve_case(complaint_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute(
        "UPDATE Complaints SET status = 'Resolved' WHERE complaint_id = ?",
        (complaint_id,),
    )
    conn.execute(
        "UPDATE Cases SET last_updated = CURRENT_TIMESTAMP WHERE complaint_id = ?",
        (complaint_id,),
    )
    conn.execute(
        "INSERT INTO Logs (user_id, action) VALUES (?, ?)",
        (session['user_id'], f"Resolved case #{complaint_id}"),
    )
    conn.commit()
    conn.close()

    flash(f'Case #{complaint_id} marked as Resolved.', 'success')
    return redirect(url_for('police_dashboard'))


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
@app.route('/case_tracking/<filter_type>')
def case_tracking(filter_type=None):
    db = get_db_connection()

    if filter_type == 'high_priority':
        cases = db.execute('''
            SELECT c.complaint_id, cc.name as category_name, c.location, c.status, 
                   cs.priority, c.created_at
            FROM Complaints c
            JOIN CrimeCategories cc ON c.category_id = cc.category_id
            JOIN Cases cs ON c.complaint_id = cs.complaint_id
            WHERE cs.priority = 'High'
            ORDER BY c.created_at DESC
        ''').fetchall()
    else:
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

    return render_template('case_tracking.html', cases=all_cases, filter_type=filter_type)


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
    is_assigned = request.args.get('assigned') == '1'
    is_detective = request.args.get('detective') == '1'

    case = db.execute('''
        SELECT c.complaint_id, cc.name as category_name, c.description, 
               c.location, c.status, c.created_at,
               cs.priority, cs.notes,
               ap_police.name as officer_name, 
               ap_police.badge_number as officer_badge,
               ap_detective.name as detective_name,
               ap_detective.badge_number as detective_badge,
               det.specialization as detective_specialization,
               vol.full_name as volunteer_name
        FROM Complaints c
        JOIN CrimeCategories cc ON c.category_id = cc.category_id
        LEFT JOIN Cases cs ON c.complaint_id = cs.complaint_id
        LEFT JOIN AuthorizedPersonnel ap_police ON cs.assigned_police_id = ap_police.personnel_id
        LEFT JOIN AuthorizedPersonnel ap_detective ON cs.assigned_detective_id = ap_detective.personnel_id
        LEFT JOIN Detectives det ON ap_detective.personnel_id = det.personnel_id
        LEFT JOIN Citizens vol ON cs.assigned_volunteer_id = vol.citizen_id
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
                'event': f"Police Officer Assigned: {case['officer_name']}",
                'date': case['created_at']
            })

        if case['detective_name']:
            timeline.append({
                'event': f"Detective Assigned: {case['detective_name']}",
                'date': case['created_at']
            })

        if case['volunteer_name']:
            timeline.append({
                'event': f"Volunteer Assigned: {case['volunteer_name']}",
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

    return render_template('case_detail.html', case=case_dict, is_assigned=is_assigned, is_detective=is_detective)


@app.route('/append_case_notes/<int:complaint_id>', methods=['POST'])
def append_case_notes(complaint_id):
    if session.get('role') != 'Detective':
        flash('Unauthorized.', 'error')
        return redirect(url_for('login'))

    new_note = request.form.get('new_note', '').strip()
    if not new_note:
        flash('Note cannot be empty.', 'error')
        return redirect(f'/case_detail/{complaint_id}?detective=1')

    conn = get_db_connection()

    check = conn.execute('''
        SELECT assigned_detective_id, notes FROM Cases WHERE complaint_id = ?
    ''', (complaint_id,)).fetchone()

    if not check:
        flash('Case not found.', 'error')
        conn.close()
        return redirect(url_for('detective_assigned_cases'))

    if check['assigned_detective_id'] != session['user_id']:
        flash('You can only add notes to cases assigned to you.', 'error')
        conn.close()
        return redirect(url_for('detective_assigned_cases'))

    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
    detective_name = session.get('name', 'Detective')
    stamped_note = f"[{timestamp}] {detective_name}: {new_note}"

    existing = check['notes'] if check['notes'] else ''
    if existing:
        updated_notes = existing + '\n' + stamped_note
    else:
        updated_notes = stamped_note

    conn.execute(
        "UPDATE Cases SET notes = ?, last_updated = CURRENT_TIMESTAMP WHERE complaint_id = ?",
        (updated_notes, complaint_id)
    )
    conn.execute(
        "INSERT INTO Logs (user_id, action) VALUES (?, ?)",
        (session['user_id'], f"Added note to case #{complaint_id}")
    )
    conn.execute(
        "INSERT INTO Notifications (message) VALUES (?)",
        (f"Detective {detective_name} added a note to case #{complaint_id}.",)
    )
    conn.commit()
    conn.close()

    flash('Note added successfully.', 'success')
    return redirect(f'/case_detail/{complaint_id}?detective=1')


@app.route('/update_case_status/<int:complaint_id>', methods=['POST'])
def update_case_status(complaint_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    new_status = request.form.get('status', '').strip()
    valid = ['Pending', 'In Progress', 'Resolved']

    if new_status not in valid:
        flash('Invalid status selected.', 'error')
        return redirect(f'/case_detail/{complaint_id}?assigned=1')

    conn = get_db_connection()

    case_check = conn.execute('''
        SELECT assigned_police_id FROM Cases WHERE complaint_id = ?
    ''', (complaint_id,)).fetchone()

    if not case_check:
        flash('Case not found.', 'error')
        conn.close()
        return redirect(url_for('my_assigned_cases'))

    if case_check['assigned_police_id'] != session['user_id']:
        flash('You can only update cases assigned to you.', 'error')
        conn.close()
        return redirect(url_for('my_assigned_cases'))

    conn.execute(
        "UPDATE Complaints SET status = ? WHERE complaint_id = ?",
        (new_status, complaint_id)
    )
    conn.execute(
        "UPDATE Cases SET last_updated = CURRENT_TIMESTAMP WHERE complaint_id = ?",
        (complaint_id,)
    )
    conn.execute(
        "INSERT INTO Logs (user_id, action) VALUES (?, ?)",
        (session['user_id'], f"Updated status of case #{complaint_id} to {new_status}")
    )
    conn.execute(
        "INSERT INTO Notifications (message) VALUES (?)",
        (f"Case #{complaint_id} has been marked as {new_status}.",)
    )
    conn.commit()
    conn.close()

    flash(f'Case #{complaint_id} status updated to {new_status}.', 'success')
    return redirect(f'/case_detail/{complaint_id}?assigned=1')


@app.route('/emergency_tracking')
def emergency_tracking():
    return render_template('emergency_tracking.html')


@app.route('/statistics_board')
def statistics_board():
    conn = get_db_connection()

    total_crimes = conn.execute("SELECT COUNT(*) FROM Complaints").fetchone()[0]

    pending = conn.execute("SELECT COUNT(*) FROM Complaints WHERE status = 'Pending'").fetchone()[0]
    in_progress = conn.execute("SELECT COUNT(*) FROM Complaints WHERE status = 'In Progress'").fetchone()[0]
    resolved = conn.execute("SELECT COUNT(*) FROM Complaints WHERE status = 'Resolved'").fetchone()[0]

    active_officers = conn.execute("SELECT COUNT(*) FROM AuthorizedPersonnel WHERE type = 'Police'").fetchone()[0]

    categories_raw = conn.execute("""
        SELECT cc.name, COUNT(c.complaint_id) as count 
        FROM Complaints c 
        JOIN CrimeCategories cc ON c.category_id = cc.category_id 
        GROUP BY cc.name 
        ORDER BY count DESC
    """).fetchall()

    max_count = max([c['count'] for c in categories_raw]) if categories_raw else 1

    red_cats = ['Theft', 'Assault', 'Robbery', 'Burglary', 'Murder', 'Kidnapping']
    yellow_cats = ['Vandalism', 'Noise Complaint', 'Other']
    cyan_cats = ['Traffic Violation', 'Accident']

    categories = []
    for c in categories_raw:
        if c['name'] in red_cats:
            bg_style = "background: linear-gradient(90deg, var(--red), #ff7a8a);"
        elif c['name'] in yellow_cats:
            bg_style = "background: linear-gradient(90deg, var(--yellow), #ffc858);"
        elif c['name'] in cyan_cats:
            bg_style = "background: linear-gradient(90deg, var(--cyan), #66e5ff);"
        else:
            bg_style = "background: linear-gradient(90deg, var(--green), #4dffce);"

        width = int((c['count'] / max_count) * 100)
        full_style = f"width: {width}%; {bg_style}"

        categories.append({
            'name': c['name'],
            'count': c['count'],
            'full_style': full_style
        })

    status_raw = conn.execute("SELECT status, COUNT(*) as count FROM Complaints GROUP BY status").fetchall()
    status_map = {'Pending': 0, 'In Progress': 0, 'Resolved': 0}
    for s in status_raw:
        if s['status'] in status_map:
            status_map[s['status']] = s['count']

    p_pending = (status_map['Pending'] / total_crimes * 100) if total_crimes > 0 else 0
    p_in_progress = (status_map['In Progress'] / total_crimes * 100) if total_crimes > 0 else 0

    stop1 = p_pending
    stop2 = stop1 + p_in_progress
    pie_gradient = f"var(--red) 0% {stop1}%, var(--cyan) {stop1}% {stop2}%, var(--green) {stop2}% 100%"

    pie_style = f"background: conic-gradient({pie_gradient});"

    avg_eta_raw = conn.execute("SELECT AVG(eta) FROM Dispatch").fetchone()[0]
    avg_eta = round(avg_eta_raw, 1) if avg_eta_raw else 0.0

    police_time = round(avg_eta * 0.9, 1)
    ambulance_time = round(avg_eta * 1.2, 1)
    fire_time = round(avg_eta * 1.0, 1)

    response_times = [
        {'label': 'Police', 'time': police_time,
         'full_style': f"width: {int((police_time / 15) * 100)}%; background: linear-gradient(90deg, var(--cyan), #66e5ff);"},
        {'label': 'Ambulance', 'time': ambulance_time,
         'full_style': f"width: {int((ambulance_time / 15) * 100)}%; background: linear-gradient(90deg, var(--green), #4dffce);"},
        {'label': 'Fire Dept', 'time': fire_time,
         'full_style': f"width: {int((fire_time / 15) * 100)}%; background: linear-gradient(90deg, var(--red), #ff7a8a);"}
    ]

    resolved_pct = int((resolved / total_crimes * 100)) if total_crimes > 0 else 0
    pending_pct = int((pending / total_crimes * 100)) if total_crimes > 0 else 0

    conn.close()

    return render_template('statistics_board.html',
                           total_crimes=total_crimes,
                           pending=pending,
                           in_progress=in_progress,
                           resolved=resolved,
                           active_officers=active_officers,
                           categories=categories,
                           status_map=status_map,
                           pie_style=pie_style,
                           response_times=response_times,
                           resolved_pct=resolved_pct,
                           pending_pct=pending_pct
                           )

@app.route('/detective_dashboard')
def detective_dashboard():
    if session.get('role') != 'Detective':
        return redirect(url_for('login'))

    conn = get_db_connection()

    # Stats: Only count cases assigned to THIS detective
    pending = conn.execute('''
        SELECT COUNT(*) FROM Complaints c
        JOIN Cases cs ON c.complaint_id = cs.complaint_id
        WHERE cs.assigned_detective_id = ? AND c.status = 'Pending'
    ''', (session.get('user_id'),)).fetchone()[0]

    in_progress = conn.execute('''
        SELECT COUNT(*) FROM Complaints c
        JOIN Cases cs ON c.complaint_id = cs.complaint_id
        WHERE cs.assigned_detective_id = ? AND c.status = 'In Progress'
    ''', (session.get('user_id'),)).fetchone()[0]

    resolved = conn.execute('''
        SELECT COUNT(*) FROM Complaints c
        JOIN Cases cs ON c.complaint_id = cs.complaint_id
        WHERE cs.assigned_detective_id = ? AND c.status = 'Resolved'
    ''', (session.get('user_id'),)).fetchone()[0]

    # High Priority: Only show cases assigned to THIS detective
    high_priority = conn.execute("""
        SELECT  c.complaint_id,
                cc.name            AS category,
                c.location,
                c.status,
                cs.priority
        FROM    Complaints c
        JOIN    Cases cs  ON c.complaint_id = cs.complaint_id
        JOIN    CrimeCategories cc ON c.category_id = cc.category_id
        WHERE   cs.priority = 'High' AND cs.assigned_detective_id = ?
        ORDER   BY c.created_at DESC
        LIMIT   4
    """, (session.get('user_id'),)).fetchall()

    # All Complaints: Only show cases assigned to THIS detective
    all_complaints = conn.execute("""
        SELECT  c.complaint_id,
                cc.name                        AS category,
                c.location,
                c.status,
                COALESCE(cs.priority, 'Medium') AS priority
        FROM    Complaints c
        LEFT JOIN Cases cs  ON c.complaint_id = cs.complaint_id
        JOIN    CrimeCategories cc ON c.category_id = cc.category_id
        WHERE   cs.assigned_detective_id = ?
        ORDER   BY c.created_at DESC
    """, (session.get('user_id'),)).fetchall()

    notifications_raw = conn.execute("""
        SELECT message, created_at
        FROM Notifications
        ORDER BY created_at DESC
        LIMIT 10
    """).fetchall()

    conn.close()

    now = datetime.utcnow()
    notifications = []
    for n in notifications_raw:
        dt = datetime.strptime(n['created_at'], '%Y-%m-%d %H:%M:%S')
        notifications.append({
            'message': n['message'],
            'time_ago': time_ago(n['created_at']),
            'is_new': (now - dt).total_seconds() / 3600 < 24
        })

    return render_template(
        'detective_dashboard.html',
        pending=pending,
        in_progress=in_progress,
        resolved=resolved,
        high_priority=high_priority,
        all_complaints=all_complaints,
        notifications=notifications,
    )

@app.route('/detective_assigned_cases')
def detective_assigned_cases():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    db = get_db_connection()
    cases = db.execute('''
        SELECT c.complaint_id, cc.name as category_name, c.location, c.status,
               cs.priority, c.created_at
        FROM Complaints c
        JOIN CrimeCategories cc ON c.category_id = cc.category_id
        JOIN Cases cs ON c.complaint_id = cs.complaint_id
        WHERE cs.assigned_detective_id = ?
        ORDER BY c.created_at DESC
    ''', (session['user_id'],)).fetchall()

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
    return render_template('case_tracking.html', cases=all_cases, filter_type='assigned', viewer_role='detective')


@app.route('/update_investigation/<int:complaint_id>', methods=['POST'])
def update_investigation(complaint_id):
    if session.get('role') != 'Detective': return redirect(url_for('login'))
    notes = request.form.get('notes', '').strip()
    status = request.form.get('status', 'In Progress')

    conn = get_db_connection()
    conn.execute("UPDATE Cases SET notes = ?, last_updated = CURRENT_TIMESTAMP WHERE complaint_id = ?",
                 (notes, complaint_id))
    conn.execute("UPDATE Complaints SET status = ? WHERE complaint_id = ?", (status, complaint_id))
    conn.execute("INSERT INTO Logs (user_id, action) VALUES (?, ?)",
                 (session['user_id'], f"Updated investigation notes for case #{complaint_id}"))
    conn.commit()
    conn.close()
    flash('Investigation updated successfully.', 'success')
    return redirect(url_for('detective_dashboard'))


@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') not in ('Operator', 'Admin'):
        return redirect(url_for('login'))

    conn = get_db_connection()

    # --- STATS ---
    pending = conn.execute("SELECT COUNT(*) FROM Complaints WHERE status = 'Pending'").fetchone()[0]
    in_progress = conn.execute("SELECT COUNT(*) FROM Complaints WHERE status = 'In Progress'").fetchone()[0]
    resolved = conn.execute("SELECT COUNT(*) FROM Complaints WHERE status = 'Resolved'").fetchone()[0]

    # --- UNASSIGNED CASES QUERIES ---
    no_officer = conn.execute("""
        SELECT c.complaint_id, cc.name as category, c.description, c.location, c.status, cs.priority, c.created_at
        FROM Complaints c
        JOIN Cases cs ON c.complaint_id = cs.complaint_id
        JOIN CrimeCategories cc ON c.category_id = cc.category_id
        WHERE cs.assigned_police_id IS NULL AND c.status IN ('Pending', 'In Progress')
        ORDER BY cs.priority DESC, c.created_at DESC
    """).fetchall()

    no_detective = conn.execute("""
        SELECT c.complaint_id, cc.name as category, c.location, c.status, cs.priority, c.created_at,
               ap.name as officer_name
        FROM Complaints c
        JOIN Cases cs ON c.complaint_id = cs.complaint_id
        JOIN CrimeCategories cc ON c.category_id = cc.category_id
        LEFT JOIN AuthorizedPersonnel ap ON cs.assigned_police_id = ap.personnel_id
        WHERE cs.assigned_police_id IS NOT NULL
          AND cs.assigned_detective_id IS NULL
          AND c.status IN ('Pending', 'In Progress')
        ORDER BY cs.priority DESC, c.created_at DESC
    """).fetchall()

    # NEW: Query for cases that need Volunteers
    no_volunteer = conn.execute("""
        SELECT c.complaint_id, cc.name as category, c.location, c.status, cs.priority, c.created_at,
               ap.name as officer_name
        FROM Complaints c
        JOIN Cases cs ON c.complaint_id = cs.complaint_id
        JOIN CrimeCategories cc ON c.category_id = cc.category_id
        LEFT JOIN AuthorizedPersonnel ap ON cs.assigned_police_id = ap.personnel_id
        WHERE cs.assigned_volunteer_id IS NULL
          AND c.status IN ('Pending', 'In Progress')
        ORDER BY cs.priority DESC, c.created_at DESC
    """).fetchall()

    # --- PERSONNEL LISTS ---
    officers = conn.execute("""
        SELECT personnel_id, name, badge_number
        FROM AuthorizedPersonnel
        WHERE type = 'Police'
        ORDER BY name
    """).fetchall()

    detectives = conn.execute("""
        SELECT p.personnel_id, p.name, p.badge_number, d.specialization
        FROM AuthorizedPersonnel p
        JOIN Detectives d ON p.personnel_id = d.personnel_id
        ORDER BY p.name
    """).fetchall()

    # NEW: List of available Volunteers
    volunteers = conn.execute("""
        SELECT personnel_id, name, badge_number
        FROM AuthorizedPersonnel
        WHERE type = 'Volunteer'
        ORDER BY name
    """).fetchall()

    # --- HIGH PRIORITY ---
    high_priority = conn.execute("""
        SELECT c.complaint_id, cc.name as category, c.description, c.location, c.status, cs.priority
        FROM Complaints c
        JOIN Cases cs ON c.complaint_id = cs.complaint_id
        JOIN CrimeCategories cc ON c.category_id = cc.category_id
        WHERE cs.priority = 'High' AND c.status != 'Resolved'
        ORDER BY c.created_at DESC
        LIMIT 5
    """).fetchall()

    # --- RECENT REPORTS ---
    recent_raw = conn.execute("""
        SELECT c.complaint_id, cc.name as category, c.location, c.status, c.created_at,
               COALESCE(cs.priority, 'Medium') as priority
        FROM Complaints c
        LEFT JOIN Cases cs ON c.complaint_id = cs.complaint_id
        JOIN CrimeCategories cc ON c.category_id = cc.category_id
        ORDER BY c.created_at DESC
        LIMIT 5
    """).fetchall()

    # --- NOTIFICATIONS ---
    notifications_raw = conn.execute("""
        SELECT message, created_at
        FROM Notifications
        ORDER BY created_at DESC
        LIMIT 10
    """).fetchall()

    # --- ALL COMPLAINTS ---
    all_complaints = conn.execute("""
        SELECT c.complaint_id, cc.name as category, c.location, c.status,
               COALESCE(cs.priority, 'Medium') as priority, c.created_at
        FROM Complaints c
        LEFT JOIN Cases cs ON c.complaint_id = cs.complaint_id
        JOIN CrimeCategories cc ON c.category_id = cc.category_id
        ORDER BY c.created_at DESC
    """).fetchall()

    conn.close()

    # --- DATA FORMATTING ---
    now = datetime.utcnow()

    recent = []
    for r in recent_raw:
        recent.append({
            'complaint_id': r['complaint_id'],
            'category': r['category'],
            'location': r['location'],
            'status': r['status'],
            'priority': r['priority'],
            'time_ago': time_ago(r['created_at'])
        })

    notifications = []
    for n in notifications_raw:
        dt = datetime.strptime(n['created_at'], '%Y-%m-%d %H:%M:%S')
        notifications.append({
            'message': n['message'],
            'time_ago': time_ago(n['created_at']),
            'is_new': (now - dt).total_seconds() / 3600 < 24
        })

    return render_template(
        'admin_dashboard.html',
        pending=pending,
        in_progress=in_progress,
        resolved=resolved,
        no_officer=no_officer,
        no_detective=no_detective,
        no_volunteer=no_volunteer,
        officers=officers,
        detectives=detectives,
        volunteers=volunteers,
        high_priority=high_priority,
        recent=recent,
        notifications=notifications,
        all_complaints=all_complaints,
    )


@app.route('/admin_assign_officer/<int:complaint_id>', methods=['POST'])
def admin_assign_officer(complaint_id):
    if session.get('role') not in ('Operator', 'Admin'):
        return redirect(url_for('login'))

    officer_id = request.form.get('officer_id')
    if not officer_id:
        flash('Please select an officer.', 'error')
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()

    officer = conn.execute(
        "SELECT name FROM AuthorizedPersonnel WHERE personnel_id = ?", (officer_id,)
    ).fetchone()

    if not officer:
        flash('Invalid officer selected.', 'error')
        conn.close()
        return redirect(url_for('admin_dashboard'))

    # FIXED: Update Cases table assignment
    conn.execute(
        "UPDATE Cases SET assigned_police_id = ?, last_updated = CURRENT_TIMESTAMP WHERE complaint_id = ?",
        (officer_id, complaint_id)
    )

    # FIXED: Also update Complaints table status to 'In Progress' so that dashboard updates
    conn.execute(
        "UPDATE Complaints SET status = 'In Progress' WHERE complaint_id = ?",
        (complaint_id,)
    )

    conn.execute(
        "INSERT INTO Logs (user_id, action) VALUES (?, ?)",
        (session['user_id'], f"Assigned officer {officer['name']} to case #{complaint_id}")
    )
    conn.execute(
        "INSERT INTO Notifications (message) VALUES (?)",
        (f"Admin assigned {officer['name']} to case #{complaint_id}.",)
    )
    conn.commit()
    conn.close()

    flash(f"Officer {officer['name']} assigned to case #{complaint_id}.", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin_assign_detective/<int:complaint_id>', methods=['POST'])
def admin_assign_detective(complaint_id):
    if session.get('role') not in ('Operator', 'Admin'):
        return redirect(url_for('login'))

    detective_id = request.form.get('detective_id')
    if not detective_id:
        flash('Please select a detective.', 'error')
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()

    detective = conn.execute("""
        SELECT p.name, d.specialization
        FROM AuthorizedPersonnel p
        JOIN Detectives d ON p.personnel_id = d.personnel_id
        WHERE p.personnel_id = ?
    """, (detective_id,)).fetchone()

    if not detective:
        flash('Invalid detective selected.', 'error')
        conn.close()
        return redirect(url_for('admin_dashboard'))


    conn.execute(
        "UPDATE Cases SET assigned_detective_id = ?, last_updated = CURRENT_TIMESTAMP WHERE complaint_id = ?",
        (detective_id, complaint_id)
    )


    conn.execute(
        "UPDATE Complaints SET status = 'In Progress' WHERE complaint_id = ?",
        (complaint_id,)
    )

    conn.execute(
        "INSERT INTO Logs (user_id, action) VALUES (?, ?)",
        (session['user_id'],
         f"Assigned detective {detective['name']} ({detective['specialization']}) to case #{complaint_id}")
    )
    conn.execute(
        "INSERT INTO Notifications (message) VALUES (?)",
        (f"Admin assigned Detective {detective['name']} ({detective['specialization']}) to case #{complaint_id}.",)
    )
    conn.commit()
    conn.close()

    flash(f"Detective {detective['name']} assigned to case #{complaint_id}.", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/dispatch_unit', methods=['POST'])
def dispatch_unit():
    if session.get('role') != 'Operator': return redirect(url_for('login'))

    complaint_id = request.form.get('complaint_id')
    unit_id = request.form.get('unit_id')
    eta = request.form.get('eta', 10)

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO Dispatch (complaint_id, assigned_unit_id, status, eta) VALUES (?, ?, 'Dispatched', ?)",
        (complaint_id, unit_id, eta))
    conn.execute("UPDATE Complaints SET status = 'In Progress' WHERE complaint_id = ?", (complaint_id,))
    conn.execute("INSERT INTO Notifications (message) VALUES (?)",
                 f'Emergency unit dispatched to Complaint #{complaint_id}. ETA: {eta} mins.')
    conn.commit()
    conn.close()

    flash('Unit dispatched successfully!', 'success')
    return redirect(url_for('operator_dashboard'))


@app.route('/update_dispatch/<int:dispatch_id>', methods=['POST'])
def update_dispatch(dispatch_id):
    new_status = request.form.get('status')
    conn = get_db_connection()
    conn.execute("UPDATE Dispatch SET status = ? WHERE dispatch_id = ?", (new_status, dispatch_id))
    if new_status == 'Completed':
        dispatch = conn.execute("SELECT complaint_id FROM Dispatch WHERE dispatch_id = ?",
                                (dispatch_id,)).fetchone()
        if dispatch:
            conn.execute("UPDATE Complaints SET status = 'Resolved' WHERE complaint_id = ?",
                         (dispatch['complaint_id'],))
    conn.commit()
    conn.close()
    return redirect(url_for('operator_dashboard'))


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


@app.route('/volunteer_dashboard')
def volunteer_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'Volunteer':
        return redirect(url_for('login'))

    conn = get_db_connection()

    updates_raw = conn.execute("""
        SELECT message, created_at
        FROM Notifications
        ORDER BY created_at DESC
        LIMIT 5
    """).fetchall()

    community_updates = []
    for u in updates_raw:
        community_updates.append({
            'title': 'Community Alert',
            'message': u['message'],
            'time_ago': time_ago(u['created_at'])
        })

    tasks_raw = conn.execute("""
        SELECT 
            cc.name as category_name,
            c.location,
            c.status,
            cs.priority,
            c.created_at
        FROM Cases cs
        JOIN Complaints c ON cs.complaint_id = c.complaint_id
        JOIN CrimeCategories cc ON c.category_id = cc.category_id
        WHERE cs.assigned_volunteer_id = ?
        ORDER BY c.created_at DESC
    """, (session.get('user_id'),)).fetchall()

    tasks = []
    for t in tasks_raw:
        created_str = t['created_at'] if t['created_at'] else ''
        tasks.append({
            'description': f"Check {t['category_name']} at {t['location']}",
            'zone': t['location'],
            'due_date': created_str.split(' ')[0] if created_str else 'N/A',
            'status': t['status'],
            'urgent': t['priority'] == 'High',
            'active': t['status'] == 'In Progress'
        })

    conn.close()

    return render_template(
        'volunteer_dashboard.html',
        community_updates=community_updates,
        tasks=tasks
    )


def get_operator_stats():
    """Generates stats for the top row of the dashboard."""
    return {
        'incoming_calls': random.randint(5, 25),
        'units_available': random.randint(3, 12),
        'active_dispatch': random.randint(4, 15)
    }


def get_high_priority_alerts():
    alert_types = ['SOS - App Trigger', '911 Call - Fire', '911 Call - Assault', 'Distress Signal']
    locations = ['Market Area', 'Sector 4, Gulberg', 'Main Boulevard', 'DHA Phase 6', 'Railway Station']

    alerts = []
    for i in range(random.randint(2, 5)):
        alerts.append({
            'call_id': 1000 + i,
            'type': random.choice(alert_types),
            'location': random.choice(locations),
            'caller_info': f'Unknown {random.randint(100, 999)}',
            'status': random.choice(['Active', 'Connecting'])
        })
    return alerts


def get_operator_notifications():
    messages = [
        "Unit Alpha-2 has arrived on scene.",
        "New SOS signal detected near Sector 5.",
        "Unit Bravo-4 marked available.",
        "Unit Charlie-1 requesting backup.",
        "Call dropped: #1042 - Attempting callback."
    ]
    notifs = []
    for msg in messages:
        notifs.append({
            'message': msg,
            'time_ago': f"{random.randint(1, 59)} mins ago",
            'is_new': random.choice([True, False])
        })
    return notifs


def get_active_dispatches():
    units = ['Alpha-1', 'Alpha-2', 'Bravo-4', 'Charlie-1', 'Delta-3', 'Echo-9']
    locations = ['Johar Town', 'Iqbal Town', 'Model Town', 'Gulberg III', 'Cantonment']

    dispatches = []
    for i, unit in enumerate(random.sample(units, k=len(units))):
        dispatches.append({
            'dispatch_id': 5000 + i,
            'unit_number': unit,
            'target_location': random.choice(locations),
            'eta': f"{random.randint(2, 15)} mins",
            'priority': random.choice(['High', 'Medium', 'Low'])
        })
    return dispatches


@app.route('/operator_dashboard')
def operator_dashboard():
    if session.get('role') not in ('Operator', 'Admin'):
        return redirect(url_for('login'))

    if 'name' not in session:
        session['name'] = 'Sarah'

    stats = get_operator_stats()
    high_priority = get_high_priority_alerts()
    notifications = get_operator_notifications()
    active_dispatches = get_active_dispatches()

    return render_template(
        'operator_dashboard.html',
        session=session,
        incoming_calls=stats['incoming_calls'],
        units_available=stats['units_available'],
        active_dispatch=stats['active_dispatch'],
        high_priority=high_priority,
        notifications=notifications,
        active_dispatches=active_dispatches
    )





@app.route('/admin_assign_volunteer/<int:complaint_id>', methods=['POST'])
def admin_assign_volunteer(complaint_id):
    if session.get('role') not in ('Operator', 'Admin'):
        return redirect(url_for('login'))

    volunteer_id = request.form.get('volunteer_id')
    if not volunteer_id:
        flash('Please select a volunteer.', 'error')
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()

    volunteer = conn.execute(
        "SELECT name FROM AuthorizedPersonnel WHERE personnel_id = ?", (volunteer_id,)
    ).fetchone()

    if not volunteer:
        flash('Invalid volunteer selected.', 'error')
        conn.close()
        return redirect(url_for('admin_dashboard'))

    # FIXED: Update Cases table assignment
    conn.execute(
        "UPDATE Cases SET assigned_volunteer_id = ?, last_updated = CURRENT_TIMESTAMP WHERE complaint_id = ?",
        (volunteer_id, complaint_id)
    )

    # FIXED: Also update Complaints table status to 'In Progress' so that dashboard updates
    conn.execute(
        "UPDATE Complaints SET status = 'In Progress' WHERE complaint_id = ?",
        (complaint_id,)
    )

    conn.execute(
        "INSERT INTO Logs (user_id, action) VALUES (?, ?)",
        (session['user_id'], f"Assigned volunteer {volunteer['name']} to case #{complaint_id}")
    )
    conn.execute(
        "INSERT INTO Notifications (message) VALUES (?)",
        (f"Admin assigned Volunteer {volunteer['name']} to case #{complaint_id}.",)
    )
    conn.commit()
    conn.close()

    flash(f"Volunteer {volunteer['name']} assigned to case #{complaint_id}.", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/log_patrol', methods=['GET', 'POST'])
def log_patrol():
    if 'user_id' not in session or session.get('role') != 'Volunteer':
        return redirect(url_for('login'))

    if request.method == 'POST':
        location = request.form.get('location', '').strip()
        notes = request.form.get('notes', '').strip()

        if not location:
            flash('Location is required.', 'error')
            return redirect(url_for('log_patrol'))

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO Logs (user_id, action) VALUES (?, ?)",
            (session['user_id'], f"Patrol logged at {location}. Notes: {notes}")
        )
        conn.execute(
            "INSERT INTO Notifications (message) VALUES (?)",
            (f"Volunteer {session.get('name')} logged patrol at {location}.",)
        )
        conn.commit()
        conn.close()

        flash('Patrol activity logged successfully.', 'success')
        return redirect(url_for('volunteer_dashboard'))

    return render_template('log_patrol.html')


@app.route('/updates')
def updates():
    return notifications()


@app.route('/schedule')
def schedule():
    if 'user_id' not in session or session.get('role') != 'Volunteer':
        return redirect(url_for('login'))

    db = get_db_connection()
    cases = db.execute('''
        SELECT c.complaint_id, cc.name as category_name, c.location, c.status,
               cs.priority, c.created_at
        FROM Complaints c
        JOIN CrimeCategories cc ON c.category_id = cc.category_id
        JOIN Cases cs ON c.complaint_id = cs.complaint_id
        WHERE cs.assigned_volunteer_id = ?
        ORDER BY c.created_at DESC
    ''', (session['user_id'],)).fetchall()

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

    return render_template('case_tracking.html', cases=all_cases, filter_type='assigned', viewer_role='volunteer')

with app.app_context():
    try:
        init_db()
    except Exception as e:
        print(f"DB Init Note: {e} ")


if __name__ == '__main__':
    app.run(debug=True)