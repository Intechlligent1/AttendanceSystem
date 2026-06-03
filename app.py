from flask import Flask, request, render_template, redirect, url_for, jsonify, send_file, session, flash
import sqlite3
from datetime import datetime, timedelta
import csv
import io

app = Flask(__name__)
app.secret_key = 'your_very_strong_secret_key' 
app.permanent_session_lifetime = timedelta(minutes=60)

DATABASE = 'attendance.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def table_exists(db, table_name):
    row = db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None

def column_exists(db, table_name, column_name):
    columns = db.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(column["name"] == column_name for column in columns)

def normalize_card_id(card_id):
    return (card_id or "").strip().upper()

def normalize_user_type(user_type):
    value = (user_type or "staff").strip().lower()
    return value if value in ("staff", "student") else "staff"

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT,
                card_id TEXT UNIQUE,
                user_type TEXT NOT NULL DEFAULT 'staff'
            )
        """)

        if table_exists(db, "staff"):
            if not column_exists(db, "staff", "user_type"):
                db.execute("ALTER TABLE staff ADD COLUMN user_type TEXT NOT NULL DEFAULT 'staff'")
            db.execute("UPDATE staff SET user_type = COALESCE(NULLIF(user_type, ''), 'staff')")
            db.execute("""
                INSERT OR IGNORE INTO users (id, name, card_id, user_type)
                SELECT id, name, card_id, COALESCE(NULLIF(user_type, ''), 'staff') FROM staff
            """)

        if table_exists(db, "students"):
            db.execute("""
                INSERT OR IGNORE INTO users (id, name, card_id, user_type)
                SELECT id, name, card_id, 'student' FROM students
            """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                timestamp TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        if column_exists(db, "attendance", "staff_id") and not column_exists(db, "attendance", "user_id"):
            db.execute("ALTER TABLE attendance RENAME COLUMN staff_id TO user_id")
        if column_exists(db, "attendance", "student_id") and not column_exists(db, "attendance", "user_id"):
            db.execute("ALTER TABLE attendance RENAME COLUMN student_id TO user_id")

        db.execute("UPDATE users SET user_type = 'staff' WHERE user_type IS NULL OR TRIM(user_type) = ''")

init_db()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin123':
            session.permanent = True
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    db = get_db()
    total_attendance = db.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_staff = db.execute("SELECT COUNT(*) FROM users WHERE user_type = 'staff'").fetchone()[0]
    total_students = db.execute("SELECT COUNT(*) FROM users WHERE user_type = 'student'").fetchone()[0]
    return render_template(
        'index.html',
        total_attendance=total_attendance,
        total_users=total_users,
        total_staff=total_staff,
        total_students=total_students,
    )

@app.route('/add-user', methods=['GET', 'POST'])
@app.route('/add-staff', methods=['GET', 'POST'])
@app.route('/add-student', methods=['GET', 'POST'])
def add_user():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        card_id = normalize_card_id(request.form['card_id'])
        user_type = normalize_user_type(request.form.get('user_type', 'staff'))
        try:
            with get_db() as db:
                db.execute(
                    "INSERT INTO users (name, card_id, user_type) VALUES (?, ?, ?)",
                    (name, card_id, user_type),
                )
            flash('User added successfully.', 'success')
            return redirect(url_for('dashboard'))
        except sqlite3.IntegrityError:
            flash('Card ID already registered.', 'error')
            return redirect(url_for('add_user'))
    return render_template('add_staff.html')

@app.route('/users')
@app.route('/staff')
@app.route('/students')
def users():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    db = get_db()
    filter_type = None
    if request.path.endswith('/staff'):
        filter_type = 'staff'
    elif request.path.endswith('/students'):
        filter_type = 'student'

    if filter_type:
        all_users = db.execute(
            "SELECT * FROM users WHERE user_type = ? ORDER BY id DESC",
            (filter_type,),
        ).fetchall()
    else:
        all_users = db.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    return render_template('staff.html', users=all_users, active_filter=filter_type)


@app.route('/edit-user/<int:id>', methods=['GET', 'POST'])
@app.route('/edit-staff/<int:id>', methods=['GET', 'POST'])
@app.route('/edit-student/<int:id>', methods=['GET', 'POST'])
def edit_user(id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (id,)).fetchone()

    if not user:
        flash("User not found", "error")
        return redirect(url_for('users'))

    if request.method == 'POST':
        name = request.form['name']
        card_id = normalize_card_id(request.form['card_id'])
        user_type = normalize_user_type(request.form.get('user_type', user['user_type']))

        try:
            db.execute(
                "UPDATE users SET name = ?, card_id = ?, user_type = ? WHERE id = ?",
                (name, card_id, user_type, id),
            )
            db.commit()
            flash("User updated successfully.", "success")
            return redirect(url_for('users'))
        except sqlite3.IntegrityError:
            flash("Card ID already exists!", "error")
            return redirect(url_for('edit_user', id=id))

    return render_template('edit_staff.html', user=user)


@app.route('/delete-user/<int:id>', methods=['POST'])
@app.route('/delete-staff/<int:id>', methods=['POST'])
@app.route('/delete-student/<int:id>', methods=['POST'])
def delete_user(id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    with get_db() as db:
        db.execute("DELETE FROM users WHERE id = ?", (id,))
    flash("User deleted successfully.", "success")
    return redirect(url_for('users'))


@app.route('/attendance')
def view_attendance():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    db = get_db()
    logs = db.execute("""
        SELECT a.timestamp, u.name, u.card_id, u.user_type
        FROM attendance a 
        JOIN users u ON a.user_id = u.id
        ORDER BY a.timestamp DESC
    """).fetchall()
    now = datetime.utcnow()
    return render_template(
        'attendance.html',
        logs=logs,
        current_month=now.strftime('%m'),
        current_year=now.strftime('%Y'),
    )

@app.route('/api/attendance', methods=['POST'])
def api_attendance():
    data = request.get_json(silent=True) or {}
    card_id = normalize_card_id(data.get('card_id', ''))
    if not card_id:
        return jsonify({
            "status": "error",
            "message": "card_id is required"
        }), 400
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE card_id = ?", (card_id,)).fetchone()
    if user:
        user_type = normalize_user_type(user['user_type'])
        db.execute("INSERT INTO attendance (user_id, timestamp) VALUES (?, ?)", (user['id'], timestamp))
        db.commit()
        response = {
            "status": "success",
            "message": "Attendance recorded",
            "user_name": user['name'],
            "user_type": user_type,
            "timestamp": timestamp
        }
        response[f"{user_type}_name"] = user['name']
        return jsonify(response)
    else:
        return jsonify({
            "status": "error",
            "message": "Card not registered",
            "card_id": card_id
        }), 404


@app.route('/export')
def export_csv():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    now = datetime.utcnow()
    month = request.args.get('month') or now.strftime('%m')
    year = request.args.get('year') or now.strftime('%Y')

    query = """
        SELECT u.name, u.user_type, u.card_id, a.timestamp
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        WHERE strftime('%m', a.timestamp) = ? AND strftime('%Y', a.timestamp) = ?
    """

    db = get_db()
    rows = db.execute(query, (month, year)).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'User Type', 'Card ID', 'Timestamp'])
    for row in rows:
        writer.writerow([row['name'], row['user_type'], row['card_id'], row['timestamp']])

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype='text/csv',
                     download_name=f"attendance_{month}_{year}.csv", as_attachment=True)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

