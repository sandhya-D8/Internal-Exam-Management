from flask import Flask, render_template, request, redirect, session
import os
import sqlite3

app = Flask(__name__)
app.secret_key = "super_secret_key"
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

# -------- DATABASE --------
def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    # Removed DROP TABLE students to prevent data loss
    conn.execute('''CREATE TABLE IF NOT EXISTS students
                 (id TEXT PRIMARY KEY,
                  name TEXT,
                  semester TEXT,
                  month TEXT,
                  attendance_percent INTEGER,
                  sub1 INTEGER,
                  sub2 INTEGER,
                  sub3 INTEGER,
                  sub4 INTEGER,
                  sub5 INTEGER,
                  total INTEGER,
                  result TEXT,
                  dob TEXT)''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS notices
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  type TEXT,
                  title TEXT,
                  content TEXT,
                  date_posted TEXT)''')
    
    conn.commit()
    conn.close()

init_db()

# Hardcoded secure admin login
admin_data = {
    "admin": "Admin@123"
}

# -------- HOME (LOGIN) --------
@app.route('/', methods=['GET'])
def index():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form['role']

        # ADMIN LOGIN
        if role == "admin":
            username = request.form['username']
            password = request.form['password'] # Using secure password

            if username in admin_data and admin_data[username] == password:
                session['admin'] = True
                return redirect('/admin_dashboard')
            else:
                return render_template("login.html", error="Invalid Admin Credentials. Please use the secure username and password.")

        # STUDENT LOGIN
        else:
            roll = request.form['roll']
            dob = request.form['dob']

            conn = sqlite3.connect(DATABASE_PATH)
            student = conn.execute(
                "SELECT * FROM students WHERE id=? AND dob=?",
                (roll, dob)
            ).fetchone()
            conn.close()

            if student:
                session['student'] = roll
                return redirect('/student_dashboard')
            else:
                return render_template("login.html", error="Invalid Student Details. Make sure you enter your Register Number and DOB correctly.")

    return render_template("login.html", error=None)

# -------- ADMIN DASHBOARD --------
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect('/login')

    conn = sqlite3.connect(DATABASE_PATH)
    data = conn.execute("SELECT * FROM students").fetchall()
    conn.close()

    pass_count = len([x for x in data if x[11] == "Pass"])
    fail_count = len([x for x in data if x[11] == "Fail"])
    absent_count = len([x for x in data if x[11] == "Absent"])
    od_count = len([x for x in data if x[11] == "OD"])

    # Calculate average marks for each subject (excluding Absent/OD students)
    valid_students = [x for x in data if x[11] not in ["Absent", "OD"]]
    num_valid = len(valid_students)
    sub1_avg = round(sum(x[5] for x in valid_students) / num_valid, 2) if num_valid > 0 else 0
    sub2_avg = round(sum(x[6] for x in valid_students) / num_valid, 2) if num_valid > 0 else 0
    sub3_avg = round(sum(x[7] for x in valid_students) / num_valid, 2) if num_valid > 0 else 0
    sub4_avg = round(sum(x[8] for x in valid_students) / num_valid, 2) if num_valid > 0 else 0
    sub5_avg = round(sum(x[9] for x in valid_students) / num_valid, 2) if num_valid > 0 else 0

    return render_template("admin_dashboard.html",
                           data=data,
                           pass_count=pass_count,
                           fail_count=fail_count,
                           absent_count=absent_count,
                           od_count=od_count,
                           sub1_avg=sub1_avg,
                           sub2_avg=sub2_avg,
                           sub3_avg=sub3_avg,
                           sub4_avg=sub4_avg,
                           sub5_avg=sub5_avg)

