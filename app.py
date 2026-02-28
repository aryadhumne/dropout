from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
from flask_mail import Mail
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from supabase_client import supabase
from datetime import datetime, timedelta
import os
import csv
import sqlite3
import io
import pandas as pd
from reportlab.pdfgen import canvas
from flask import jsonify
from supabase import create_client
# -------- AI MODEL --------
import joblib
import numpy as np
import shap
import cloudinary
import cloudinary.uploader
# -------- NLP & GENERATIVE AI --------
from textblob import TextBlob
# import google.generativeai as genai
# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

cloudinary.config(
    cloud_name="de20jxqpu",
    api_key="436794672919247",
    api_secret="NiTxT3Tn3qYHjHeM82PiX8ygKb8"
)

# -------- LOAD AI FILES --------
model = joblib.load("risk_model.pkl")
model_features = joblib.load("model_features.pkl")

explainer = shap.TreeExplainer(model)
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
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mail import Mail
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv
import os
from supabase_client import supabase
from werkzeug.security import generate_password_hash, check_password_hash
# -------- AI MODEL --------
import joblib
import numpy as np
import shap
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name="de20jxqpu",
    api_key="436794672919247",
    api_secret="NiTxT3Tn3qYHjHeM82PiX8ygKb8"
)

# -------- LOAD AI FILES --------
model = joblib.load("risk_model.pkl")
model_features = joblib.load("model_features.pkl")


explainer = shap.TreeExplainer(model)



@app.route("/ngo/admin/login", methods=["GET", "POST"])
def ngo_admin_login():

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("All fields required", "error")
            return redirect(url_for("ngo_admin_login"))

        res = supabase.table("users") \
            .select("*") \
            .eq("role", "ngo_admin") \
            .eq("email", email) \
            .execute()

        if not res.data:
            flash("Invalid credentials", "error")
            return redirect(url_for("ngo_admin_login"))

        user = res.data[0]

        if not check_password_hash(user["password"], password):
            flash("Invalid credentials", "error")
            return redirect(url_for("ngo_admin_login"))

        session.clear()
        session["role"] = "ngo_admin"
        session["email"] = email

        flash("Login successful", "success")
        return redirect(url_for("dashboard_admin"))

    return render_template("ngo_admin_login.html")

@app.route("/ngo")
def ngo_role():
    return render_template("ngo_role.html")


# ---------------- VOLUNTEER LOGIN (SEPARATE) ----------------
@app.route('/volunteer/login', methods=['GET', 'POST'])
def volunteer_login():

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash("All fields required", "error")
            return redirect(url_for('volunteer_login'))

        district = request.form.get("district")
        ngo_name = request.form.get("ngo_name")

        res = supabase.table("users") \
            .select("*") \
            .eq("role", "volunteer") \
            .eq("email", email) \
            .eq("district", district) \
            .eq("ngo_name", ngo_name) \
            .execute()

        if not res.data:
            flash("Invalid credentials", "error")
            return redirect(url_for('volunteer_login'))

        user = res.data[0]

        if not check_password_hash(user["password"], password):
            flash("Invalid credentials", "error")
            return redirect(url_for('volunteer_login'))

        session.clear()
        session["role"] = "volunteer"
        session["email"] = email

        flash("Login successful", "success")
        return redirect(url_for("dashboard_volunteer"))

    return render_template("volunteer_login.html")


# ---------------- VOLUNTEER REGISTER (SEPARATE) ----------------
@app.route('/volunteer/register', methods=['GET', 'POST'])
def volunteer_register():

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not name or not email or not password:
            flash("All fields required", "error")
            return redirect(url_for('volunteer_register'))

        if not password.isdigit() or len(password) != 6:
            flash("Password must be 6 digits", "error")
            return redirect(url_for('volunteer_register'))

        existing = supabase.table("users") \
            .select("*") \
            .eq("email", email) \
            .execute()

        if existing.data:
            flash("Email already registered", "error")
            return redirect(url_for('volunteer_register'))

        hashed = generate_password_hash(password)

        supabase.table("users").insert({
            "role": "volunteer",
            "name": name,
            "email": email,
            "password": hashed
        }).execute()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for('volunteer_login'))

    return render_template("volunteer_register.html")


@app.route("/ngo/admin/register", methods=["GET", "POST"])
def ngo_admin_register():

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        ngo_name = request.form.get("ngo_name")   # MUST be this
        email = request.form.get("email", "").strip().lower()
        district = request.form.get("district", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # -------- VALIDATION --------
        if not all([name, ngo_name, email, district, password, confirm_password]):
            flash("All fields are required", "error")
            return redirect(url_for("ngo_admin_register"))

        if password != confirm_password:
            flash("Passwords do not match", "error")
            return redirect(url_for("ngo_admin_register"))

        if not password.isdigit() or len(password) != 6:
            flash("Password must be exactly 6 digits", "error")
            return redirect(url_for("ngo_admin_register"))

        # Check existing email
        existing = supabase.table("users") \
            .select("*") \
            .eq("email", email) \
            .execute()

        if existing.data:
            flash("Email already registered", "error")
            return redirect(url_for("ngo_admin_register"))

        hashed = generate_password_hash(password)

        # -------- INSERT --------
        supabase.table("users").insert({
            "role": "ngo_admin",
            "name": name,
            "ngo_name": ngo_name,
            "email": email,
            "district": district,
            "password": hashed
        }).execute()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for("ngo_admin_login"))

    return render_template("ngo_admin_register.html")

