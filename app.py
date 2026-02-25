from flask import (
    Flask, render_template, request,
    redirect, url_for, flash,
    session, send_file
)
from flask_mail import Mail
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from supabase_client import supabase

import os
import sqlite3
import io
import pandas as pd
from reportlab.pdfgen import canvas
from flask import jsonify
from supabase import create_client
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


from twilio.rest import Client
def calculate_dropout_probability(risk_score):
    
    if risk_score >= 80:
        return 85
    elif risk_score >= 60:
        return 60
    elif risk_score >= 40:
        return 35
    else:
        return 10


def send_sms(to_number, student_name, risk_score):

    account_sid = "YOUR_SID"
    auth_token = "YOUR_TOKEN"

    client = Client(account_sid, auth_token)

    client.messages.create(
        body=f"Alert: {student_name} risk level is {risk_score}%. Please contact school.",
        from_="+YOUR_TWILIO_NUMBER",
        to=to_number
    )


def calculate_risk(avg_attendance, assignment_status, behaviour):

    score = 0

    # Attendance (50% weight)
    if avg_attendance < 60:
        score += 50
    elif avg_attendance < 75:
        score += 30
    else:
        score += 10

    # Assignment (30% weight)
    if assignment_status == "Not Completed":
        score += 30
    else:
        score += 5

    # Behaviour (20% weight)
    if behaviour == "Poor":
        score += 20
    elif behaviour == "Average":
        score += 10
    else:
        score += 5

    return min(score, 100)


# ---------------- APP INIT ----------------
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

# ---------------- MAIL CONFIG ----------------
app.config.update(
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME="example@gmail.com",
    MAIL_PASSWORD="password",
    MAIL_DEFAULT_SENDER="example@gmail.com"
)

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)

# ---------------- HOME ----------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/select_role')
def select_role():
    return render_template('select_role.html')
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
            return redirect(url_for('select_role'))
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
@app.route('/about')
def about():
    return render_template('about.html')

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
        return redirect(url_for('select_role'))


    return render_template('reset_password.html')
@app.route('/login/<role>', methods=['GET', 'POST'])
def role_login(role):

    # Map role to template name
    template_map = {
        "student": "student_login.html",
        "teacher": "teacher_login.html",
        "principal": "principal_login.html",
        "ngo": "ngo_login.html",
        "admin": "admin_login.html"
    }

    if role not in template_map:
        return "Invalid Role", 404

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email and password:
            session["user"] = email
            session["role"] = role

            if role == "student":
                return redirect(url_for("dashboard"))
            elif role == "teacher":
                return redirect(url_for("teacher_dashboard"))

            elif role == "principal":
                return redirect(url_for("principal_dashboard"))
            elif role == "ngo":
                return redirect(url_for("volunteer_dashboard"))
           

    return render_template(template_map[role])


# ---------------- STUDENT DASHBOARD ----------------
@app.route('/student/dashboard')
def dashboard_student():

    if session.get('role') != 'student':
        return redirect(url_for('student_login'))

    student_id = session.get('student_id')

    # Get student account
    student_account = supabase.table("students") \
        .select("*") \
        .eq("id", student_id) \
        .execute()

    if not student_account.data:
        flash("Account not found", "danger")
        return redirect(url_for('student_login'))

    performance_id = student_account.data[0]["student_performance_id"]

    # Fetch performance data
    performance = supabase.table("student_performance") \
        .select("*") \
        .eq("id", performance_id) \
        .execute()

    if not performance.data:
        flash("Performance data not found", "danger")
        return redirect(url_for('student_login'))

    return render_template(
        "student/dashboard.html",
        performance=performance.data,
        no_data=False
    )




@app.route('/student/register', methods=['GET', 'POST'])
def student_register():

    if request.method == 'POST':

        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # 1️⃣ Password match check
        if password != confirm_password:
            return "Passwords do not match"

        try:
            # 2️⃣ Check if teacher added this student
            teacher_record = supabase.table("student_performance") \
                .select("*") \
                .eq("email", email) \
                .execute()

            if not teacher_record.data:
                return "This email is not registered by teacher."

            # 3️⃣ Check if already registered
            existing = supabase.table("students") \
                .select("*") \
                .eq("email", email) \
                .execute()

            if existing.data:
                return "Student already registered. Please login."

            # 4️⃣ Insert into students table
            supabase.table("students").insert({
                "email": email,
                "password": generate_password_hash(password),
                "student_performance_id": teacher_record.data[0]["id"]
            }).execute()


            return redirect('/student/login')

        except Exception as e:
            return str(e)

    return render_template("student_register.html")


