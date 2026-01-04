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
        email = request.form['email'].strip()
        password = request.form['password'].strip()
        role = request.form['role'].strip()

        user = next(
            (u for u in registered_users
             if u['email'] == email and u['password'] == password and u['role'] == role),
            None
        )

        if user:
            if role == 'teacher':
                return redirect(url_for('dashboard_teacher'))
            elif role == 'volunteer':
                return redirect(url_for('dashboard_volunteer'))
            elif role == 'coordinator':
                return redirect(url_for('dashboard_coordinator'))
            elif role == 'student':
                return redirect(url_for('dashboard_student'))
        else:
            flash("Invalid credentials or role.", "error")

    return render_template('login.html')

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password'].strip()
        role = request.form['role'].strip()

        if any(u['email'] == email for u in registered_users):
            flash("User already exists. Please login.", "error")
        else:
            registered_users.append({
                'email': email,
                'password': password,
                'role': role
            })
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))

    return render_template('register.html')
@app.route('/dashboard/student')
def dashboard_student():
    return render_template('dashboard_student.html')

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
