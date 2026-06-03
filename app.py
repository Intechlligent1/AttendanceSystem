# from flask import Flask, request, render_template, redirect, url_for, jsonify, send_file, session, flash
# import sqlite3
# from datetime import datetime, timedelta
# import csv
# import io

# app = Flask(__name__)
# app.secret_key = 'your_very_strong_secret_key' 
# app.permanent_session_lifetime = timedelta(minutes=60)

# DATABASE = 'attendance.db'

# def get_db():
#     conn = sqlite3.connect(DATABASE)
#     conn.row_factory = sqlite3.Row
#     return conn

# def table_exists(db, table_name):
#     row = db.execute(
#         "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
#         (table_name,),
#     ).fetchone()
#     return row is not None

# def column_exists(db, table_name, column_name):
#     columns = db.execute(f"PRAGMA table_info({table_name})").fetchall()
#     return any(column["name"] == column_name for column in columns)

# def init_db():
#     with get_db() as db:
#         db.execute("""
#             CREATE TABLE IF NOT EXISTS staff (
#                 id INTEGER PRIMARY KEY,
#                 name TEXT,
#                 card_id TEXT UNIQUE
#             )
#         """)

#         if table_exists(db, "students"):
#             db.execute("""
#                 INSERT OR IGNORE INTO staff (id, name, card_id)
#                 SELECT id, name, card_id FROM students
#             """)

#         db.execute("""
#             CREATE TABLE IF NOT EXISTS attendance (
#                 id INTEGER PRIMARY KEY,
#                 staff_id INTEGER,
#                 timestamp TEXT,
#                 FOREIGN KEY(staff_id) REFERENCES staff(id)
#             )
#         """)

#         if column_exists(db, "attendance", "student_id") and not column_exists(db, "attendance", "staff_id"):
#             db.execute("ALTER TABLE attendance RENAME COLUMN student_id TO staff_id")

# init_db()

# @app.route('/', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         if username == 'admin' and password == 'admin123':
#             session.permanent = True
#             session['logged_in'] = True
#             return redirect(url_for('dashboard'))
#         else:
#             flash('Invalid credentials', 'error')
#     return render_template('login.html')

# @app.route('/dashboard')
# def dashboard():
#     if 'logged_in' not in session:
#         return redirect(url_for('login'))
#     db = get_db()
#     total_attendance = db.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
#     total_staff = db.execute("SELECT COUNT(*) FROM staff").fetchone()[0]
#     return render_template('index.html', total_attendance=total_attendance, total_staff=total_staff)

# @app.route('/add-staff', methods=['GET', 'POST'])
# @app.route('/add-student', methods=['GET', 'POST'])
# def add_staff():
#     if 'logged_in' not in session:
#         return redirect(url_for('login'))
#     if request.method == 'POST':
#         name = request.form['name']
#         card_id = request.form['card_id'].upper()
#         try:
#             with get_db() as db:
#                 db.execute("INSERT INTO staff (name, card_id) VALUES (?, ?)", (name, card_id))
#             flash('Staff added successfully.', 'success')
#             return redirect(url_for('dashboard'))
#         except sqlite3.IntegrityError:
#             flash('Card ID already registered.', 'error')
#             return redirect(url_for('add_staff'))
#     return render_template('add_staff.html')

# @app.route('/staff')
# @app.route('/students')
# def staff():
#     if 'logged_in' not in session:
#         return redirect(url_for('login'))
#     db = get_db()
#     all_staff = db.execute("SELECT * FROM staff ORDER BY id DESC").fetchall()
#     return render_template('staff.html', staff_members=all_staff)


# @app.route('/edit-staff/<int:id>', methods=['GET', 'POST'])
# @app.route('/edit-student/<int:id>', methods=['GET', 'POST'])
# def edit_staff(id):
#     if 'logged_in' not in session:
#         return redirect(url_for('login'))

#     db = get_db()
#     staff_member = db.execute("SELECT * FROM staff WHERE id = ?", (id,)).fetchone()

#     if not staff_member:
#         flash("Staff member not found", "error")
#         return redirect(url_for('staff'))

#     if request.method == 'POST':
#         name = request.form['name']
#         card_id = request.form['card_id'].upper()