# ---------------- VOLUNTEER DASHBOARD ----------------
@app.route('/volunteer/dashboard', methods=['GET', 'POST'])
def dashboard_volunteer():
    if session.get('role') != 'volunteer':
        flash("Unauthorized access", "error")
        return redirect(url_for('login'))

    email = session.get('email')

    # -------- AI PREDICTION FUNCTION (nested helper) --------
    def predict_student_risk(student):
        attendance_val = float(student.get("attendance", student.get("avg", 0)))
        monthly_test_val = float(student.get("monthly_test_score", 0))
        assignment_val = float(student.get("assignment", 0))
        quiz_val = float(student.get("quiz", 0))

        # MUST match training order: ["attendance", "monthly_test", "assignment", "quiz"]
        input_data = np.array([[attendance_val, monthly_test_val, assignment_val, quiz_val]])

        prediction = model.predict(input_data)[0]
        probability = model.predict_proba(input_data)[0]
        confidence = round(max(probability) * 100, 2)

        # SHAP explainability
        shap_values = explainer.shap_values(input_data)
        # shap_values is a list of arrays (one per class). Use the predicted class.
        feature_names = ["Attendance", "Monthly Test", "Assignment", "Quiz"]
        shap_for_pred = shap_values[int(prediction)][0] if isinstance(shap_values, list) else shap_values[0]
        shap_dict = {feature_names[i]: round(float(shap_for_pred[i]), 4) for i in range(len(feature_names))}

        return prediction, confidence, attendance_val, monthly_test_val, assignment_val, quiz_val, shap_dict

    # ---- Fetch volunteer info (THIS MUST BE OUTSIDE predict_student_risk) ----
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
            intervention_type = request.form.get('intervention_type')
            status = request.form.get('status')
            notes = request.form.get('notes')
            proof_file = request.files.get("proof_image")

            proof_url = None
            approval_status = "Approved"

            # Financial Aid always requires admin approval regardless of status
            if intervention_type == "Financial Aid":
                approval_status = "Pending"
                if status == "Completed":
                    if not proof_file:
                        flash("Photo proof required for completed Financial Aid cases", "error")
                        return redirect(url_for("dashboard_volunteer"))
                    upload_result = cloudinary.uploader.upload(proof_file)
                    proof_url = upload_result["secure_url"]
                # For Financial Aid, keep status as-is but always require admin approval
            elif status == "Completed":
                if not proof_file:
                    flash("Photo proof required for completed cases", "error")
                    return redirect(url_for("dashboard_volunteer"))

                upload_result = cloudinary.uploader.upload(proof_file)
                proof_url = upload_result["secure_url"]

                approval_status = "Pending"

            supabase.table("ngo_interventions").insert({
                "student_id": student_id,
                "type": intervention_type,
                "status": status if intervention_type != "Financial Aid" or status != "Completed" else "Awaiting Approval",
                "notes": notes,
                "by": email,
                "proof_image": proof_url,
                "approval_status": approval_status
            }).execute()

            flash("Intervention submitted", "success")
            return redirect(url_for("dashboard_volunteer"))

        except Exception as e:
            print("UPLOAD ERROR:", e)
            flash("Error saving intervention", "error")
            return redirect(url_for("dashboard_volunteer"))

    # ---------------- GET: fetch only students with risk = "At Risk" OR "Medium" ----------------
    try:
        students_res = supabase.table("student_performance") \
            .select("*") \
            .in_("risk", ["At Risk", "Medium"]) \
            .execute()

        students = students_res.data or []

        interventions_res = supabase.table("ngo_interventions") \
            .select("*") \
            .order("created_at", desc=True) \
            .execute()

        all_interventions = interventions_res.data or []
        latest_map = {}
        for i in all_interventions:
            sid = str(i["student_id"])
            if sid not in latest_map:
                latest_map[sid] = i

        active_interventions_count = sum(
            1 for v in latest_map.values()
            if v.get("status") != "Completed"
        )

        filtered_students = []
        for s in students:
            sid = str(s["id"])
            latest = latest_map.get(sid)
            if latest:
                s["current_intervention"] = latest.get("type", "-")
                s["current_status"] = latest.get("status", "-")
                s["current_notes"] = latest.get("notes", "-")
                if latest and latest.get("approval_status") == "Approved":
                    continue
            else:
                s["current_intervention"] = "-"
                s["current_status"] = "-"
                s["current_notes"] = "-"
            filtered_students.append(s)

        students = filtered_students

        # -------- ADD AI EXPLANATION + SHAP --------
        for s in students:
            try:
                prediction, confidence, attendance_val, monthly_test_val, assignment_val, quiz_val, shap_dict = predict_student_risk(s)

                # Build explanation from SHAP - find top contributing factors
                sorted_factors = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)
                top_factors = [f"{name} ({val:+.3f})" for name, val in sorted_factors[:3]]

                risk_labels = {0: "Low Risk", 1: "Medium Risk", 2: "High Risk"}
                risk_label = risk_labels.get(prediction, "Unknown")

                factors_str = ", ".join(top_factors)
                ai_reason = (
                    f"AI predicts {risk_label}. "
                    f"Key factors: {factors_str}. "
                    f"Attendance: {attendance_val:.0f}%, Monthly Test: {monthly_test_val:.0f}, "
                    f"Assignment: {assignment_val:.0f}, Quiz: {quiz_val:.0f}."
                )

                s["ai_reason"] = ai_reason
                s["ai_confidence"] = f"{confidence}%"
                s["shap_values"] = shap_dict

            except Exception as e:
                print("AI ERROR:", e)
                s["ai_reason"] = "AI unavailable"
                s["ai_confidence"] = "-"
                s["shap_values"] = {}

    except Exception as e:
        print("Supabase .in_() may not be supported; falling back. Error:", e)
        all_res = supabase.table("student_performance").select("*").execute()
        all_students = all_res.data if all_res.data else []
        students = [s for s in all_students if s.get("risk") in ("At Risk", "Medium")]

    interventions_res = supabase.table("ngo_interventions") \
        .select("*, student_performance(name, roll, division)") \
        .order("created_at", desc=True) \
        .execute()

    interventions = [
        i for i in (interventions_res.data or [])
        if i.get("approval_status") == "Approved"
    ]

    return render_template(
        "dashboard_volunteer.html",
        volunteer=volunteer,
        students=students,
        interventions=interventions,
        active_interventions=active_interventions_count
    )