@app.route('/student/login', methods=['GET', 'POST'])
def student_login():

    if request.method == 'POST':

        email = request.form.get("email")
        password = request.form.get("password")

        try:
            user = supabase.table("students") \
                .select("*") \
                .eq("email", email) \
                .execute()

            if not user.data:
                return "Invalid Email or Password"

            stored_hash = user.data[0]['password']

            if not check_password_hash(stored_hash, password):
                return "Invalid Email or Password"

            # Store student ID (IMPORTANT)
            session['student_id'] = user.data[0]['id']
            session['role'] = "student"

            return redirect('/student/dashboard')

        except Exception as e:
            return str(e)

    return render_template("student_login.html")


@app.route('/teacher/dashboard')
def teacher_dashboard():

    if session.get('role') != 'teacher':
        return redirect(url_for('index'))

    response = supabase.table("student_performance").select("*").execute()
    students = response.data

    total_students = len(students)

    high_risk = len([
    s for s in students
    if (s.get("risk_score") or 0) >= 60
])

    medium_risk = len([s for s in students if 40 <= s.get("risk_score", 0) < 60])
    low_risk = len([s for s in students if s.get("risk_score", 0) < 40])

    # Standard-wise risk
    standards = sorted(set(s["standard"] for s in students))
    standard_risk_counts = []

    for std in standards:
        count = len([
            s for s in students 
            if s["standard"] == std and s.get("risk_score", 0) >= 40
        ])
        standard_risk_counts.append(count)

    return render_template(
        "teacher/dashboard.html",
        total_students=total_students,
        high_risk=high_risk,
        medium_risk=medium_risk,
        low_risk=low_risk,
        standards=standards,
        standard_risk_counts=standard_risk_counts
    )
@app.route('/teacher/add_student', methods=['GET', 'POST'])
def add_student():

    if session.get('role') != 'teacher':
        return redirect(url_for('index'))

    if request.method == 'POST':

        # -------------------------
        # Basic Details
        # -------------------------
        name = request.form.get('name')
        roll = request.form.get('roll')
        standard = request.form.get('standard')
        division = request.form.get('division')
        gender = request.form.get('gender')
        email = request.form.get('email')
        parent_email = request.form.get('parent_email')

        # -------------------------
        # Parent Details
        # -------------------------
        parent_name = request.form.get('parent_name')
        parent_phone = request.form.get('parent_phone')
        parent_alt_phone = request.form.get('parent_alt_phone')
        parent_address = request.form.get('parent_address')

        # -------------------------
        # Academic Data
        # -------------------------
        attendance = int(request.form.get("attendance") or 0)
        monthly_test_score = int(request.form.get('monthly_test_score') or 0)

        assignment_status = request.form.get("assignment_status")
        quiz_status = request.form.get("quiz_performance")

        behaviour = request.form.get("behaviour")
        month = request.form.get("month")

        # -------------------------
        # Validation
        # -------------------------
        if not name or not email:
            flash("Name and Email required", "danger")
            return redirect(url_for('add_student'))

        # -------------------------
        # Duplicate Check
        # -------------------------
        existing = supabase.table("student_performance") \
            .select("id") \
            .eq("email", email) \
            .eq("is_deleted", False) \
            .execute()

        if existing.data:
            flash("Student with this email already exists", "danger")
            return redirect(url_for('add_student'))

        # -------------------------
        # Convert Status → Score
        # -------------------------

        # Assignment conversion
        if assignment_status == "Completed":
            assignment_score = 100
        elif assignment_status == "Pending":
            assignment_score = 50
        else:
            assignment_score = 0

        # Quiz conversion
        if quiz_status == "Good":
            quiz_score = 100
        elif quiz_status == "Average":
            quiz_score = 50
        else:
            quiz_score = 0

        # -------------------------
        # Risk Calculation
        # -------------------------
        risk_score = 0
        risk_reason = []

        if monthly_test_score < 35:
            risk_score += 40
            risk_reason.append("Low Monthly Score")

        if attendance < 60:
            risk_score += 30
            risk_reason.append("Low Attendance")

        if assignment_score < 50:
            risk_score += 15
            risk_reason.append("Low Assignment")

        if quiz_score < 50:
            risk_score += 15
            risk_reason.append("Low Quiz")

        risk_status = "At Risk" if risk_score >= 60 else "Safe"

        # -------------------------
        # Insert Data
        # -------------------------
        insert_data = {
            "name": name,
            "roll": roll,
            "standard": standard,
            "division": division,
            "gender": gender,
            "email": email,
            "parent_email": parent_email,
            "monthly_test_score": monthly_test_score,
            "attendance": attendance,

            # Store both status & score
            "assignment_status": assignment_status,
            "assignment_score": assignment_score,
            "quiz_status": quiz_status,
            "quiz_score": quiz_score,

            "behaviour": behaviour,
            "month": month,

            "risk_score": risk_score,
            "risk_reason": ", ".join(risk_reason),
            "risk_status": risk_status,

            "parent_name": parent_name,
            "parent_phone": parent_phone,
            "parent_alt_phone": parent_alt_phone,
            "parent_address": parent_address,
            "is_deleted": False
        }

        try:
            response = supabase.table("student_performance") \
                .insert(insert_data) \
                .execute()

            if response.data:
                flash("Student Added Successfully", "success")
                return redirect(url_for('student_records'))
            else:
                flash("Insert failed. Check Supabase RLS.", "danger")
                return redirect(url_for('add_student'))

        except Exception as e:
            print("INSERT FAILED:", str(e))
            flash("Error adding student.", "danger")
            return redirect(url_for('add_student'))

    return render_template("teacher/add_student.html")
