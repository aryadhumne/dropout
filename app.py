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
import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

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

    # Recalculate risk score from actual data
    performance_data = _recalc_risk(performance.data)

    # Fetch teachers for feedback dropdown
    teachers = supabase.table("teachers").select("id,name").execute().data or []

    # Check for active feedback window
    feedback_active = False
    feedback_window = None
    already_reviewed = []
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        windows = supabase.table("feedback_windows").select("*").lte("start_date", today).gte("end_date", today).order("created_at", desc=True).limit(1).execute().data or []
        if windows:
            feedback_window = windows[0]
            feedback_active = True
            # Find which teachers this student already reviewed in this window
            existing = supabase.table("student_feedback").select("teacher_name").eq("student_id", str(student_id)).eq("window_id", feedback_window["id"]).execute().data or []
            already_reviewed = [e["teacher_name"] for e in existing]
    except:
        pass

    # Fetch student's leave history
    leave_history = []
    try:
        leave_history = supabase.table("student_leaves").select("*").eq("student_id", str(student_id)).order("created_at", desc=True).execute().data or []
    except:
        pass

    return render_template(
        "student/dashboard.html",
        performance=performance_data,
        teachers=teachers,
        no_data=False,
        feedback_active=feedback_active,
        feedback_window=feedback_window,
        already_reviewed=already_reviewed,
        leave_history=leave_history
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

    # Check for active feedback window
    active_window = None
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        windows = supabase.table("feedback_windows").select("*").lte("start_date", today).gte("end_date", today).order("created_at", desc=True).limit(1).execute().data or []
        if windows:
            active_window = windows[0]
    except:
        pass

    if not active_window:
        flash("Feedback submission is currently closed.", "danger")
        return redirect(url_for('dashboard_student'))

    teacher_name = request.form.get('teacher_name', '')

    # Check duplicate: 1 feedback per teacher per student per window
    try:
        existing = supabase.table("student_feedback").select("id").eq("student_id", str(student_id)).eq("teacher_name", teacher_name).eq("window_id", active_window["id"]).execute().data
        if existing:
            flash(f"You have already submitted feedback for {teacher_name} in this period.", "warning")
            return redirect(url_for('dashboard_student'))
    except:
        pass

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
        "sentiment_label": sentiment_label,
        "window_id": active_window["id"]
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


# ---------------- AI CHATBOT (Gemini + Smart Fallback) ----------------
import time as _time
_gemini_cooldown = 0

# --- System prompts per role ---
def _get_system_prompt(role):
    prompts = {
        'homepage': (
            "You are EduBot, the AI assistant for EduDrop - a platform that helps schools "
            "identify students at risk of dropping out. You are on the public homepage. "
            "Answer questions about EduDrop's features, how it works, who can use it "
            "(students, teachers, principals, NGOs), and how to get started. "
            "Keep responses concise (2-3 sentences). Be welcoming and informative."
        ),
        'student': (
            "You are EduBot, a friendly AI academic counselor for school students. "
            "Keep responses concise (2-3 sentences max). Be supportive and encouraging. "
            "If the student shares data, give specific advice based on their numbers."
        ),
        'teacher': (
            "You are EduBot, an AI teaching assistant for school teachers using EduDrop. "
            "Help teachers understand risk scores, manage students, interpret data trends, "
            "suggest intervention strategies for at-risk students, and handle leave requests. "
            "Keep responses concise (2-3 sentences). Be professional and actionable."
        ),
        'principal': (
            "You are EduBot, an AI analytics assistant for school principals using EduDrop. "
            "Help principals interpret school-wide analytics, compare risk trends, plan "
            "interventions, manage teachers, and make data-driven decisions about student welfare. "
            "Keep responses concise (2-3 sentences). Be strategic and data-focused."
        ),
    }
    return prompts.get(role, prompts['homepage'])

# --- Context builders ---
def _get_student_context(sess):
    student_data = None
    context = ""
    try:
        student_id = sess.get('student_id')
        student_account = supabase.table("students").select("*").eq("id", student_id).execute()
        if student_account.data:
            perf_id = student_account.data[0].get("student_performance_id")
            if perf_id:
                perf = supabase.table("student_performance").select("*").eq("id", perf_id).execute()
                if perf.data:
                    student_data = perf.data[0]
                    p = student_data
                    context = (
                        f"Student Profile:\n"
                        f"- Name: {p.get('name', 'N/A')}\n"
                        f"- Attendance: {p.get('attendance', 'N/A')}%\n"
                        f"- Monthly Test Score: {p.get('monthly_test_score', 'N/A')}\n"
                        f"- Assignment Score: {p.get('assignment', 'N/A')}\n"
                        f"- Quiz Score: {p.get('quiz', 'N/A')}\n"
                        f"- Risk Status: {p.get('risk_status', p.get('risk', 'N/A'))}\n"
                    )
    except Exception as e:
        print("CHAT CONTEXT ERROR (student):", e)
    return {'context': context, 'student_data': student_data}

def _get_teacher_context(sess):
    context = ""
    data = {}
    try:
        students = _recalc_risk(
            supabase.table("student_performance").select("*").eq("is_deleted", False).execute().data or []
        )
        total = len(students)
        high = len([s for s in students if s["risk_score"] >= 60])
        medium = len([s for s in students if 40 <= s["risk_score"] < 60])
        low = total - high - medium
        pending = 0
        try:
            leaves = supabase.table("student_leaves").select("status").execute().data or []
            pending = len([l for l in leaves if l.get("status") == "Pending"])
        except:
            pass
        context = (
            f"Teacher Dashboard Summary:\n"
            f"- Total Students: {total}\n"
            f"- High Risk: {high}\n"
            f"- Medium Risk: {medium}\n"
            f"- Low Risk: {low}\n"
            f"- Pending Leave Requests: {pending}\n\n"
            f"Individual Student Details:\n"
        )
        for s in students:
            context += (
                f"  - {s.get('name', 'N/A')} | Class {s.get('standard', '?')}-{s.get('division', '?')} | "
                f"Attendance: {s.get('attendance', 'N/A')}% | "
                f"Test: {s.get('monthly_test_score', 'N/A')} | "
                f"Assignment: {s.get('assignment', 'N/A')} | "
                f"Quiz: {s.get('quiz', 'N/A')} | "
                f"Risk: {s['risk_score']}% ({s.get('risk_status', 'N/A')}) | "
                f"Reason: {s.get('risk_reason', 'None')}\n"
            )
        data = {'total': total, 'high': high, 'medium': medium, 'low': low, 'pending_leaves': pending}
    except Exception as e:
        print("CHAT CONTEXT ERROR (teacher):", e)
    return {'context': context, 'data': data}

def _get_principal_context(sess):
    context = ""
    data = {}
    try:
        rows = supabase.table("student_performance").select("*").execute().data or []
        total = len(rows)
        high = sum(1 for r in rows if _safe_int(r.get("attendance")) < 75 or _safe_int(r.get("monthly_test_score")) < 40)
        avg_att = round(sum(_safe_int(r.get("attendance")) for r in rows) / total, 1) if total else 0
        boys_risk = sum(1 for r in rows if str(r.get("gender", "")).lower() == "male" and (_safe_int(r.get("attendance")) < 75 or _safe_int(r.get("monthly_test_score")) < 40))
        girls_risk = sum(1 for r in rows if str(r.get("gender", "")).lower() == "female" and (_safe_int(r.get("attendance")) < 75 or _safe_int(r.get("monthly_test_score")) < 40))
        teachers = supabase.table("teachers").select("id").execute().data or []
        context = (
            f"School Analytics:\n"
            f"- Total Students: {total}\n"
            f"- High Risk: {high}\n"
            f"- Average Attendance: {avg_att}%\n"
            f"- Boys at High Risk: {boys_risk}, Girls at High Risk: {girls_risk}\n"
            f"- Total Teachers: {len(teachers)}\n"
        )
        data = {'total': total, 'high': high, 'avg_att': avg_att, 'boys_risk': boys_risk, 'girls_risk': girls_risk, 'teachers': len(teachers)}
    except Exception as e:
        print("CHAT CONTEXT ERROR (principal):", e)
    return {'context': context, 'data': data}

# --- Simple fallback (only used if Gemini is down) ---
def _safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def _recalc_risk(students):
    """Recalculate risk_score for students that don't have it stored in DB."""
    for s in students:
        if s.get("risk_score") is None:
            rs = 0
            mts = _safe_int(s.get("monthly_test_score"), 100)
            att = _safe_int(s.get("attendance"), 100)
            assign = str(s.get("assignment", "")).lower()
            quiz = str(s.get("quiz", "")).lower()
            if mts < 35:
                rs += 40
            if att < 60:
                rs += 30
            if assign in ("not completed", "incomplete", "pending", "poor"):
                rs += 15
            elif _safe_int(s.get("assignment"), 100) < 50:
                rs += 15
            if quiz in ("not completed", "incomplete", "pending", "poor"):
                rs += 15
            elif _safe_int(s.get("quiz"), 100) < 50:
                rs += 15
            s["risk_score"] = rs
        if not s.get("risk_status"):
            s["risk_status"] = "At Risk" if s["risk_score"] >= 60 else "Safe"
    return students

def _fallback(role, message, extra_data):
    return "Sorry, I'm temporarily unavailable. Please try again in a few minutes."

# --- Main chat route (multi-role) ---
@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json()
    message = data.get('message', '') if data else ''
    role = data.get('role', '') if data else ''
    lang = data.get('lang', 'en') if data else 'en'
    if not message:
        return jsonify({"error": "No message provided"}), 400

    allowed_roles = ['homepage', 'student', 'teacher', 'principal']
    # Use session role if available, fall back to requested role for homepage
    session_role = session.get('role')
    if role == 'homepage':
        pass  # No auth needed for homepage
    elif session_role in allowed_roles:
        role = session_role  # Trust the session, not the frontend
    else:
        return jsonify({"error": "Please log in to use the chatbot."}), 401

    # Language name map
    _lang_names = {
        'en': 'English', 'hi': 'Hindi', 'bn': 'Bengali', 'te': 'Telugu',
        'mr': 'Marathi', 'ta': 'Tamil', 'gu': 'Gujarati', 'kn': 'Kannada',
        'ml': 'Malayalam', 'pa': 'Punjabi', 'or': 'Odia', 'as': 'Assamese',
        'ur': 'Urdu', 'sa': 'Sanskrit', 'ne': 'Nepali', 'sd': 'Sindhi',
        'ks': 'Kashmiri', 'doi': 'Dogri', 'mai': 'Maithili',
        'mni-Mtei': 'Manipuri', 'sat': 'Santali', 'gom': 'Konkani'
    }
    lang_name = _lang_names.get(lang, 'English')

    context = ""
    extra_data = None
    if role == 'student':
        extra_data = _get_student_context(session)
        context = extra_data.get('context', '')
    elif role == 'teacher':
        extra_data = _get_teacher_context(session)
        context = extra_data.get('context', '')
    elif role == 'principal':
        extra_data = _get_principal_context(session)
        context = extra_data.get('context', '')

    system_prompt = _get_system_prompt(role)
    global _gemini_cooldown
    if _time.time() > _gemini_cooldown:
        try:
            prompt = system_prompt + "\n\n"
            if lang != 'en':
                prompt += f"IMPORTANT: You MUST respond entirely in {lang_name}. The user's preferred language is {lang_name}. Do not use English.\n\n"
            if context:
                prompt += f"Available data:\n{context}\n\n"
            prompt += f"User's message: {message}"
            import requests as _req
            api_key = os.getenv("GEMINI_API_KEY")
            gemini_resp = _req.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=10
            )
            if gemini_resp.status_code == 200:
                resp_data = gemini_resp.json()
                text = resp_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if text:
                    return jsonify({"response": text})
            else:
                raise Exception(f"HTTP {gemini_resp.status_code}")
        except Exception as e:
            _gemini_cooldown = _time.time() + 300
            print(f"GEMINI FAILED ({type(e).__name__}: {e}) — cooldown 5 min")

    return jsonify({"response": _fallback(role, message, extra_data)})


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

    response = supabase.table("student_performance").select("*").eq("is_deleted", False).execute()
    students = _recalc_risk(response.data or [])

    total_students = len(students)
    high_risk = len([s for s in students if s["risk_score"] >= 60])
    medium_risk = len([s for s in students if 40 <= s["risk_score"] < 60])
    low_risk = len([s for s in students if s["risk_score"] < 40])

    # Standard-wise risk breakdown
    standards = sorted(set(s["standard"] for s in students))
    standard_risk_counts = []
    std_high = []
    std_medium = []
    std_low = []

    for std in standards:
        cls = [s for s in students if s["standard"] == std]
        standard_risk_counts.append(len([s for s in cls if s["risk_score"] >= 40]))
        std_high.append(len([s for s in cls if s["risk_score"] >= 60]))
        std_medium.append(len([s for s in cls if 40 <= s["risk_score"] < 60]))
        std_low.append(len([s for s in cls if s["risk_score"] < 40]))

    # Format standard labels
    std_labels = [f"Class {s}" for s in standards]

    return render_template(
        "teacher/dashboard.html",
        total_students=total_students,
        high_risk=high_risk,
        medium_risk=medium_risk,
        low_risk=low_risk,
        standards=std_labels,
        standard_risk_counts=standard_risk_counts,
        std_high=std_high,
        std_medium=std_medium,
        std_low=std_low
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

    return redirect(url_for('teacher_leave_requests'))

@app.route('/teacher/leave_requests')
def teacher_leave_requests():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
    try:
        leave_requests = supabase.table("student_leaves").select("*").order("created_at", desc=True).execute().data or []
    except:
        leave_requests = []
    pending = len([l for l in leave_requests if l.get("status") == "Pending"])
    return render_template("teacher/leave_requests.html", leave_requests=leave_requests, pending_count=pending)

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

@app.route('/teacher/csv_template')
def csv_template():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'name', 'roll', 'standard', 'division', 'email', 'gender',
        'monthly_test_score', 'attendance', 'assignment', 'quiz',
        'behaviour', 'parent_name', 'parent_phone', 'parent_alt_phone',
        'parent_address'
    ])
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=student_upload_template.csv'}
    )