@app.route('/ngo/admin/dashboard')
def dashboard_admin():

    if session.get('role') != 'ngo_admin':
        flash("Unauthorized access", "error")
        return redirect(url_for('ngo_admin_login'))

    email = session.get('email')

    res = supabase.table("users") \
        .select("*") \
        .eq("role", "ngo_admin") \
        .eq("email", email) \
        .execute()

    admin = res.data[0] if res.data else None
    pending_res = supabase.table("ngo_interventions") \
        .select("*, student_performance(name, roll)") \
        .eq("approval_status", "Pending") \
        .execute()

    pending_cases = pending_res.data or []

    return render_template("dashboard_admin.html",
                        admin=admin,
                        pending_cases=pending_cases)

 

@app.route("/approve-intervention/<id>", methods=["POST"])
def approve_intervention(id):

    if session.get("role") != "ngo_admin":
        return redirect(url_for("login"))

    # Check if this is a Financial Aid case awaiting approval
    intervention = supabase.table("ngo_interventions").select("type,status").eq("id", id).execute()
    update_data = {
        "approval_status": "Approved",
        "approved_by": session.get("email")
    }
    # If Financial Aid was awaiting approval, mark it as Completed now
    if intervention.data and intervention.data[0].get("type") == "Financial Aid" and intervention.data[0].get("status") == "Awaiting Approval":
        update_data["status"] = "Completed"

    supabase.table("ngo_interventions").update(update_data).eq("id", id).execute()

    flash("Intervention approved", "success")
    return redirect(url_for("dashboard_admin"))


@app.route("/reject-intervention/<id>", methods=["POST"])
def reject_intervention(id):
    if session.get("role") != "ngo_admin":
        return redirect(url_for("login"))

    supabase.table("ngo_interventions").update({
        "approval_status": "Rejected",
        "approved_by": session.get("email")
    }).eq("id", id).execute()

    flash("Intervention rejected", "success")
    return redirect(url_for("dashboard_admin"))
