import sqlite3
import os
import time
from flask import Flask, request, render_template, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
from flask import url_for, flash
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


@app.route('/personnel_select')
def personnel_select():
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
            'Assault': 'High',
            'Theft': 'Medium',
            'Fraud': 'Medium',
            'Cybercrime': 'Medium',
            'Vandalism': 'Low',
            'Other': 'Medium',
        }
        priority = PRIORITY_MAP.get(crime_type, 'Medium')

        db.execute('''
            INSERT INTO Cases (complaint_id, assigned_police_id, assigned_detective_id, assigned_volunteer_id, priority, notes)
            VALUES (?, ?, ?, ?)
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
    valid_roles = ['Police', 'Detective', 'Operator', 'Admin']
    if role not in valid_roles:
        return redirect(url_for('portal'))

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

            if user['type'] != role:
                flash(f"This account is registered as '{user['type']}', not '{role}'.", "role_error")
                error = True

        if error:
            return render_template("login.html", role=role)

        session['user_id'] = user['personnel_id']
        session['name'] = user['name']
        session['role'] = user['type']

        if user['type'] == 'Police':
            return redirect(url_for('police_dashboard'))
        elif user['type'] == 'Detective':
            return redirect(url_for('detective_dashboard'))
        elif user['type'] == 'Operator':
            return redirect(url_for('admin_dashboard'))
        elif user['type'] == 'Admin':
            return redirect(url_for('admin_dashboard'))

    return render_template("login.html", role=role)


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

@app.route('/my_assigned_cases')
def my_assigned_cases():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect('/login')

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
    return render_template('case_tracking.html', cases=all_cases, filter_type='assigned')


@app.route('/police_dashboard')
def police_dashboard():
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

    conn.close()

    return render_template(
        'police_dashboard.html',
        pending=pending,
        in_progress=in_progress,
        resolved=resolved,
        high_priority=high_priority,
        all_complaints=all_complaints,
    )


@app.route('/assign_case/<int:complaint_id>', methods=['POST'])
def assign_case(complaint_id):
    if 'personnel_id' not in session:
        flash('Please log in first.', 'error')
        return redirect('/login')

    conn = get_db_connection()
    case = conn.execute(
        "SELECT case_id FROM Cases WHERE complaint_id = ?", (complaint_id,)
    ).fetchone()

    if case:
        conn.execute(
            "UPDATE Cases SET assigned_police_id = ?, last_updated = CURRENT_TIMESTAMP "
            "WHERE complaint_id = ?",
            (session['personnel_id'], complaint_id),
        )
        conn.execute(
            "UPDATE Complaints SET status = 'In Progress' WHERE complaint_id = ?",
            (complaint_id,),
        )
        # Log the action
        conn.execute(
            "INSERT INTO Logs (user_id, action) VALUES (?, ?)",
            (session['personnel_id'], f"Assigned case #{complaint_id}"),
        )
        conn.commit()
        flash(f'Case #{complaint_id} assigned to you.', 'success')
    else:
        flash(f'No case record found for complaint #{complaint_id}.', 'error')

    conn.close()
    return redirect('/police_dashboard')


@app.route('/resolve_case/<int:complaint_id>', methods=['POST'])
def resolve_case(complaint_id):
    if 'personnel_id' not in session:
        flash('Please log in first.', 'error')
        return redirect('/login')

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
        (session['personnel_id'], f"Resolved case #{complaint_id}"),
    )
    conn.commit()
    conn.close()

    flash(f'Case #{complaint_id} marked as Resolved.', 'success')
    return redirect('/police_dashboard')


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

    return render_template('case_detail.html', case=case_dict, is_assigned=is_assigned)


@app.route('/update_case_status/<int:complaint_id>', methods=['POST'])
def update_case_status(complaint_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect('/login')

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
        return redirect('/my_assigned_cases')

    if case_check['assigned_police_id'] != session['user_id']:
        flash('You can only update cases assigned to you.', 'error')
        conn.close()
        return redirect('/my_assigned_cases')

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

    # Total Crimes
    total_crimes = conn.execute("SELECT COUNT(*) FROM Complaints").fetchone()[0]

    # Crime by Category (REQ-24)
    categories = conn.execute("""
        SELECT cc.name, COUNT(c.complaint_id) as count 
        FROM Complaints c JOIN CrimeCategories cc ON c.category_id = cc.category_id 
        GROUP BY cc.name ORDER BY count DESC
    """).fetchall()
    status_stats = conn.execute("""
            SELECT status, COUNT(*) as count
            FROM Complaints
            GROUP BY status
        """).fetchall()

    conn.close()

    return render_template('statistics_board.html',
                           total_crimes=total_crimes,
                           categories=categories,
                           status_stats=status_stats)


@app.route('/detective_dashboard')
def detective_dashboard():
    if session.get('role') != 'Detective':
        return redirect(url_for('login'))

    conn = get_db_connection()

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

    high_priority = conn.execute("""
        SELECT  c.complaint_id,
                cc.name            AS category,
                c.description,
                c.location,
                c.status,
                cs.priority
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

    conn.close()

    return render_template(
        'detective_dashboard.html',
        pending=pending,
        in_progress=in_progress,
        resolved=resolved,
        high_priority=high_priority,
        all_complaints=all_complaints,
    )


@app.route('/detective_assigned_cases')
def detective_assigned_cases():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect('/login')

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
    return render_template('case_tracking.html', cases=all_cases, filter_type='assigned')


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
    if session.get('role') != 'Operator': return redirect(url_for('login'))

    conn = get_db_connection()
    active_dispatches = conn.execute("""
            SELECT d.dispatch_id, d.complaint_id, d.status, d.eta, c.location, cc.name as category
            FROM Dispatch d
            JOIN Complaints c ON d.complaint_id = c.complaint_id
            JOIN CrimeCategories cc ON c.category_id = cc.category_id
            WHERE d.status NOT IN ('Completed')
            ORDER BY d.created_at DESC
        """).fetchall()

    unassigned_high = conn.execute("""
            SELECT c.complaint_id, cc.name as category, c.location 
            FROM Complaints c JOIN Cases cs ON c.complaint_id = cs.complaint_id
            JOIN CrimeCategories cc ON c.category_id = cc.category_id
            WHERE cs.priority = 'High' AND c.complaint_id NOT IN (SELECT complaint_id FROM Dispatch)
        """).fetchall()

    # Get available units (Citizens marked as volunteers or personnel)
    units = conn.execute("SELECT citizen_id, full_name FROM Citizens LIMIT 5").fetchall()
    conn.close()

    return render_template('operator_dashboard.html', active_dispatches=active_dispatches,
                           unassigned_high=unassigned_high, units=units)


@app.route('/dispatch_unit', methods=['POST'])
def dispatch_unit():
    if session.get('role') != 'Operator': return redirect(url_for('login'))

    complaint_id = request.form.get('complaint_id')
    unit_id = request.form.get('unit_id')
    eta = request.form.get('eta', 10)

    conn = get_db_connection()
    # Insert dispatch record
    conn.execute(
        "INSERT INTO Dispatch (complaint_id, assigned_unit_id, status, eta) VALUES (?, ?, 'Dispatched', ?)",
        (complaint_id, unit_id, eta))
    # Update complaint status
    conn.execute("UPDATE Complaints SET status = 'In Progress' WHERE complaint_id = ?", (complaint_id,))
    conn.execute("INSERT INTO Notifications (message) VALUES (?)",
                 (f'Emergency unit dispatched to Complaint #{complaint_id}. ETA: {eta} mins.'))
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
    return redirect(url_for('admin_dashboard'))


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