@app.route('/teacher/bulk_upload', methods=['POST'])
def bulk_upload():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))

    file = request.files.get('csv_file')
    if not file or not file.filename.endswith('.csv'):
        flash("Please upload a valid CSV file.", "danger")
        return redirect(url_for('add_student'))

    try:
        stream = io.StringIO(file.stream.read().decode('utf-8'))
        reader = csv.DictReader(stream)

        required = ['name', 'roll', 'standard', 'email']
        if not all(col in (reader.fieldnames or []) for col in required):
            flash(f"CSV must have columns: {', '.join(required)}", "danger")
            return redirect(url_for('add_student'))

        success = 0
        errors = []

        for i, row in enumerate(reader, start=2):
            name = (row.get('name') or '').strip()
            roll = (row.get('roll') or '').strip()
            standard = (row.get('standard') or '').strip()
            email = (row.get('email') or '').strip().lower()

            if not all([name, roll, standard, email]):
                errors.append(f"Row {i}: Missing required field (name/roll/standard/email)")
                continue

            try:
                standard_int = int(standard)
            except ValueError:
                errors.append(f"Row {i}: Invalid standard '{standard}'")
                continue

            division = (row.get('division') or '').strip()
            gender = (row.get('gender') or '').strip() or None

            # Monthly test score
            try:
                monthly_test_score = int(row.get('monthly_test_score') or 0)
            except (ValueError, TypeError):
                monthly_test_score = 0

            # Attendance
            try:
                attendance = int(float(row.get('attendance') or 0))
            except (ValueError, TypeError):
                attendance = 0

            assignment_status = (row.get('assignment') or '').strip()
            quiz_status = (row.get('quiz') or '').strip()
            behaviour = (row.get('behaviour') or '').strip()

            # Risk calculation (same logic as add_student)
            assignment_score = 100 if assignment_status == "Completed" else 0
            if quiz_status == "Good":
                quiz_score = 100
            elif quiz_status == "Average":
                quiz_score = 50
            else:
                quiz_score = 0

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
                "standard": standard_int,
                "division": division,
                "email": email,
                "gender": gender,
                "monthly_test_score": monthly_test_score,
                "attendance": attendance,
                "assignment": assignment_status,
                "quiz": quiz_status,
                "behaviour": behaviour,
                "subjects": [],
                "risk": risk_text,
                "risk_reason": ", ".join(risk_reason),
                "risk_status": risk_status,
                "parent_name": (row.get('parent_name') or '').strip(),
                "parent_phone": (row.get('parent_phone') or '').strip(),
                "parent_alt_phone": (row.get('parent_alt_phone') or '').strip() or None,
                "parent_address": (row.get('parent_address') or '').strip(),
                "role": "student",
                "is_deleted": False
            }

            try:
                supabase.table("student_performance").insert(insert_data).execute()
                success += 1
            except Exception as e:
                errors.append(f"Row {i} ({name}): {str(e)}")

        if success:
            flash(f"Successfully added {success} student(s)!", "success")
        if errors:
            flash(f"Failed rows: {'; '.join(errors[:5])}" + (f" and {len(errors)-5} more..." if len(errors) > 5 else ""), "danger")

    except Exception as e:
        flash(f"Error processing CSV: {str(e)}", "danger")

    return redirect(url_for('add_student'))

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

    students = _recalc_risk(students)

    # ---------------- RISK COUNTS ----------------
    high_risk = len([s for s in students if s["risk_score"] >= 60])
    medium_risk = len([s for s in students if 40 <= s["risk_score"] < 60])
    low_risk = len([s for s in students if s["risk_score"] < 40])

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

    return render_template(
        "dashboard_principal.html",
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
        success_rate=success_rate
    )