@app.route('/admin/add-volunteer', methods=['GET', 'POST'])
def add_volunteer():
    # Only NGO admin can access
    if session.get('role') != 'ngo_admin':
        flash("Unauthorized", "error")
        return redirect(url_for('login'))

    # 🔥 Get logged in admin info
    admin_email = session.get("email")
    admin_res = supabase.table("users") \
        .select("district, ngo_name") \
        .eq("email", admin_email) \
        .eq("role", "ngo_admin") \
        .execute()

    if not admin_res.data:
        flash("Admin data not found", "error")
        return redirect(url_for('dashboard_admin'))

    admin_data = admin_res.data[0]
    admin_district = admin_data["district"]
    admin_ngo = admin_data["ngo_name"]

    if request.method == 'POST':
        try:
            # ✅ Get form data
            name = request.form.get('name', '').strip()
            age = request.form.get('age', '').strip()
            gender = request.form.get('gender', '').strip()
            mobile = request.form.get('mobile', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '').strip()

            # 🔹 Server-side validation
            if not (name and age and gender and mobile and email and password):
                flash("All fields are required!", "error")
                return redirect(url_for('add_volunteer'))

            if not age.isdigit() or int(age) <= 0:
                flash("Please enter a valid age", "error")
                return redirect(url_for('add_volunteer'))

            age = int(age)
            hashed_password = generate_password_hash(password)

            # 🔹 Insert volunteer
            supabase.table("users").insert({
                "role": "volunteer",
                "name": name,
                "age": age,
                "gender": gender,
                "mobile": mobile,
                "email": email,
                "password": hashed_password,
                "district": admin_district,
                "ngo_name": admin_ngo
            }).execute()

            flash("Volunteer added successfully!", "success")
            return redirect(url_for('dashboard_admin'))

        except Exception as e:
            print("INSERT ERROR:", e)

            if "duplicate key value" in str(e).lower():
                flash("Email already exists!", "error")
            else:
                flash("Database error occurred", "error")

            return redirect(url_for('add_volunteer'))

    # GET request
    return render_template("add_volunteer.html")

@app.route("/get-ngos/<district>")
def get_ngos(district):

    res = supabase.table("users") \
        .select("ngo_name") \
        .eq("role", "ngo_admin") \
        .eq("district", district) \
        .execute()

    ngos = list(set([r["ngo_name"] for r in res.data])) if res.data else []

    return ngos
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
        "ngo": "ngo_role.html",
       
    }

    if role not in template_map:
        return "Invalid Role", 404

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email and password:
            # Principal register/login validation
            if role == "principal":
                action = request.form.get("action")

                if action == "register":
                    # Check if already registered
                    existing = supabase.table("users").select("id").eq("email", email).eq("role", "principal").execute()
                    if existing.data:
                        flash("Email already registered. Please login.", "danger")
                        return render_template(template_map[role])

                    supabase.table("users").insert({
                        "email": email,
                        "password": generate_password_hash(password),
                        "role": "principal",
                        "name": request.form.get("principal_name", ""),
                        "school_name": request.form.get("school_name", ""),
                       
                        "district": request.form.get("district", "")
                    }).execute()

                    flash("Registration successful! Please login.", "success")
                    return render_template(template_map[role])

                else:  # login
                    principal_check = supabase.table("users").select("*").eq("email", email).eq("role", "principal").execute()
                    if not principal_check.data:
                        flash("Invalid Email ID. Account not found.", "danger")
                        return render_template(template_map[role])

                    if not check_password_hash(principal_check.data[0]["password"], password):
                        flash("Invalid password.", "danger")
                        return render_template(template_map[role])

            session["user"] = email
            session["role"] = role

            if role == "student":
                return redirect(url_for("dashboard"))
            elif role == "teacher":
                return redirect(url_for("teacher_dashboard"))

            elif role == "principal":
                return redirect(url_for("dashboard_principal"))
            elif role == "ngo":
                return redirect(url_for("dashboard_volunteer"))
           

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

    # Fetch teachers for feedback dropdown
    teachers = supabase.table("teachers").select("id,name").execute().data or []

    return render_template(
        "student/dashboard.html",
        performance=performance.data,
        teachers=teachers,
        no_data=False
    )


# ---------------- STUDENT FEEDBACK ----------------
@app.route('/student/feedback', methods=['POST'])
def student_feedback():
    if session.get('role') != 'student':
        return redirect(url_for('select_role'))

    student_id = session.get('student_id')
    feedback_text = request.form.get('feedback')

    if not feedback_text:
        flash("Please enter your feedback.", "danger")
        return redirect(url_for('dashboard_student'))

    # Get student info for display on principal dashboard
    student_account = supabase.table("students").select("*").eq("id", student_id).execute()
    student_name = "Unknown"
    standard = None
    division = None

    if student_account.data:
        perf_id = student_account.data[0].get("student_performance_id")
        if perf_id:
            perf = supabase.table("student_performance").select("name,standard,division").eq("id", perf_id).execute()
            if perf.data:
                student_name = perf.data[0].get("name", "Unknown")
                standard = perf.data[0].get("standard")
                division = perf.data[0].get("division")

    teacher_name = request.form.get('teacher_name', '')

    # -------- SENTIMENT ANALYSIS (TextBlob) --------
    try:
        sentiment = TextBlob(feedback_text).sentiment
        sentiment_score = round(sentiment.polarity, 2)
        if sentiment_score > 0.1:
            sentiment_label = "Positive"
        elif sentiment_score < -0.1:
            sentiment_label = "Negative"
        else:
            sentiment_label = "Neutral"
    except:
        sentiment_score = 0.0
        sentiment_label = "Neutral"

    supabase.table("student_feedback").insert({
        "student_id": str(student_id),
        "student_name": student_name,
        "standard": standard,
        "division": division,
        "feedback_text": feedback_text,
        "teacher_name": teacher_name,
        "sentiment_score": sentiment_score,
        "sentiment_label": sentiment_label
    }).execute()

    flash("Feedback submitted successfully!", "success")
    return redirect(url_for('dashboard_student'))


