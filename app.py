from flask import Flask, render_template, request, redirect, url_for, flash, session

from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
app = Flask(__name__)
app.secret_key = "secret_key_for_flask_sessions"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///edudrop.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
# ---------------- TEMPORARY STORAGE ----------------
registered_users = []     # for login/register
students = []  
students_data = {}  # key = roll number
# for teacher dashboard student records

# ---------------- HOME / INDEX ----------------
@app.route('/')
# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form['role']
        password = request.form['password']

        # -------- STUDENT LOGIN --------
        if role == 'student':
            roll = request.form['roll']
            name = request.form['name']

            student = next(
                (s for s in students
                 if s['roll'] == roll
                 and s['name'].lower() == name.lower()
                 and s['password'] == password),
                None
            )

            if student:
                session['role'] = 'student'
                session['roll'] = roll
                return redirect(url_for('dashboard_student'))
            else:
                flash("Invalid student credentials", "error")

        # -------- TEACHER LOGIN --------
        elif role == 'teacher':
            email = request.form['email']

            if any(t for t in teachers if t['email'] == email and t['password'] == password):
                session['role'] = 'teacher'
                return redirect(url_for('dashboard_teacher'))
            flash("Invalid teacher credentials", "error")

        # -------- ADMIN LOGIN --------
        elif role == 'admin':
            email = request.form['email']

            if any(a for a in admins if a['email'] == email and a['password'] == password):
                session['role'] = 'admin'
                return redirect(url_for('dashboard_admin'))
            flash("Invalid admin credentials", "error")

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form['role']
        password = request.form['password']

        # ---- STUDENT REGISTRATION ----
        if role == 'student':
            roll = request.form['roll']
            name = request.form['name']

            # 6-digit password validation
            if not password.isdigit() or len(password) != 6:
                flash("Student password must be exactly 6 digits", "error")
                return redirect(url_for('register'))

            if any(s for s in students if s['roll'] == roll):
                flash("Student already registered", "error")
                return redirect(url_for('register'))

            students.append({
                'roll': roll,
                'name': name,
                'password': password
            })

        # ---- TEACHER / ADMIN REGISTRATION ----
        else:
            email = request.form['email']

            if role == 'teacher':
                teachers.append({'email': email, 'password': password})
            elif role == 'admin':
                admins.append({'email': email, 'password': password})

        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        roll = request.form['roll']
        name = request.form['name']

        student = next(
            (s for s in students if s['roll'] == roll and s['name'].lower() == name.lower()),
            None
        )

        if student:
            return redirect(url_for('student_dashboard', roll=roll))
        else:
            flash("❌ Student record not found. Contact your teacher.", "error")

    return render_template('student_login.html')
@app.route('/student/dashboard')
def dashboard_student():
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('login'))

    roll = session.get('roll')
    student = students_data.get(roll)

    if not student:
        return render_template("dashboard_student.html", no_data=True)

    return render_template(
        "dashboard_student.html",
        student=student,
        no_data=False
    )
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")

        user = (
            Teacher.query.filter_by(email=email).first()
            or Volunteer.query.filter_by(email=email).first()
            or Coordinator.query.filter_by(email=email).first()
        )

        if not user:
            flash("Email not registered")
            return redirect(url_for("forgot_password"))

        token = serializer.dumps(email, salt="password-reset")

        reset_link = url_for(
            "reset_password",
            token=token,
            _external=True,
            _scheme="https"
        )

        msg = Message(
            subject="EduDrop Password Reset",
            recipients=[email],
            body=f"Click the link to reset your password:\n{reset_link}"
        )
        mail.send(msg)

        flash("Password reset link sent to your email")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        email = serializer.loads(token, salt="password-reset", max_age=900)  # 15 min
    except:
        flash("Invalid or expired link")
        return redirect(url_for("login"))

    if request.method == "POST":
        new_password = request.form.get("password")
        confirm = request.form.get("confirm")

        if new_password != confirm:
            flash("Passwords do not match")
            return redirect(request.url)

        user = User.query.filter_by(email=email).first()
        user.password = generate_password_hash(new_password)
        db.session.commit()

        flash("Password reset successful")
        return redirect(url_for("login"))

    return render_template("reset_password.html")
@app.route('/dashboard/admin')
def dashboard_admin():
    total_students = len(students)
    high_risk = len([s for s in students if s['risk'] == 'High'])

    return render_template(
        'dashboard_admin.html',
        students=students,
        total=total_students,
        high_risk=high_risk
    )
@app.route('/dashboard/teacher', methods=['GET', 'POST'])
def dashboard_teacher():
    if 'role' not in session or session['role'] != 'teacher':
        flash("Unauthorized access", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':

        # -------- BASIC STUDENT INFO --------
        name = request.form['name']
        roll = request.form['roll']
        standard = request.form['standard']
        division = request.form['division']
        month = request.form['month']

        assignment = request.form['assignment']
        quiz = request.form['quiz']

        # -------- SUBJECT & ATTENDANCE (DYNAMIC) --------
        subjects = request.form.getlist('subjects[]')
        attendance = request.form.getlist('attendance[]')

        subject_data = []
        total = 0

        for s, a in zip(subjects, attendance):
            if s.strip() and a.strip():
                a = int(a)
                subject_data.append({
                    'name': s.strip(),          # dynamic subject
                    'attendance': a
                })
                total += a

        avg_attendance = round(total / len(subject_data), 1) if subject_data else 0

        # -------- DROPOUT RISK LOGIC --------
        if avg_attendance >= 75 and assignment == "Completed" and quiz in ["Excellent", "Good"]:
            risk = "Low"
        elif avg_attendance < 60 or assignment == "Pending" or quiz == "Poor":
            risk = "High"
        else:
            risk = "Medium"

        # -------- STORE / UPDATE STUDENT (CENTRALIZED) --------
        students_data[roll] = {
            'name': name,
            'roll': roll,
            'standard': standard,
            'division': division,
            'month': month,
            'subjects': subject_data,
            'avg': avg_attendance,
            'assignment': assignment,
            'quiz': quiz,
            'risk': risk
        }

        flash("✅ Student data saved successfully!", "success")

    # Send all students to teacher dashboard (optional list view)
    return render_template(
        'dashboard_teacher.html',
        students=students_data.values()
    )



# ---------------- VOLUNTEER DASHBOARD ----------------
@app.route('/dashboard/volunteer')
def dashboard_volunteer():
    return render_template('dashboard_volunteer.html')

# ---------------- COORDINATOR DASHBOARD ----------------
@app.route('/dashboard/coordinator')
def dashboard_coordinator():
    return render_template('dashboard_coordinator.html')

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True, port=5001)