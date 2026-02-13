from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mail import Mail
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv
import os
from supabase_client import supabase
from werkzeug.security import generate_password_hash, check_password_hash
# ---------------- TEMP IN-MEMORY STORAGE ----------------
students_data = {}
ngo_interventions = {}
# ---------------- APP INIT ----------------
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or "supersecretkey"
# ---------------- MAIL CONFIG ----------------
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "example@gmail.com"
app.config["MAIL_PASSWORD"] = "password"
app.config["MAIL_DEFAULT_SENDER"] = "example@gmail.com"

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)
# ---------------- HOME ----------------
@app.route('/')
def home():
    return redirect(url_for('login'))
# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('role', '').lower()
        password = request.form.get('password', '')

        if not role or not password:
            flash("Please fill all required fields", "error")
            return redirect(url_for('login'))

        try:
            # ---------------- STUDENT LOGIN ----------------
            if role == 'student':
                roll = request.form.get('roll', '').strip()
                if not roll:
                    flash("Roll number is required", "error")
                    return redirect(url_for('login'))

                res = supabase.table("users") \
                    .select("*") \
                    .eq("role", "student") \
                    .eq("roll", roll) \
                    .execute()

                if not res.data:
                    flash("Invalid student credentials", "error")
                    return redirect(url_for('login'))

                user = res.data[0]
                if not check_password_hash(user['password'], password):
                    flash("Invalid student credentials", "error")
                    return redirect(url_for('login'))

                session.clear()
                session['role'] = 'student'
                session['roll'] = roll
                flash("Login successful!", "success")
                return redirect(url_for('dashboard_student'))

            # ---------------- OTHER ROLES (EMAIL LOGIN) ----------------
            else:
                email = request.form.get('email', '').strip().lower()
                if not email:
                    flash("Email is required", "error")
                    return redirect(url_for('login'))

                res = supabase.table("users") \
                    .select("*") \
                    .eq("role", role) \
                    .eq("email", email) \
                    .execute()

                if not res.data:
                    flash("Invalid credentials", "error")
                    return redirect(url_for('login'))

                user = res.data[0]
                if not check_password_hash(user['password'], password):
                    flash("Invalid credentials", "error")
                    return redirect(url_for('login'))

                session.clear()
                session['role'] = role
                session['email'] = email

                redirect_map = {
                    "teacher": "dashboard_teacher",
                    "principal": "dashboard_principal",
                    "volunteer": "dashboard_volunteer",
                    "admin": "dashboard_admin"
                }

                flash("Login successful!", "success")
                return redirect(url_for(redirect_map.get(role, 'login')))

        except Exception as e:
            print("LOGIN ERROR:", e)
            flash("Login failed. Please try again.", "error")

    return render_template('login.html')
# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form.get('role', '').lower()
        raw_password = request.form.get('password', '')

        if not raw_password.isdigit() or len(raw_password) != 6:
            flash("Password must be exactly 6 digits", "error")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(raw_password)
        data = {"role": role, "password": hashed_password}

      
        if role == "student":
            roll = request.form.get('roll', '').strip()
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip().lower()

            if not roll or not name or not email:
                    flash("Roll, Name and Email are required", "error")
                    return redirect(url_for('register'))

            existing_roll = supabase.table("users").select("*").eq("roll", roll).execute()
            if existing_roll.data:
                    flash("Roll number already registered", "error")
                    return redirect(url_for('register'))

            existing_email = supabase.table("users").select("*").eq("email", email).execute()
            if existing_email.data:
                    flash("Email already registered", "error")
                    return redirect(url_for('register'))

            data["roll"] = roll
            data["name"] = name
            data["email"] = email

 # ---------- OTHER ROLES ----------
        else:
            email = request.form.get('email', '').strip().lower()
            name = request.form.get('name', '').strip()   # ✅ FIXED

            if not email or not name:
                flash("Email and Name are required", "error")
                return redirect(url_for('register'))

            existing = supabase.table("users").select("*").eq("email", email).execute()
            if existing.data:
                flash("Email already registered", "error")
                return redirect(url_for('register'))

            data["email"] = email
            data["name"] = name

        try:
            supabase.table("users").insert(data).execute()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))

        except Exception as e:
            print("REGISTER ERROR:", e)
            flash("Registration failed", "error")
            return redirect(url_for('register'))

    return render_template('register.html')
# ---------------- FORGOT PASSWORD ----------------
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        res = supabase.table("users").select("*").eq("email", email).execute()

        if not res.data:
            flash("Email not registered", "error")
            return redirect(url_for('forgot_password'))

        session['reset_email'] = email
        return redirect(url_for('reset_password'))

    return render_template('forgot_password.html')