# ---------------- STUDENT LEAVE APPLICATION ----------------
@app.route('/student/leave', methods=['POST'])
def student_leave():
    if session.get('role') != 'student':
        return redirect(url_for('select_role'))

    student_id = session.get('student_id')
    leave_date = request.form.get('leave_date')
    reason = request.form.get('reason')

    if not leave_date or not reason:
        flash("Please fill in all fields.", "danger")
        return redirect(url_for('dashboard_student'))

    # Get student info
    student_account = supabase.table("students").select("*").eq("id", student_id).execute()
    student_name = "Unknown"
    standard = None
    division = None

    if student_account.data:
        perf_id = student_account.data[0].get("student_performance_id")
        if perf_id:
            perf = supabase.table("student_performance").select("name,standard,division").eq("id", perf_id).execute()
            if perf.data:
                student_name = perf.data[0].get("name", "Unknown")
                standard = perf.data[0].get("standard")
                division = perf.data[0].get("division")

    supabase.table("student_leaves").insert({
        "student_id": str(student_id),
        "student_name": student_name,
        "standard": standard,
        "division": division,
        "leave_date": leave_date,
        "reason": reason,
        "status": "Pending"
    }).execute()

    flash("Leave application submitted successfully!", "success")
    return redirect(url_for('dashboard_student'))


# # ---------------- AI CHATBOT (Gemini + Smart Fallback) ----------------
# import time as _time
# _gemini_cooldown = 0
#
# def _smart_fallback(message, student_data):
#     msg = message.lower()
#     p = student_data or {}
#     name = p.get("name", "there")
#     att = int(p.get("attendance", 0))
#     monthly = int(p.get("monthly_test_score", 0))
#     assign = int(p.get("assignment", 0))
#     quiz_score = int(p.get("quiz", 0))
#     risk = p.get("risk_status", p.get("risk", "Unknown"))
#     scores = {"attendance": att, "monthly test": monthly, "assignments": assign, "quizzes": quiz_score}
#     weakest = min(scores, key=scores.get)
#     strongest = max(scores, key=scores.get)
#     if any(w in msg for w in ["how am i", "my performance", "how do i", "my score", "my marks", "my result"]):
#         tips = []
#         if att < 75: tips.append(f"Your attendance is {att}% — aim for 75%+ by attending regularly.")
#         if monthly < 40: tips.append(f"Monthly test score is {monthly} — try solving previous year papers.")
#         if assign < 50: tips.append(f"Assignment score is {assign} — submit all pending work to boost this.")
#         if quiz_score < 50: tips.append(f"Quiz score is {quiz_score} — daily 15-min revision can help.")
#         if not tips: return f"Great job {name}! Your scores look good. Keep it up!"
#         return f"Hi {name}! Here's what needs attention: " + " ".join(tips)
#     elif any(w in msg for w in ["improve", "better", "help", "tip", "study", "advice"]):
#         return f"Focus on your weakest area ({weakest}) and practice daily. You're strong in {strongest} — keep that up!"
#     elif any(w in msg for w in ["stress", "worried", "scared", "anxious", "sad", "depressed", "motivation"]):
#         return f"It's completely normal to feel this way, {name}. Take it one step at a time. Talk to your teacher if you need support."
#     elif any(w in msg for w in ["hello", "hi", "hey", "good morning", "good evening"]):
#         return f"Hello {name}! I'm EduBot. Ask me about your performance, study tips, or how to improve."
#     elif any(w in msg for w in ["risk", "danger", "dropout", "at risk"]):
#         return f"Your status is {risk}. Focus on {weakest} (score: {scores[weakest]}). Small daily improvements help!"
#     else:
#         return f"Hi {name}! Attendance: {att}%, Test: {monthly}, Assignment: {assign}, Quiz: {quiz_score}. Strongest: {strongest}."
#
# @app.route('/api/chat', methods=['POST'])
# def api_chat():
#     if session.get('role') != 'student':
#         return jsonify({"error": "Unauthorized"}), 401
#     data = request.get_json()
#     message = data.get('message', '') if data else ''
#     if not message:
#         return jsonify({"error": "No message provided"}), 400
#     student_id = session.get('student_id')
#     student_data = None
#     context = ""
#     try:
#         student_account = supabase.table("students").select("*").eq("id", student_id).execute()
#         if student_account.data:
#             perf_id = student_account.data[0].get("student_performance_id")
#             if perf_id:
#                 perf = supabase.table("student_performance").select("*").eq("id", perf_id).execute()
#                 if perf.data:
#                     student_data = perf.data[0]
#                     p = student_data
#                     context = (
#                         f"Student Profile:\n"
#                         f"- Name: {p.get('name', 'N/A')}\n"
#                         f"- Attendance: {p.get('attendance', 'N/A')}%\n"
#                         f"- Monthly Test Score: {p.get('monthly_test_score', 'N/A')}\n"
#                         f"- Assignment Score: {p.get('assignment', 'N/A')}\n"
#                         f"- Quiz Score: {p.get('quiz', 'N/A')}\n"
#                         f"- Risk Status: {p.get('risk_status', p.get('risk', 'N/A'))}\n"
#                     )
#     except Exception as e:
#         print("CHAT CONTEXT ERROR:", e)
#     global _gemini_cooldown
#     if _time.time() > _gemini_cooldown:
#         try:
#             prompt = (
#                 "You are EduBot, a friendly AI academic counselor for school students. "
#                 "Keep responses concise (2-3 sentences max). Be supportive and encouraging. "
#                 "If the student shares data, give specific advice based on their numbers.\n\n"
#             )
#             if context: prompt += f"Student data:\n{context}\n"
#             prompt += f"Student's message: {message}"
#             response = genai.GenerativeModel('gemini-2.0-flash').generate_content(
#                 prompt, request_options={"timeout": 8}
#             )
#             return jsonify({"response": response.text})
#         except Exception as e:
#             _gemini_cooldown = _time.time() + 300
#             print(f"GEMINI FAILED ({type(e).__name__}) — cooldown 5 min")
#     return jsonify({"response": _smart_fallback(message, student_data)})


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

    # -------- STUDENT LEAVE REQUESTS --------
    try:
        leave_requests = supabase.table("student_leaves").select("*").order("created_at", desc=True).execute().data or []
    except:
        leave_requests = []

    return render_template(
        "teacher/dashboard.html",
        total_students=total_students,
        high_risk=high_risk,
        medium_risk=medium_risk,
        low_risk=low_risk,
        standards=standards,
        standard_risk_counts=standard_risk_counts,
        leave_requests=leave_requests
    )