#         try:
#             db.execute("UPDATE staff SET name = ?, card_id = ? WHERE id = ?", (name, card_id, id))
#             db.commit()
#             flash("Staff member updated successfully.", "success")
#             return redirect(url_for('staff'))
#         except sqlite3.IntegrityError:
#             flash("Card ID already exists!", "error")
#             return redirect(url_for('edit_staff', id=id))

#     return render_template('edit_staff.html', staff_member=staff_member)


# @app.route('/delete-staff/<int:id>', methods=['POST'])
# @app.route('/delete-student/<int:id>', methods=['POST'])
# def delete_staff(id):
#     if 'logged_in' not in session:
#         return redirect(url_for('login'))

#     with get_db() as db:
#         db.execute("DELETE FROM staff WHERE id = ?", (id,))
#     flash("Staff member deleted successfully.", "success")
#     return redirect(url_for('staff'))


# @app.route('/attendance')
# def view_attendance():
#     if 'logged_in' not in session:
#         return redirect(url_for('login'))
#     db = get_db()
#     logs = db.execute("""
#         SELECT a.timestamp, s.name, s.card_id
#         FROM attendance a 
#         JOIN staff s ON a.staff_id = s.id
#         ORDER BY a.timestamp DESC
#     """).fetchall()
#     now = datetime.utcnow()
#     return render_template(
#         'attendance.html',
#         logs=logs,
#         current_month=now.strftime('%m'),
#         current_year=now.strftime('%Y'),
#     )

# @app.route('/api/attendance', methods=['POST'])
# def api_attendance():
#     data = request.json
#     card_id = data.get('card_id', '').upper()
#     timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

#     db = get_db()
#     staff_member = db.execute("SELECT * FROM staff WHERE card_id = ?", (card_id,)).fetchone()
#     if staff_member:
#         db.execute("INSERT INTO attendance (staff_id, timestamp) VALUES (?, ?)", (staff_member['id'], timestamp))
#         db.commit()
#         return jsonify({
#             "status": "success",
#             "message": "Attendance recorded",
#             "staff_name": staff_member['name'],
#             "timestamp": timestamp
#         })
#     else:
#         # New: return card UID so ESP32 can show it
#         return jsonify({
#             "status": "error",
#             "message": "Card not registered",
#             "card_id": card_id
#         }), 404


# @app.route('/export')
# def export_csv():
#     if 'logged_in' not in session:
#         return redirect(url_for('login'))
#     now = datetime.utcnow()
#     month = request.args.get('month') or now.strftime('%m')
#     year = request.args.get('year') or now.strftime('%Y')

#     query = """
#         SELECT s.name, s.card_id, a.timestamp
#         FROM attendance a
#         JOIN staff s ON a.staff_id = s.id
#         WHERE strftime('%m', a.timestamp) = ? AND strftime('%Y', a.timestamp) = ?
#     """

#     db = get_db()
#     rows = db.execute(query, (month, year)).fetchall()

#     output = io.StringIO()
#     writer = csv.writer(output)
#     writer.writerow(['Name', 'Card ID', 'Timestamp'])
#     for row in rows:
#         writer.writerow([row['name'], row['card_id'], row['timestamp']])

#     output.seek(0)
#     return send_file(io.BytesIO(output.getvalue().encode()), mimetype='text/csv',
#                      download_name=f"attendance_{month}_{year}.csv", as_attachment=True)

# @app.route('/logout')
# def logout():
#     session.pop('logged_in', None)
#     flash('You have been logged out.', 'success')
#     return redirect(url_for('login'))

# if __name__ == '__main__':
#     app.run(debug=True, host='0.0.0.0')




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

def find_registered_member(db, card_id):
    normalized_card_id = normalize_card_id(card_id)
    student = db.execute(
        "SELECT id, name, card_id FROM students WHERE UPPER(card_id) = ?",
        (normalized_card_id,),
    ).fetchone()
    if student:
        return "students", student

    if table_exists(db, "staff"):
        staff_member = db.execute(
            "SELECT id, name, card_id FROM staff WHERE UPPER(card_id) = ?",
            (normalized_card_id,),
        ).fetchone()
        if staff_member:
            return "staff", staff_member

    return None, None

