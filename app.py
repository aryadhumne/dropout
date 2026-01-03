from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "secret_key_for_flask_sessions"  # Needed for flash messages

# Temporary "users" storage for demo purposes
registered_users = []

@app.route('/')
def home():
    return redirect(url_for('login'))

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password'].strip()
        role = request.form['role'].strip()

        # Find user
        user = next((u for u in registered_users if u['email'] == email and u['password'] == password and u['role'] == role), None)
        
        if user:
            # Redirect to role-specific dashboard
            if role == 'teacher':
                return redirect(url_for('dashboard_teacher'))
            elif role == 'volunteer':
                return redirect(url_for('dashboard_volunteer'))
            elif role == 'coordinator':
                return redirect(url_for('dashboard_coordinator'))
        else:
            flash("Invalid credentials or role. Please register first or try again.", "error")

    return render_template('login.html')

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password'].strip()
        role = request.form['role'].strip()

        if any(u['email'] == email for u in registered_users):
            flash("User already registered. Please login.", "error")
        else:
            registered_users.append({'email': email, 'password': password, 'role': role})
            flash("Registration successful! You can now login.", "success")
            return redirect(url_for('login'))
            
    return render_template('register.html')

# ---------------- DASHBOARDS ----------------
@app.route('/dashboard/teacher')
def dashboard_teacher():
    return render_template('dashboard_teacher.html')

@app.route('/dashboard/volunteer')
def dashboard_volunteer():
    return render_template('dashboard_volunteer.html')

@app.route('/dashboard/coordinator')
def dashboard_coordinator():
    return render_template('dashboard_coordinator.html')

# ---------------- RUN APP ----------------
if __name__ == '__main__':
    app.run(debug=True, port=5001)