@app.route('/teacher/leave/<leave_id>/<action>', methods=['POST'])
def teacher_leave_action(leave_id, action):
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))

    if action in ('Approved', 'Rejected'):
        supabase.table("student_leaves").update({
            "status": action
        }).eq("id", leave_id).execute()
        flash(f"Leave {action.lower()}.", "success")

    return redirect(url_for('teacher_dashboard'))
@app.route('/teacher/add_student', methods=['GET', 'POST'])
def add_student():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))

    if request.method == 'POST':
        # ---------------- BASIC DETAILS ----------------
        name = request.form.get('name', '').strip()
        roll = request.form.get('roll', '').strip()
        standard = request.form.get('standard', '')
        division = request.form.get('division', '')
        email = request.form.get('email', '').strip().lower()
        gender = request.form.get('gender', '')

        # ---------------- SUBJECT ATTENDANCE ----------------
        subjects = request.form.getlist("subjects[]")
        attendance_list = request.form.getlist("attendance[]")

        # Calculate average attendance safely
        attendance_values = []
        for a in attendance_list:
            try:
                val = int(a)
                if 0 <= val <= 100:
                    attendance_values.append(val)
            except (ValueError, TypeError):
                continue
        
        avg_attendance = int(sum(attendance_values) / len(attendance_values)) if attendance_values else 0

        # ---------------- ACADEMIC ----------------
        monthly_test_score = 0
        try:
            monthly_input = request.form.get('monthly_score', '0')
            monthly_test_score = int(monthly_input)
        except (ValueError, TypeError):
            monthly_test_score = 0

        assignment_status = request.form.get("assignment", "").strip()
        quiz_status = request.form.get("quiz", "").strip()

        # ---------------- PARENT ----------------
        parent_name = request.form.get('parent_name', '').strip()
        parent_phone = request.form.get('parent_phone', '').strip()
        parent_alt_phone = request.form.get('parent_alt_phone', '').strip()
        parent_address = request.form.get('parent_address', '').strip()

        # ---------------- VALIDATION ----------------
        if not all([name, roll, standard, email]):
            flash("Please fill required fields: Name, Roll, Standard, Email", "danger")
            return redirect(url_for('add_student'))

        # ---------------- DUPLICATE CHECK ----------------
        existing = supabase.table("student_performance") \
            .select("id") \
            .eq("email", email) \
            .eq("is_deleted", False) \
            .execute()

        if existing.data:
            flash("Student with this email already exists!", "danger")
            return redirect(url_for('add_student'))

        # ---------------- STATUS TO SCORE ----------------
        assignment_score = 100 if assignment_status == "Completed" else 0
        
        if quiz_status == "Good":
            quiz_score = 100
        elif quiz_status == "Average":
            quiz_score = 50
        else:
            quiz_score = 0

        # ---------------- RISK CALCULATION ----------------
        risk_score = 0
        risk_reason = []

        if monthly_test_score < 35:
            risk_score += 40
            risk_reason.append("Low Monthly Score")

        if avg_attendance < 60:
            risk_score += 30
            risk_reason.append("Low Attendance")

        if assignment_score < 50:
            risk_score += 15
            risk_reason.append("Low Assignment")

        if quiz_score < 50:
            risk_score += 15
            risk_reason.append("Low Quiz")

        # Convert numeric score to text for DB
        if risk_score >= 60:
            risk_text = "High Risk"
        elif risk_score >= 40:
            risk_text = "Medium Risk"
        else:
            risk_text = "Low Risk"

        risk_status = "At Risk" if risk_score >= 60 else "Safe"
        insert_data = {
            "name": name,
            "roll": roll,
            "standard": int(standard),
            "division": division,
            "email": email,
            "gender": gender or None,
            "monthly_test_score": monthly_test_score,
            "attendance": avg_attendance,
            "assignment": assignment_status,
            "quiz": quiz_status,
            "behaviour": request.form.get("behaviour", ""),
            "subjects": subjects,
            "risk": risk_text,
            "risk_reason": ", ".join(risk_reason),
            "risk_status": risk_status,
            "month": request.form.get("month"),
            "parent_name": parent_name,
            "parent_phone": parent_phone,
            "parent_alt_phone": parent_alt_phone or None,
            "parent_address": parent_address,
            "role": "student",
            "is_deleted": False
        }


        response = supabase.table("student_performance") \
            .insert(insert_data) \
            .execute()

        if response.data:
            flash("Student Added Successfully!", "success")
            return redirect(url_for('student_records'))
        else:
            flash(f"Insert failed! Error: {response}", "danger")
            return redirect(url_for('add_student'))

    return render_template("teacher/add_student.html")