@app.route('/teacher/student_records')
def student_records():

    if session.get('role') != 'teacher':
        return redirect(url_for('index'))

    # ✅ FIXED ORDER COLUMN
    response = supabase.table("student_performance") \
        .select("*") \
        .execute()

    students = response.data or []

    print("RAW RESPONSE:", response)
    print("FETCHED STUDENTS:", students)



    # ---------------- FIX RISK DATA ----------------
    for s in students:

        # Derive risk_status if missing
        if not s.get("risk_status"):
            if s.get("risk") == "At Risk":
                s["risk_status"] = "At Risk"
                s["risk_score"] = 60
            else:
                s["risk_status"] = "Safe"
                s["risk_score"] = 10

        # Safety fallback
        if s.get("risk_score") is None:
            s["risk_score"] = 0

    # ---------------- RISK COUNTS ----------------
    high_risk = len([s for s in students if s.get("risk_status") == "At Risk"])
    medium_risk = len([s for s in students if 40 <= s.get("risk_score", 0) < 60])
    low_risk = len([s for s in students if s.get("risk_score", 0) < 40])

    # ---------------- GROUP BY CLASS & DIVISION ----------------
    grouped = {}

    for s in students:
        standard = s.get("standard") or "Unknown"
        division = s.get("division") or "Unknown"

        key = f"Class {standard} - {division}"

        if key not in grouped:
            grouped[key] = []

        grouped[key].append(s)

    return render_template(
        "teacher/student_records.html",
        grouped=grouped,
        high_risk=high_risk,
        medium_risk=medium_risk,
        low_risk=low_risk
    )

@app.route('/teacher/delete_student/<student_id>', methods=['POST'])
def delete_student(student_id):

    if session.get('role') != 'teacher':
        return jsonify({"error": "Unauthorized"}), 403

    supabase.table("student_performance") \
        .update({"is_deleted": True}) \
        .eq("id", student_id) \
        .execute()

    return jsonify({"success": True})


# ===============================
# EDIT
# ===============================
@app.route('/teacher/edit_student/<student_id>', methods=['GET', 'POST'])
def edit_student(student_id):

    if request.method == 'POST':

        name = request.form['name']
        parent_phone = request.form['parent_phone']

        supabase.table("student_performance").update({
            "name": name,
            "parent_phone": parent_phone
        }).eq("id", student_id).execute()

        return redirect(url_for('student_records'))

    student = supabase.table("student_performance").select("*").eq("id", student_id).execute().data[0]

    return render_template("teacher/edit_student.html", student=student)