@app.route("/principal/teachers")
def principal_teachers():
    if session.get("role") != "principal":
        return redirect(url_for("login"))

    teachers = supabase.table("teachers").select("*").execute().data or []
    return render_template("principal/teachers.html", teachers=teachers)


@app.route("/principal/feedback")
def principal_feedback():
    if session.get("role") != "principal":
        return redirect(url_for("login"))

    # Fetch latest feedback window
    window = None
    window_active = False
    try:
        windows = supabase.table("feedback_windows").select("*").order("created_at", desc=True).limit(1).execute().data or []
        if windows:
            window = windows[0]
            today = datetime.now().strftime("%Y-%m-%d")
            window_active = window["start_date"] <= today <= window["end_date"]
    except:
        pass

    # Fetch feedbacks for latest window only
    feedbacks = []
    try:
        query = supabase.table("student_feedback").select("*")
        if window:
            query = query.eq("window_id", window["id"])
        feedbacks = query.order("created_at", desc=True).execute().data or []
    except:
        feedbacks = []

    # Get unique teacher names for filter dropdown
    teacher_names = sorted(set(f["teacher_name"] for f in feedbacks if f.get("teacher_name")))

    # Apply filters
    filter_teacher = request.args.get("teacher_filter", "")
    filter_sentiment = request.args.get("sentiment_filter", "")

    if filter_teacher:
        feedbacks = [f for f in feedbacks if f.get("teacher_name") == filter_teacher]
    if filter_sentiment:
        feedbacks = [f for f in feedbacks if f.get("sentiment_label") == filter_sentiment]

    return render_template(
        "principal/feedback.html",
        feedbacks=feedbacks,
        window=window,
        window_active=window_active,
        teacher_names=teacher_names,
        filter_teacher=filter_teacher,
        filter_sentiment=filter_sentiment
    )


