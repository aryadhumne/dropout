from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

app = Flask(__name__)
app.secret_key = "secret_key_for_flask_sessions"

# ---------------- CONFIG ----------------
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///edudrop.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Mail config (dummy – app will still run)
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "example@gmail.com"
app.config["MAIL_PASSWORD"] = "password"
app.config["MAIL_DEFAULT_SENDER"] = "example@gmail.com"

db = SQLAlchemy(app)
mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)

# ---------------- TEMP STORAGE ----------------
registered_users = []

students = []          # registered students (login)
teachers = []          # FIXED ✅
admins = []            # FIXED ✅
students_data = {} 
principals = []
@app.route('/')
def home():
    return redirect(url_for('login'))
# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form['role']
        password = request.form['password']

        # -------- STUDENT LOGIN (ROLL BASED) --------
        if role == 'student':
            roll = request.form['roll']

            student = next(
                (s for s in students if s['roll'] == roll and s['password'] == password),
                None
            )

            if student:
                session['role'] = 'student'
                session['roll'] = roll
                return redirect(url_for('dashboard_student'))
            else:
                flash("Invalid student credentials", "error")

        # -------- PRINCIPAL LOGIN --------
        elif role == 'principal':
            email = request.form['email']
            principal = next(
                (p for p in principals if p['email'] == email and p['password'] == password),
                None
            )

            if principal:
                session['role'] = 'principal'
                return redirect(url_for('dashboard_principal'))
            else:
                flash("Invalid principal credentials", "error")

        # -------- TEACHER / ADMIN LOGIN --------
        elif role == 'teacher':
            email = request.form['email']
            teacher = next(
                (t for t in teachers if t['email'] == email and t['password'] == password),
                None
            )

            if teacher:
                session['role'] = 'teacher'
                return redirect(url_for('dashboard_teacher'))
            else:
                flash("Invalid teacher credentials", "error")

        elif role == 'admin':
            email = request.form['email']
            admin = next(
                (a for a in admins if a['email'] == email and a['password'] == password),
                None
            )

            if admin:
                session['role'] = 'admin'
                return redirect(url_for('dashboard_admin'))
            else:
                flash("Invalid admin credentials", "error")

    return render_template('login.html')


# ---------------- LANGUAGE SUPPORT ----------------
@app.route('/change-language/<lang>')
def change_language(lang):
    if lang not in ['en', 'hi', 'mr']:
        lang = 'en'
    session['lang'] = lang
    flash(f"Language changed to {'English' if lang=='en' else 'Hindi' if lang=='hi' else 'Marathi'}", "success")
    return redirect(request.referrer or url_for('home'))