@app.route('/teacher/student_records')
def student_records():

    if session.get('role') != 'teacher':
        return redirect(url_for('index'))

    try:
        # ✅ Fetch only active students
        response = supabase.table("student_performance") \
            .select("*") \
            .eq("is_deleted", False) \
            .order("standard", desc=False) \
            .order("division", desc=False) \
            .order("roll", desc=False) \
            .execute()

        students = response.data or []

    except Exception as e:
        print("FETCH ERROR:", e)
        students = []

    # ---------------- SAFE RISK FIX ----------------
    for s in students:

        if s.get("risk_score") is None:
            s["risk_score"] = 0

        if not s.get("risk_status"):
            s["risk_status"] = "At Risk" if s["risk_score"] >= 60 else "Safe"

    # ---------------- RISK COUNTS ----------------
    high_risk = len([s for s in students if s.get("risk_score", 0) >= 60])
    medium_risk = len([s for s in students if 40 <= s.get("risk_score", 0) < 60])
    low_risk = len([s for s in students if s.get("risk_score", 0) < 40])

    # ---------------- GROUP STANDARD WISE (1–8) ----------------
    grouped = {}

    for std in range(1, 9):   # Force order 1 to 8

        class_students = [
            s for s in students
            if str(s.get("standard")) == str(std)
        ]

        if class_students:
            grouped[f"Class {std}"] = class_students

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

    if session.get('role') != 'teacher':
        return redirect(url_for('index'))

    if request.method == 'POST':

        # Build subjects JSON
        subject_names = request.form.getlist("subjects[]")
        attendances = request.form.getlist("attendance[]")
        subjects = []
        for sname, att in zip(subject_names, attendances):
            if sname.strip():
                subjects.append({"subject": sname.strip(), "attendance": int(att)})

        avg_attendance = sum(s["attendance"] for s in subjects) / len(subjects) if subjects else 0

        update_data = {
            "name": request.form.get("name"),
            "roll": int(request.form.get("roll", 0)),
            "standard": int(request.form.get("standard", 0)),
            "division": request.form.get("division"),
            "assignment": request.form.get("assignment_status"),
            "behaviour": request.form.get("behaviour"),
            "parent_name": request.form.get("parent_name"),
            "parent_phone": request.form.get("parent_phone"),
            "parent_alt_phone": request.form.get("parent_alt_phone") or None,
            "parent_address": request.form.get("parent_address") or None,
            "subjects": subjects if subjects else None,
            "attendance": avg_attendance,
        }

        supabase.table("student_performance").update(update_data).eq("id", student_id).execute()

        flash("Student updated successfully!", "success")
        return redirect(url_for('student_records'))

    student = supabase.table("student_performance").select("*").eq("id", student_id).execute().data[0]

    return render_template("teacher/edit_student.html", student=student)