def attendance_member_column(db):
    if column_exists(db, "attendance", "student_id"):
        return "student_id"
    if column_exists(db, "attendance", "staff_id"):
        return "staff_id"
    return "student_id"

def attendance_member_table(db):
    column_name = attendance_member_column(db)
    if column_name == "staff_id" and table_exists(db, "staff"):
        return "staff"
    return "students"

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY,
                name TEXT,
                card_id TEXT UNIQUE
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY,
                student_id INTEGER,
                timestamp TEXT,
                FOREIGN KEY(student_id) REFERENCES students(id)
            )
        """)

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
    total_students = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    return render_template('index.html', total_attendance=total_attendance, total_students=total_students)

@app.route('/add-student', methods=['GET', 'POST'])
def add_student():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        card_id = normalize_card_id(request.form['card_id'])
        try:
            with get_db() as db:
                db.execute("INSERT INTO students (name, card_id) VALUES (?, ?)", (name, card_id))
            flash('Student added successfully.', 'success')
            return redirect(url_for('dashboard'))
        except sqlite3.IntegrityError:
            flash('Card ID already registered.', 'error')
            return redirect(url_for('add_student'))
    return render_template('add_student.html')

@app.route('/students')
def students():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    db = get_db()
    all_students = db.execute("SELECT * FROM students ORDER BY id DESC").fetchall()
    return render_template('students.html', students=all_students)


@app.route('/edit-student/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id = ?", (id,)).fetchone()

    if not student:
        flash("Student not found", "error")
        return redirect(url_for('students'))

    if request.method == 'POST':
        name = request.form['name']
        card_id = normalize_card_id(request.form['card_id'])

        try:
            db.execute("UPDATE students SET name = ?, card_id = ? WHERE id = ?", (name, card_id, id))
            db.commit()
            flash("Student updated successfully.", "success")
            return redirect(url_for('students'))
        except sqlite3.IntegrityError:
            flash("Card ID already exists!", "error")
            return redirect(url_for('edit_student', id=id))

    return render_template('edit_student.html', student=student)


@app.route('/delete-student/<int:id>', methods=['POST'])
def delete_student(id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    with get_db() as db:
        db.execute("DELETE FROM students WHERE id = ?", (id,))
    flash("Student deleted successfully.", "success")
    return redirect(url_for('students'))


@app.route('/attendance')
def view_attendance():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    db = get_db()
    attendance_column = attendance_member_column(db)
    member_table = attendance_member_table(db)
    logs = db.execute("""
        SELECT a.timestamp, s.name, s.card_id 
        FROM attendance a 
        JOIN {member_table} s ON a.{attendance_column} = s.id 
        ORDER BY a.timestamp DESC
    """.format(member_table=member_table, attendance_column=attendance_column)).fetchall()
    return render_template('attendance.html', logs=logs)

@app.route('/api/attendance', methods=['POST'])
def api_attendance():
    data = request.json
    card_id = normalize_card_id(data.get('card_id', ''))
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()
    member_table, member = find_registered_member(db, card_id)
    if member:
        attendance_column = attendance_member_column(db)
        db.execute(
            f"INSERT INTO attendance ({attendance_column}, timestamp) VALUES (?, ?)",
            (member['id'], timestamp),
        )
        db.commit()
        return jsonify({
            "status": "success",
            "message": "Attendance recorded",
            "student_name": member['name'],
            "timestamp": timestamp
        })
    else:
        # New: return card UID so ESP32 can show it
        return jsonify({
            "status": "error",
            "message": "Card not registered",
            "card_id": card_id
        }), 404


@app.route('/export')
def export_csv():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    month = request.args.get('month')
    year = request.args.get('year')
    db = get_db()
    attendance_column = attendance_member_column(db)
    member_table = attendance_member_table(db)

    query = """
        SELECT s.name, s.card_id, a.timestamp
        FROM attendance a
        JOIN {member_table} s ON a.{attendance_column} = s.id
        WHERE strftime('%m', a.timestamp) = ? AND strftime('%Y', a.timestamp) = ?
    """.format(member_table=member_table, attendance_column=attendance_column)

    rows = db.execute(query, (month, year)).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Card ID', 'Timestamp'])
    for row in rows:
        writer.writerow([row['name'], row['card_id'], row['timestamp']])

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