# ---------------- RESET PASSWORD ----------------
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_email' not in session:
        flash("Unauthorized access", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if password != confirm:
            flash("Passwords do not match", "error")
            return redirect(url_for('reset_password'))

        hashed = generate_password_hash(password)

        supabase.table("users") \
            .update({"password": hashed}) \
            .eq("email", session['reset_email']) \
            .execute()

        session.pop('reset_email')
        flash("Password reset successful", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html')
# ---------------- STUDENT DASHBOARD ----------------
# ---------------- STUDENT DASHBOARD ----------------
@app.route('/student/dashboard')
def dashboard_student():
    if session.get('role') != 'student':
        flash("Please login first", "error")
        return redirect(url_for('login'))

    roll = str(session.get('roll')).strip()

    # Fetch student basic info
    user_res = supabase.table("users") \
        .select("*") \
        .eq("role", "student") \
        .eq("roll", roll) \
        .execute()

    student = user_res.data[0] if user_res.data else None

    # Fetch teacher-added data
    perf_res = supabase.table("student_performance") \
        .select("*") \
        .eq("roll", roll) \
        .execute()

    performance = perf_res.data if perf_res.data else []

    return render_template(
        "dashboard_student.html",
        student=student,
        performance=performance
    )
# ---------------- TEACHER DASHBOARD ----------------
@app.route('/teacher/dashboard')
def dashboard_teacher():
    if session.get('role') != 'teacher':
        flash("Unauthorized access", "error")
        return redirect(url_for('login'))

    email = session.get('email')

    teacher_res = supabase.table("users") \
        .select("*") \
        .eq("role", "teacher") \
        .eq("email", email) \
        .execute()

    teacher = teacher_res.data[0] if teacher_res.data else None

    # ❌ removed .order("roll")
    students_res = supabase.table("student_performance") \
        .select("*") \
        .execute()

    students = students_res.data if students_res.data else []

    return render_template(
        "dashboard_teacher.html",
        teacher=teacher,
        students=students
    )

@app.route('/teacher/add_student', methods=['POST'])
def add_student():
    student_id = request.form.get('student_id')  # hidden field for editing
    name = request.form['name']
    roll = request.form['roll']
    standard = request.form['standard']
    division = request.form['division']
    month = request.form['month']
    assignment = request.form['assignment']
    quiz = request.form['quiz']

    # Collect subjects & attendance
    subjects = request.form.getlist('subjects[]')
    attendance = request.form.getlist('attendance[]')
    subject_data = [{"name": s, "attendance": int(a)} for s, a in zip(subjects, attendance)]
    
    avg = sum(int(a) for a in attendance)/len(attendance) if attendance else 0
    if avg < 60:
        risk = "At Risk"
    elif avg < 75:
        risk = "Medium"
    else:
        risk = "Safe"



    if student_id:  # Edit existing student
        supabase.table("student_performance") \
            .update({
                "name": name,
                "roll": roll,
                "standard": standard,
                "division": division,
                "month": month,
                "subjects": subject_data,
                "avg": avg,
                "assignment": assignment,
                "quiz": quiz,
                "risk": risk
            }) \
            .eq("id", student_id).execute()
        flash("Student updated successfully!", "success")
    else:  # Add new student
        supabase.table("student_performance").insert({
            "name": name,
            "roll": roll,
            "standard": standard,
            "division": division,
            "month": month,
            "subjects": subject_data,
            "avg": avg,
            "assignment": assignment,
            "quiz": quiz,
            "risk": risk
        }).execute()
        flash("Student added successfully!", "success")
    
    return redirect(url_for('dashboard_teacher'))

@app.route('/about')
def about():
    return render_template('about.html')  # Make sure about.html exists in templates/
@app.route('/principal/dashboard')
def principal_dashboard():
    if session.get('role') != 'principal':
        flash("Unauthorized access", "error")
        return redirect(url_for('login'))

    students = supabase.table("student_performance").select("*").execute().data or []

    division_wise = {}
    high_risk_students = []

    for s in students:
        division = s.get("division", "Unknown")
        avg = s.get("avg", 0)

        if avg < 60:
            risk = "High"
        elif avg < 75:
            risk = "Medium"
        else:
            risk = "Low"

        s["risk"] = risk
        division_wise.setdefault(division, []).append(s)

        if risk == "High":
            high_risk_students.append(s)

    return render_template(
        "dashboard_principal.html",   # ✅ YOUR FILE
        division_wise=division_wise,
        high_risk_students=high_risk_students
    )

# ---------------- VOLUNTEER DASHBOARD ----------------
@app.route('/volunteer/dashboard', methods=['GET', 'POST'])
def dashboard_volunteer():
    if session.get('role') != 'volunteer':
        flash("Unauthorized access", "error")
        return redirect(url_for('login'))

    email = session.get('email')

    # Fetch volunteer info
    volunteer_res = supabase.table("users") \
        .select("*") \
        .eq("role", "volunteer") \
        .eq("email", email) \
        .execute()

    volunteer = volunteer_res.data[0] if volunteer_res.data else None

    # ---------------- Handle form submit for adding an intervention ----------------
    if request.method == 'POST':
        try:
            student_id = request.form.get('student_id')
            intervention_type = request.form.get('intervention_type', '').strip()
            status = request.form.get('status', '').strip()
            notes = request.form.get('notes', '').strip()

            # Minimal validation
            if not student_id or not status:
                flash("Student and status are required", "error")
                return redirect(url_for('dashboard_volunteer'))

            # Insert into ngo_interventions (adjust column names if your table differs)
            supabase.table("ngo_interventions").insert({
                "student_id": student_id,
                "type": intervention_type,
                "status": status,
                "notes": notes,
                "by": email
            }).execute()

            flash("Intervention saved", "success")
            return redirect(url_for("dashboard_volunteer"))
        except Exception as e:
            print("VOLUNTEER POST ERROR:", e)
            flash("Failed to save intervention", "error")
            return redirect(url_for("dashboard_volunteer"))

    # ---------------- GET: fetch only students with risk = "At Risk" OR "Medium" ----------------
    try:
        # Preferred: server-side filter (fast)
        students_res = supabase.table("student_performance") \
            .select("*") \
            .in_("risk", ["At Risk", "Medium"]) \
            .execute()

        students = students_res.data if students_res.data else []

    except Exception as e:
        # Fallback: client-side filter if .in_() is not supported by your client
        print("Supabase .in_() may not be supported; falling back. Error:", e)
        all_res = supabase.table("student_performance").select("*").execute()
        all_students = all_res.data if all_res.data else []
        students = [s for s in all_students if s.get("risk") in ("At Risk", "Medium")]

    # Fetch interventions history
    interventions_res = supabase.table("ngo_interventions") \
        .select("*") \
        .order("visit_date", desc=True) \
        .execute()

    interventions = interventions_res.data if interventions_res.data else []

    return render_template(
        "dashboard_volunteer.html",
        volunteer=volunteer,
        students=students,
        interventions=interventions
    )

# ---------------- ADMIN DASHBOARD ----------------
@app.route('/admin/dashboard')
def dashboard_admin():
    if session.get('role') != 'admin':
        flash("Unauthorized access", "error")
        return redirect(url_for('login'))

    email = session.get('email')
    res = supabase.table("users").select("*").eq("role", "admin").eq("email", email).execute()
    admin = res.data[0] if res.data else None

    return render_template("dashboard_admin.html", admin=admin)

# ===== DELETE STUDENT =====
@app.route('/delete_student/<int:roll>', methods=['POST'])
def delete_student(roll):
    # Delete student by roll number
    supabase.table("student_performance").delete().eq("roll", roll).execute()
    return '', 200

# ===== UPDATE STUDENT =====
@app.route('/update_student', methods=['POST'])
def update_student():
    roll = request.form.get('roll')
    name = request.form.get('name')
    standard = request.form.get('standard')
    division = request.form.get('division')
    month = request.form.get('month')

    # Update student data
    supabase.table("student_performance").update({
        "name": name,
        "standard": standard,
        "division": division,
        "month": month
    }).eq("roll", roll).execute()

    return '', 200

# ===== ADDITIONAL: Parent call & escalation logic =====
def check_attendance_risk(student):
    # Suppose avg < 75% is low
    if student['avg'] < 75:
        parent_calls = student.get('parent_calls', 0)
        if parent_calls < 2:
            # increment parent call
            supabase.table("student_performance").update({
                "parent_calls": parent_calls + 1
            }).eq("roll", student['roll']).execute()
            print(f"Parent called for student {student['name']}")
        else:
            # escalate to principal
            supabase.table("student_performance").update({
                "status": "Escalated"
            }).eq("roll", student['roll']).execute()
            print(f"Escalated to principal: {student['name']}")

# ===== Example: run this check for all students =====
@app.route('/check_risks')
def check_risks():
    students = supabase.table("student_performance").select("*").execute().data
    for student in students:
        check_attendance_risk(student)
    return "Risk check complete"
# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for('login'))
# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True, port=8000)