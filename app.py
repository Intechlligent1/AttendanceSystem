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

# Create tables if not exist
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
        card_id = request.form['card_id'].upper()
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
        card_id = request.form['card_id'].upper()

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
    logs = db.execute("""
        SELECT a.timestamp, s.name, s.card_id 
        FROM attendance a 
        JOIN students s ON a.student_id = s.id 
        ORDER BY a.timestamp DESC
    """).fetchall()
    return render_template('attendance.html', logs=logs)

@app.route('/api/attendance', methods=['POST'])
def api_attendance():
    data = request.json
    card_id = data.get('card_id', '').upper()
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()
    student = db.execute("SELECT * FROM students WHERE card_id = ?", (card_id,)).fetchone()
    if student:
        db.execute("INSERT INTO attendance (student_id, timestamp) VALUES (?, ?)", (student['id'], timestamp))
        return jsonify({
            "status": "success",
            "message": "Attendance recorded",
            "student_name": student['name'],
            "timestamp": timestamp
        })
    else:
        return jsonify({"status": "error", "message": "Card not registered"}), 404

@app.route('/export')
def export_csv():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    month = request.args.get('month')
    year = request.args.get('year')

    query = """
        SELECT s.name, s.card_id, a.timestamp
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE strftime('%m', a.timestamp) = ? AND strftime('%Y', a.timestamp) = ?
    """

    db = get_db()
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
