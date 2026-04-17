import sqlite3
from flask import Flask, request, render_template, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
from flask import url_for,  flash

app = Flask(__name__)
app.secret_key = "safe_city_secret_123"

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

@app.route('/portal')
def portal():
    return render_template('portal.html')

@app.route('/report')
def report():
    return render_template('report.html')


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
        return redirect(url_for("portal"))

    return render_template("register_badge.html")

@app.route('/police_dashboard')
def police_dashboard():
    return render_template('police_dashboard.html')

@app.route('/submit_report', methods=['POST'])
def submit_report():
    name = request.form.get('name')
    cnic = request.form.get('cnic')
    description = request.form.get('description')
    location = request.form.get('location')
    category_name = request.form.get('category')
    anonymous = request.form.get('anonymous')
    conn = get_db_connection()
    if anonymous:
        user_id = None
    else:
        citizen = conn.execute(
            "SELECT * FROM Citizens WHERE cnic = ?",
            (cnic,)
        ).fetchone()

        if citizen:
            user_id = citizen['citizen_id']
        else:
            cursor = conn.execute(
                "INSERT INTO Citizens (name, cnic) VALUES (?, ?)",
                (name, cnic)
            )
            user_id = cursor.lastrowid

    category = conn.execute(
        "SELECT category_id FROM CrimeCategories WHERE name = ?",
        (category_name,)
    ).fetchone()

    category_id = category['category_id'] if category else None

    conn.execute("""
        INSERT INTO Complaints (user_id, category_id, description, location)
        VALUES (?, ?, ?, ?)
    """, (user_id, category_id, description, location))

    conn.commit()
    conn.close()

    flash("Complaint submitted successfully 🚀", "success")
    return redirect(url_for('report'))

if __name__ == '__main__':
    app.run(debug=True)