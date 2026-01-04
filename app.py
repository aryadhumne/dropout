from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "secret_key_for_flask_sessions"

# ---------------- TEMPORARY STORAGE ----------------
registered_users = []     # for login/register
students = []             # for teacher dashboard student records

# ---------------- HOME / INDEX ----------------
@app.route('/')

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form['role']

        # -------- STUDENT LOGIN --------
        if role == 'student':
            roll = request.form['roll']
            name = request.form['name']

            student = next(
                (s for s in students if s['roll'] == roll and s['name'].lower() == name.lower()),
                None
            )

            if student:
                session['role'] = 'student'
                session['roll'] = roll
                return redirect(url_for('dashboard_student'))
            else:
                flash("Student record not found. Contact teacher.", "error")

        # -------- TEACHER LOGIN --------
        elif role == 'teacher':
            email = request.form['email']
            password = request.form['password']

            if any(t for t in teachers if t['email'] == email and t['password'] == password):
                session['role'] = 'teacher'
                return redirect(url_for('dashboard_teacher'))
            flash("Invalid teacher credentials", "error")

        # -------- ADMIN LOGIN --------
        elif role == 'admin':
            email = request.form['email']
            password = request.form['password']

            if any(a for a in admins if a['email'] == email and a['password'] == password):
                session['role'] = 'admin'
                return redirect(url_for('dashboard_admin'))
            flash("Invalid admin credentials", "error")

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form['role']
        email = request.form['email']
        password = request.form['password']

        if role not in ['teacher', 'admin']:
            flash("Students cannot register.", "error")
            return redirect(url_for('register'))

        if role == 'teacher':
            teachers.append({'email': email, 'password': password})
        else:
            admins.append({'email': email, 'password': password})

        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


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
@app.route('/student/dashboard/<roll>')
def student_dashboard(roll):
    student = next((s for s in students if s['roll'] == roll), None)

    if not student:
        return redirect(url_for('student_login'))

    return render_template('student_dashboard.html', student=student)
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
    if request.method == 'POST':

        # -------- BASIC STUDENT INFO --------
        name = request.form['name']
        roll = request.form['roll']
        standard = request.form['standard']
        division = request.form['division']
        month = request.form['month']

        assignment = request.form['assignment']
        quiz = request.form['quiz']

        # -------- SUBJECT & ATTENDANCE --------
        subjects = request.form.getlist('subjects[]')
        attendance = request.form.getlist('attendance[]')

        subject_data = []
        total = 0
        count = 0

        for s, a in zip(subjects, attendance):
            if s.strip() and a.strip():
                a = int(a)
                subject_data.append({
                    'subject': s,
                    'attendance': a
                })
                total += a
                count += 1

        # Prevent division by zero
        avg_attendance = round(total / count, 1) if count > 0 else 0

        # -------- DROPOUT RISK LOGIC --------
        if avg_attendance >= 75 and assignment == "Completed" and quiz in ["Excellent", "Good"]:
            risk = "Low"
        elif avg_attendance < 60 or assignment == "Pending" or quiz == "Poor":
            risk = "High"
        else:
            risk = "Medium"

        # -------- STORE STUDENT --------
        student = {
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

        students.append(student)
        flash("✅ Student added successfully!", "success")

    return render_template('dashboard_teacher.html', students=students)


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