@app.route("/dashboard/principal", methods=["GET", "POST"])
def dashboard_principal():

    from datetime import datetime, timedelta

    selected_class = request.args.get("class_filter")
    selected_risk = request.args.get("risk_filter")
    selected_gender = request.args.get("gender_filter")

    response = supabase.table("students").select("*").execute()
    rows = response.data or []

    filtered_rows = []

    # ---------- FILTER ----------
    for r in rows:
        cls = r.get("class")
        gender = (r.get("gender") or "").lower()

        if selected_class and cls != selected_class:
            continue
        if selected_gender and gender != selected_gender.lower():
            continue

        filtered_rows.append(r)

    total_students = len(filtered_rows)
    high_risk = 0
    medium_risk = 0
    total_att = 0

    classes = {}
    boys_risk = 0
    girls_risk = 0

    red_flag_students = []
    students = []

    # ---------- MAIN LOOP ----------
    for r in filtered_rows:

        roll = r.get("roll")
        name = r.get("name")
        cls = r.get("class")

        gender = str(r.get("gender") or "Not Set")
        gender_lower = gender.strip().lower()

        att = int(r.get("attendance") or 0)
        marks = int(r.get("marks") or 0)

        total_att += att
        classes.setdefault(cls, 0)

        # ---------- RISK LOGIC ----------
        if att < 75 or marks < 40:
            risk = "High"
            high_risk += 1
            classes[cls] += 1
            red_flag_students.append(name)

            if gender_lower == "male":
                boys_risk += 1
            elif gender_lower == "female":
                girls_risk += 1

        elif att < 85 or marks < 55:
            risk = "Medium"
            medium_risk += 1
        else:
            risk = "Low"

        if selected_risk and risk != selected_risk:
            continue

        # ---------- EXPLAINABLE AI LOGIC ----------
        reason = ""
        suggested_action = ""

        if risk == "High":
            if att < 75 and marks < 40:
                reason = f"Low attendance ({att}%) and Low marks ({marks})"
            elif att < 75:
                reason = f"Low attendance ({att}%)"
            else:
                reason = f"Low marks ({marks})"

            suggested_action = "Home Visit"

        elif risk == "Medium":
            if att < 85 and marks < 55:
                reason = f"Attendance ({att}%) and Marks ({marks}) declining"
            elif att < 85:
                reason = f"Attendance slightly low ({att}%)"
            else:
                reason = f"Marks slightly low ({marks})"

            suggested_action = "Extra Classes"

        else:
            reason = "Good academic performance"
            suggested_action = "Regular Monitoring"

        students.append((
            roll,
            name,
            cls,
            att,
            marks,
            risk,
            reason,
            suggested_action
        ))

    # ---------- AVERAGE ATTENDANCE ----------
    avg_attendance = round(total_att / total_students, 2) if total_students else 0

    # ---------- TEACHERS ----------
    teacher_response = supabase.table("teachers").select("*").execute()
    teachers = teacher_response.data or []

    # ================= INTERVENTION TRACKING =================
    intervention_response = supabase.table("interventions").select("*").execute()
    interventions = intervention_response.data or []

    home_visits = 0
    parent_meetings = 0
    high_to_medium = 0
    medium_to_low = 0

    for record in interventions:
        if record.get("type") == "home_visit":
            home_visits += 1

        if record.get("type") == "parent_meeting":
            parent_meetings += 1

        if record.get("transition") == "High_to_Medium":
            high_to_medium += 1

        if record.get("transition") == "Medium_to_Low":
            medium_to_low += 1

    # ---------- LAST 30 DAYS ANALYSIS ----------
    thirty_days_ago = datetime.now() - timedelta(days=30)

    response_30 = supabase.table("students") \
        .select("*") \
        .gte("updated_at", thirty_days_ago.isoformat()) \
        .execute()

    last30_students = response_30.data or []

    improved_students = 0
    declined_students = 0

    for s in last30_students:
        attendance = int(s.get("attendance") or 0)
        marks = int(s.get("marks") or 0)

        if attendance > 75 and marks > 50:
            improved_students += 1
        else:
            declined_students += 1

    return render_template(
        "dashboard_principal.html",
        students=students,
        total_students=total_students,
        high_risk=high_risk,
        medium_risk=medium_risk,
        avg_attendance=avg_attendance,
        class_labels=list(classes.keys()),
        class_values=list(classes.values()),
        boys_risk=boys_risk,
        girls_risk=girls_risk,
        red_flag_students=red_flag_students,
        teachers=teachers,
        selected_class=selected_class,
        improved_students=improved_students,
        declined_students=declined_students,
        home_visits=home_visits,
        parent_meetings=parent_meetings,
        high_to_medium=high_to_medium,
        medium_to_low=medium_to_low,
    )