@app.route("/principal/create_feedback_window", methods=["POST"])
def create_feedback_window():
    if session.get("role") != "principal":
        return redirect(url_for("login"))

    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")

    if not start_date or not end_date:
        flash("Please provide both start and end dates.", "danger")
        return redirect(url_for("principal_feedback"))

    if end_date < start_date:
        flash("End date must be after start date.", "danger")
        return redirect(url_for("principal_feedback"))

    try:
        supabase.table("feedback_windows").insert({
            "start_date": start_date,
            "end_date": end_date,
            "created_by": session.get("user_id", "principal")
        }).execute()
        flash("Feedback window created successfully!", "success")
    except Exception as e:
        flash(f"Error creating feedback window: {str(e)}", "danger")

    return redirect(url_for("principal_feedback"))


@app.route("/principal/ai_analysis")
def principal_ai_analysis():
    if session.get("role") != "principal":
        return redirect(url_for("login"))

    selected_class = request.args.get("class_filter")
    selected_risk = request.args.get("risk_filter")
    selected_gender = request.args.get("gender_filter")

    response = supabase.table("student_performance").select("*").execute()
    rows = response.data or []

    filtered = []
    for r in rows:
        cls = str(r.get("class"))
        gender = str(r.get("gender")).lower()

        if selected_class and cls != selected_class:
            continue
        if selected_gender and gender != selected_gender.lower():
            continue
        filtered.append(r)

    total_students = len(filtered)
    high_risk = medium_risk = 0
    students = []

    for r in filtered:
        roll = r.get("roll")
        name = r.get("name")
        cls = r.get("class")
        gender = str(r.get("gender"))
        att = int(r.get("attendance") or 0)
        marks = int(r.get("marks") or 0)

        risk_score = max(0, 100 - ((att + marks) / 2))

        if att < 75 or marks < 40:
            risk = "High"
            high_risk += 1
            action = "Home Visit"
        elif att < 85 or marks < 55:
            risk = "Medium"
            medium_risk += 1
            action = "Extra Classes"
        else:
            risk = "Low"
            action = "Regular Monitoring"

        reason = f"Attendance: {att}%, Marks: {marks}"

        if selected_risk and risk != selected_risk:
            continue

        students.append((roll, name, cls, gender, att, marks, risk, reason, action, int(risk_score)))

    return render_template(
        "principal/ai_analysis.html",
        students=students,
        total_students=total_students,
        high_risk=high_risk,
        medium_risk=medium_risk
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

# ---------------- TTS PROXY (Google Translate TTS) ----------------
@app.route('/api/tts')
def api_tts():
    text = request.args.get('q', '')
    lang = request.args.get('tl', 'en')
    if not text or len(text) > 300:
        return "Bad request", 400
    import requests as _req
    try:
        resp = _req.get(
            'https://translate.google.com/translate_tts',
            params={'ie': 'UTF-8', 'client': 'tw-ob', 'tl': lang, 'q': text},
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=5
        )
        if resp.status_code == 200:
            return Response(resp.content, mimetype='audio/mpeg')
    except:
        pass
    return "TTS unavailable", 503

# ---------------- SERVICE WORKER (must be served from root) ----------------
@app.route('/sw.js')
def service_worker():
    return app.send_static_file('service-worker.js'), 200, {'Content-Type': 'application/javascript', 'Service-Worker-Allowed': '/'}

@app.route('/offline')
def offline_page():
    return render_template('offline.html')

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True, port=5001)