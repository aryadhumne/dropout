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

        # ---------- STUDENT ----------
        if role == "student":
            roll = request.form.get('roll', '').strip()
            name = request.form.get('name', '').strip()   # ✅ FIXED

            if not roll or not name:
                flash("Roll and Name are required", "error")
                return redirect(url_for('register'))

            existing = supabase.table("users").select("*").eq("roll", roll).execute()
            if existing.data:
                flash("Roll number already registered", "error")
                return redirect(url_for('register'))

            data["roll"] = roll
            data["name"] = name

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
@app.route('/student/dashboard')
def dashboard_student():
    if session.get('role') != 'student':
        flash("Please login first", "error")
        return redirect(url_for('login'))

    roll = session.get('roll')
    res = supabase.table("users").select("*").eq("role", "student").eq("roll", roll).execute()
    student = res.data[0] if res.data else None

    return render_template("dashboard_student.html", student=student)


# ---------------- TEACHER DASHBOARD ----------------
@app.route('/teacher/dashboard')
def dashboard_teacher():
    if session.get('role') != 'teacher':
        flash("Unauthorized access", "error")
        return redirect(url_for('login'))

    email = session.get('email')
    res = supabase.table("users").select("*").eq("role", "teacher").eq("email", email).execute()
    teacher = res.data[0] if res.data else None

    return render_template("dashboard_teacher.html", teacher=teacher)


# ---------------- PRINCIPAL DASHBOARD ----------------
@app.route('/principal/dashboard')
def dashboard_principal():
    if session.get('role') != 'principal':
        flash("Unauthorized access", "error")
        return redirect(url_for('login'))

    email = session.get('email')

    # Fetch principal
    pres = supabase.table("users") \
        .select("*") \
        .eq("role", "principal") \
        .eq("email", email) \
        .execute()

    principal = pres.data[0] if pres.data else None

    # Fetch students
    sres = supabase.table("student_performance") \
        .select("*") \
        .execute()

    students = sres.data if sres.data else []

    # Group students division-wise
    division_wise = {}
    for s in students:
        div = s.get("division", "Unknown")
        division_wise.setdefault(div, []).append(s)

    return render_template(
        "dashboard_principal.html",
        principal=principal,
        students=students,
        division_wise=division_wise
    )


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
@app.route('/admin/dashboard')
def dashboard_admin():
    if session.get('role') != 'admin':
        flash("Unauthorized access", "error")
        return redirect(url_for('login'))

    email = session.get('email')
    res = supabase.table("users").select("*").eq("role", "admin").eq("email", email).execute()
    admin = res.data[0] if res.data else None

    return render_template("dashboard_admin.html", admin=admin)


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for('login'))


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True, port=5001)