@app.route("/dashboard/principal")
def dashboard_principal():

    # -------- SECURITY --------
    if session.get("role") != "principal":
        return redirect(url_for("login"))

    # -------- FILTERS --------
    selected_class = request.args.get("class_filter")
    selected_risk = request.args.get("risk_filter")
    selected_gender = request.args.get("gender_filter")
    min_att = request.args.get("min_att")
    min_marks = request.args.get("min_marks")
    date_range = request.args.get("date_range")

    response = supabase.table("student_performance").select("*").execute()
    rows = response.data or []

    filtered = []
    now = datetime.now()

    for r in rows:

        cls = str(r.get("class"))
        gender = str(r.get("gender")).lower()
        att = int(r.get("attendance") or 0)
        marks = int(r.get("marks") or 0)
        updated = r.get("updated_at")

        if selected_class and cls != selected_class:
            continue
        if selected_gender and gender != selected_gender.lower():
            continue
        if min_att and att < int(min_att):
            continue
        if min_marks and marks < int(min_marks):
            continue

        if date_range:
            days = int(date_range)
            if updated:
                updated_date = datetime.fromisoformat(updated.replace("Z",""))
                if updated_date < now - timedelta(days=days):
                    continue

        filtered.append(r)

    total_students = len(filtered)
    high_risk = medium_risk = 0
    total_att = 0
    classes = {}
    boys_risk = girls_risk = other_risk = 0
    students = []
    red_flags = []

    # -------- RISK LOGIC --------
    for r in filtered:

        roll = r.get("roll")
        name = r.get("name")
        cls = r.get("class")
        gender = str(r.get("gender"))
        att = int(r.get("attendance") or 0)
        marks = int(r.get("marks") or 0)

        total_att += att
        classes.setdefault(cls, 0)

        # Risk Score (0-100)
        risk_score = max(0, 100 - ((att + marks) / 2))

        if att < 75 or marks < 40:
            risk = "High"
            high_risk += 1
            classes[cls] += 1
            red_flags.append((name, att))
            action = "Home Visit"
        elif att < 85 or marks < 55:
            risk = "Medium"
            medium_risk += 1
            action = "Extra Classes"
        else:
            risk = "Low"
            action = "Regular Monitoring"

        if gender.lower() == "male" and risk == "High":
            boys_risk += 1
        elif gender.lower() == "female" and risk == "High":
            girls_risk += 1
        elif risk == "High":
            other_risk += 1

        reason = f"Attendance: {att}%, Marks: {marks}"

        if selected_risk and risk != selected_risk:
            continue

        students.append((roll,name,cls,gender,att,marks,risk,reason,action,int(risk_score)))

    avg_attendance = round(total_att/total_students,2) if total_students else 0

    # -------- RED FLAG SORT --------
    red_flags = sorted(red_flags, key=lambda x: x[1])

    # -------- TEACHERS --------
    teachers = supabase.table("teachers").select("*").execute().data or []

    # -------- INTERVENTIONS --------
    interventions = supabase.table("interventions").select("*").execute().data or []

    home_visits = sum(1 for i in interventions if i.get("type")=="home_visit")
    parent_meetings = sum(1 for i in interventions if i.get("type")=="parent_meeting")
    high_to_medium = sum(1 for i in interventions if i.get("transition")=="High_to_Medium")
    medium_to_low = sum(1 for i in interventions if i.get("transition")=="Medium_to_Low")

    success_rate = round(((high_to_medium+medium_to_low)/len(interventions))*100,2) if interventions else 0

    improved_students = high_to_medium
    declined_students = total_students - improved_students

    # -------- STUDENT FEEDBACK --------
    try:
        feedbacks = supabase.table("student_feedback").select("*").order("created_at", desc=True).execute().data or []
    except:
        feedbacks = []

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
        other_risk=other_risk,
        teachers=teachers,
        red_flags=red_flags,
        improved_students=improved_students,
        declined_students=declined_students,
        home_visits=home_visits,
        parent_meetings=parent_meetings,
        high_to_medium=high_to_medium,
        medium_to_low=medium_to_low,
        success_rate=success_rate,
        feedbacks=feedbacks
    )


# ================= NGO CSV =================
@app.route("/export_high_risk_csv")
def export_high_risk_csv():

    rows = supabase.table("student_performance").select("*").execute().data or []

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Roll","Name","Class","Gender","Attendance","Marks"])

    for r in rows:
        att = int(r.get("attendance") or 0)
        marks = int(r.get("marks") or 0)
        if att < 75 or marks < 40:
            writer.writerow([r.get("roll"),r.get("name"),r.get("class"),r.get("gender"),att,marks])

    output.seek(0)

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition":"attachment;filename=high_risk_students.csv"}
    )
# ================= ADD TEACHER =================
@app.route("/add_teacher", methods=["POST"])
def add_teacher():

    if session.get("role") != "principal":
        return redirect(url_for("login"))

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
@app.route('/remove_teacher/<teacher_id>')
def remove_teacher(teacher_id):

    if "role" not in session or session["role"] != "principal":
        return redirect(url_for("login"))

    # Delete teacher using UUID
    supabase.table("teachers").delete().eq("id", teacher_id).execute()

    flash("Teacher removed successfully", "success")
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
    return redirect(url_for('select_role'))

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True, port=5001)