@app.context_processor
def inject_language():
    return dict(current_lang=session.get('lang', 'en'))
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        # Check in teachers / principals / volunteers
        user = next((u for u in teachers if u['email'] == email), None) \
            or next((u for u in principals if u['email'] == email), None)

        if not user:
            flash("Email not registered", "error")
            return redirect(url_for('forgot_password'))

        # Store email temporarily (session-based reset)
        session['reset_email'] = email
        flash("Password reset link verified. Set new password.", "success")
        return redirect(url_for('reset_password'))

    return render_template('forgot_password.html')
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_email' not in session:
        flash("Unauthorized access", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':
        password = request.form['password']
        confirm = request.form['confirm']

        if password != confirm:
            flash("Passwords do not match", "error")
            return redirect(url_for('reset_password'))

        if not password.isdigit() or len(password) != 6:
            flash("Password must be exactly 6 digits", "error")
            return redirect(url_for('reset_password'))

        email = session['reset_email']

        # Update password
        for u in teachers + principals:
            if u['email'] == email:
                u['password'] = password

        session.pop('reset_email')
        flash("Password reset successful. Please login.", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html')
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form['role']
        password = request.form['password']

        # -------- STUDENT REGISTRATION --------
        if role == 'student':
            roll = request.form['roll']
            name = request.form['name']

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

        # -------- PRINCIPAL --------
        elif role == 'principal':
            name = request.form['name']
            email = request.form['email']

            if not password.isdigit() or len(password) != 6:
                flash("Principal password must be exactly 6 digits", "error")
                return redirect(url_for('register'))

            principals.append({
                'name': name,
                'email': email,
                'password': password
            })

        # -------- TEACHER / ADMIN --------
        else:
            email = request.form['email']

            if role == 'teacher':
                teachers.append({'email': email, 'password': password})
            elif role == 'admin':
                admins.append({'email': email, 'password': password})

        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

# ---------------- STUDENT DASHBOARD ----------------
@app.route('/student/dashboard')
def dashboard_student():
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    roll = session.get('roll')
    student = students_data.get(roll)

    if not student:
        basic = next((s for s in students if s['roll'] == roll), None)
        return render_template(
            "dashboard_student.html",
            student=basic,
            no_data=True
        )

    return render_template(
        "dashboard_student.html",
        student=student,
        no_data=False
    )
# ---------------- TEACHER DASHBOARD ----------------
@app.route('/dashboard/teacher', methods=['GET', 'POST'])
def dashboard_teacher():
    if session.get('role') != 'teacher':
        flash("Unauthorized access", "error")
        return redirect(url_for('login'))

    # Get the teacher info to pass to template
    email = session.get('teacher_email')
    teacher = next((t for t in teachers if t['email'] == email), None)
    if not teacher:
        teacher = {'email': email, 'name': 'Teacher'}  # fallback

    if request.method == 'POST':
        name = request.form['name']
        roll = request.form['roll']
        standard = request.form['standard']
        division = request.form['division']
        month = request.form['month']
        assignment = request.form['assignment']
        quiz = request.form['quiz']

        subjects = request.form.getlist('subjects[]')
        attendance = request.form.getlist('attendance[]')

        subject_data = []
        total = 0

        for s, a in zip(subjects, attendance):
            if s.strip() and a.strip():
                a = int(a)
                subject_data.append({'name': s.strip(), 'attendance': a})
                total += a

        avg = round(total / len(subject_data), 1) if subject_data else 0

        if avg >= 75 and assignment == "Completed" and quiz in ["Excellent", "Good"]:
            risk = "Low"
        elif avg < 60 or assignment == "Pending" or quiz == "Poor":
            risk = "High"
        else:
            risk = "Medium"

        students_data[roll] = {
            'name': name,
            'roll': roll,
            'standard': standard,
            'division': division,
            'month': month,
            'subjects': subject_data,
            'avg': avg,
            'assignment': assignment,
            'quiz': quiz,
            'risk': risk
        }

        flash("Student data saved successfully", "success")

    # Pass 'teacher' to template to avoid UndefinedError
    return render_template(
        'dashboard_teacher.html',
        teacher=teacher,
        students=students_data.values(),
        no_data=False if students_data else True
    )
@app.route('/dashboard/principal')
def dashboard_principal():
    if session.get('role') != 'principal':
        flash("Unauthorized access", "error")
        return redirect(url_for('login'))

    division_wise = {}
    high_risk_students = []

    for student in students_data.values():
        div = student['division']

        if div not in division_wise:
            division_wise[div] = []

        division_wise[div].append(student)

        if student['risk'] == "High":
            high_risk_students.append(student)

    return render_template(
        "dashboard_principal.html",
        division_wise=division_wise,
        high_risk_students=high_risk_students,
        total_students=len(students_data),
        total_high_risk=len(high_risk_students)
    )
    # ---------------- ABOUT US ----------------
@app.route('/about')
def about_us():
    return render_template('about.html')
@app.route('/logout')
def logout():
     session.clear()
     flash("You have been logged out successfully", "success")
     return redirect(url_for('login'))

@app.route('/student/<roll>')
def student_profile(roll):
    if session.get('role') not in ['principal', 'teacher']:
        flash("Unauthorized access", "error")
        return redirect(url_for('login'))

    student = students_data.get(roll)

    if not student:
        flash("Student not found", "error")
        return redirect(url_for('dashboard_principal'))

    return render_template('student_profile.html', student=student)


# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True, port=5001)