# -------- ADD STUDENT --------
@app.route('/add', methods=['GET','POST'])
def add():
    if 'admin' not in session:
        return redirect('/login')

    if request.method == 'POST':
        reg_id = request.form['id']
        name = request.form['name']
        semester = request.form['semester']
        month = request.form['month']
        attendance_percent = int(request.form['attendance_percent'])
        exam_status = request.form.get('exam_status', 'Present')
        dob = request.form['dob']

        if exam_status == 'Absent':
            sub1, sub2, sub3, sub4, sub5, total = 0, 0, 0, 0, 0, 0
            result = "Absent"
        elif exam_status == 'OD':
            sub1, sub2, sub3, sub4, sub5, total = 0, 0, 0, 0, 0, 0
            result = "OD"
        else:
            sub1 = int(request.form.get('sub1', 0))
            sub2 = int(request.form.get('sub2', 0))
            sub3 = int(request.form.get('sub3', 0))
            sub4 = int(request.form.get('sub4', 0))
            sub5 = int(request.form.get('sub5', 0))
            total = sub1 + sub2 + sub3 + sub4 + sub5

            # Must score 40 or above in ALL individual subjects to pass
            if sub1 >= 40 and sub2 >= 40 and sub3 >= 40 and sub4 >= 40 and sub5 >= 40:
                result = "Pass"
            else:
                result = "Fail"

        conn = sqlite3.connect(DATABASE_PATH)
        try:
            conn.execute("INSERT INTO students(id,name,semester,month,attendance_percent,sub1,sub2,sub3,sub4,sub5,total,result,dob) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         (reg_id, name, semester, month, attendance_percent, sub1, sub2, sub3, sub4, sub5, total, result, dob))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Error: A student with this Register Number already exists!", 400
            
        conn.close()
        return redirect('/admin_dashboard')

    return render_template("add.html")

# -------- EDIT --------
@app.route('/edit/<id>', methods=['GET','POST'])
def edit(id):
    if 'admin' not in session:
        return redirect('/login')

    conn = sqlite3.connect(DATABASE_PATH)

    if request.method == 'POST':
        name = request.form['name']
        semester = request.form['semester']
        month = request.form['month']
        attendance_percent = int(request.form['attendance_percent'])
        exam_status = request.form.get('exam_status', 'Present')
        dob = request.form['dob']

        if exam_status == 'Absent':
            sub1, sub2, sub3, sub4, sub5, total = 0, 0, 0, 0, 0, 0
            result = "Absent"
        elif exam_status == 'OD':
            sub1, sub2, sub3, sub4, sub5, total = 0, 0, 0, 0, 0, 0
            result = "OD"
        else:
            sub1 = int(request.form.get('sub1', 0))
            sub2 = int(request.form.get('sub2', 0))
            sub3 = int(request.form.get('sub3', 0))
            sub4 = int(request.form.get('sub4', 0))
            sub5 = int(request.form.get('sub5', 0))
            total = sub1 + sub2 + sub3 + sub4 + sub5

            if sub1 >= 40 and sub2 >= 40 and sub3 >= 40 and sub4 >= 40 and sub5 >= 40:
                result = "Pass"
            else:
                result = "Fail"

        conn.execute("UPDATE students SET name=?, semester=?, month=?, attendance_percent=?, sub1=?, sub2=?, sub3=?, sub4=?, sub5=?, total=?, result=?, dob=? WHERE id=?",
                     (name, semester, month, attendance_percent, sub1, sub2, sub3, sub4, sub5, total, result, dob, id))
        conn.commit()
        conn.close()

        return redirect('/edit_students')

    student = conn.execute("SELECT * FROM students WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template("edit.html", student=student)

# -------- DELETE --------
@app.route('/delete/<id>')
def delete(id):
    if 'admin' not in session:
        return redirect('/login')

    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("DELETE FROM students WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect('/edit_students')

# -------- VIEW STUDENTS --------
@app.route('/view_students')
def view_students():
    if 'admin' not in session:
        return redirect('/login')

    query = request.args.get('q', '')

    conn = sqlite3.connect(DATABASE_PATH)
    if query:
        data = conn.execute("SELECT * FROM students WHERE id LIKE ? OR name LIKE ?", ('%'+query+'%', '%'+query+'%')).fetchall()
    else:
        data = conn.execute("SELECT * FROM students").fetchall()
    conn.close()

    return render_template("view_students.html", data=data)

# -------- EDIT STUDENTS (LIST) --------
@app.route('/edit_students')
def edit_students():
    if 'admin' not in session:
        return redirect('/login')

    query = request.args.get('q', '')

    conn = sqlite3.connect(DATABASE_PATH)
    if query:
        data = conn.execute("SELECT * FROM students WHERE id LIKE ? OR name LIKE ?", ('%'+query+'%', '%'+query+'%')).fetchall()
    else:
        data = conn.execute("SELECT * FROM students").fetchall()
    conn.close()

    return render_template("edit_students.html", data=data)

# -------- STUDENT DASHBOARD --------
@app.route('/student_dashboard')
def student_dashboard():
    if 'student' not in session:
        return redirect('/login')

    roll = session['student']

    conn = sqlite3.connect(DATABASE_PATH)
    student = conn.execute("SELECT * FROM students WHERE id=?", (roll,)).fetchone()
    notices = conn.execute("SELECT * FROM notices ORDER BY id DESC LIMIT 5").fetchall()
    conn.close()

    return render_template("student_dashboard.html", student=student, notices=notices)

# -------- LOGOUT --------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# -------- NOTICES MANAGEMENT --------
from datetime import datetime

@app.route('/manage_notices', methods=['GET', 'POST'])
def manage_notices():
    if 'admin' not in session:
        return redirect('/login')
        
    conn = sqlite3.connect(DATABASE_PATH)
    
    if request.method == 'POST':
        notice_type = request.form['type']
        title = request.form['title']
        content = request.form['content']
        date_posted = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        conn.execute("INSERT INTO notices (type, title, content, date_posted) VALUES (?, ?, ?, ?)",
                     (notice_type, title, content, date_posted))
        conn.commit()
        return redirect('/manage_notices')
        
    notices = conn.execute("SELECT * FROM notices ORDER BY id DESC").fetchall()
    conn.close()
    
    return render_template("manage_notices.html", notices=notices)

@app.route('/delete_notice/<int:id>')
def delete_notice(id):
    if 'admin' not in session:
        return redirect('/login')
        
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("DELETE FROM notices WHERE id=?", (id,))
    conn.commit()
    conn.close()
    
    return redirect('/manage_notices')

if __name__ == '__main__':
    app.run(debug=True)