# ================= ADD TEACHER =================
@app.route("/add_teacher", methods=["POST"])
def add_teacher():

    name = request.form.get("name")
    email = request.form.get("email")
    assigned_class = request.form.get("assigned_class")

    supabase.table("teachers").insert({
        "name": name,
        "email": email,
        "assigned_class": assigned_class
    }).execute()

    return redirect(url_for("dashboard_principal"))


# ================= REMOVE TEACHER =================
@app.route("/remove_teacher/<teacher_id>")
def remove_teacher(teacher_id):

    supabase.table("teachers").delete().eq("id", teacher_id).execute()

    return redirect(url_for("dashboard_principal"))


# ================= SEND HIGH RISK TO NGO =================
@app.route("/send_ngo")
def send_ngo():

    response = supabase.table("students").select("*").execute()
    rows = response.data or []

    for r in rows:
        att = int(r.get("attendance") or 0)
        marks = int(r.get("marks") or 0)

        if att < 75 or marks < 40:
            supabase.table("ngo_notifications").insert({
                "student_name": r.get("name"),
                "class": r.get("class"),
                "attendance": att,
                "marks": marks
            }).execute()

    return redirect(url_for("dashboard_principal"))
# ---------------- VOLUNTEER DASHBOARD ----------------
@app.route('/volunteer/dashboard')
def dashboard_volunteer():
    if session.get('role') != 'volunteer':
        flash("Unauthorized access", "error")
        return redirect(url_for('login'))

    email = session.get('email')

    # -------- FETCH VOLUNTEER --------
    volunteer_res = supabase.table("users") \
        .select("*") \
        .eq("role", "volunteer") \
        .eq("email", email) \
        .execute()

    volunteer = volunteer_res.data[0] if volunteer_res.data else None

    # -------- FETCH STUDENT PERFORMANCE (NO INVALID COLUMN) --------
    students_res = supabase.table("student_performance") \
        .select("*") \
        .execute()

    students = students_res.data if students_res.data else []

    # -------- FETCH NGO INTERVENTIONS --------
    interventions_res = supabase.table("ngo_interventions") \
        .select("*") \
        .execute()

    interventions = interventions_res.data if interventions_res.data else []

    return render_template(
        "dashboard_volunteer.html",
        volunteer=volunteer,
        students=students,
        interventions=interventions
    )
# ---------------- ADMIN DASHBOARD ----------------
@app.route('/teacher/risk_trend')
def risk_trend():

    response = supabase.table("risk_history") \
        .select("created_at, risk_score") \
        .order("created_at") \
        .execute()

    data = response.data

    dates = [r["created_at"][:10] for r in data]
    scores = [r["risk_score"] for r in data]

    return jsonify({
        "dates": dates,
        "scores": scores
    })

@app.route('/admin/dashboard')
def dashboard_admin():
    if session.get('role') != 'admin':
        flash("Unauthorized access", "error")
        return redirect(url_for('login'))

    email = session.get('email')
    res = supabase.table("users").select("*").eq("role", "admin").eq("email", email).execute()
    admin = res.data[0] if res.data else None

    return render_template("dashboard_admin.html", admin=admin)
def predict_future_risk(current_score, past_scores):
    
    if len(past_scores) < 2:
        return current_score

    trend = past_scores[-1] - past_scores[-2]
    predicted = current_score + trend

    return max(0, min(predicted, 100))


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
@app.route('/student/set_password', methods=['GET', 'POST'])
def set_password():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        supabase.table("student_performance") \
            .update({"password": hashed_password}) \
            .eq("email", email) \
            .execute()

        return redirect(url_for('student_login'))

    return render_template("student/set_password.html")
@app.route('/teacher/risk_trend_data')
def risk_trend_data():

    response = supabase.table("risk_history") \
        .select("created_at, risk_score") \
        .order("created_at") \
        .execute()

    data = response.data

    dates = [r["created_at"][:10] for r in data]
    scores = [r["risk_score"] for r in data]

    return jsonify({
        "dates": dates,
        "scores": scores
    })

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
    return redirect(url_for('select_role'))

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True, port=5001)