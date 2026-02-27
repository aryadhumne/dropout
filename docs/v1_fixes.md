# EduDrop v1 Fixes & Feature Log

## 1. Complete UI Makeover

- **Design System**: New CSS design system (`static/css/main.css`) with CSS custom properties
- **Color Scheme**: Pink-to-orange gradient (`#e72191` to `#ff951a`) as accent, dark navy (`#122132`) for sidebar/nav/footer
- **Font**: Plus Jakarta Sans (400–800 weights) via Google Fonts
- **Template Inheritance**: `base.html` (dashboard layout), `base_auth.html` (login/register layout) for consistent UI across all pages
- **Responsive Design**: Mobile-friendly sidebar with overlay, hamburger toggle, responsive grid layouts
- **Landing Page**: Hero section, feature cards grid, step-by-step "How It Works" section, CTA section
- **Footer**: Multi-column dark footer (brand, platform links, role links, about section)
- **Select Role Page**: 2x2 grid of animated role tiles with hover effects and gradient accents
- **Stat Cards**: Reusable card components with left-border color coding for dashboards
- **Tables**: Clean table styling (`table-clean`) used across all dashboards

---

## 2. Teacher Email Validation

- **File**: `app.py` — `role_login()` function
- **Change**: When role is "teacher", the system queries the `teachers` table to verify the email exists before allowing login
- **Error Message**: "Invalid Email ID. Please contact your principal." if email is not found
- **Purpose**: Only emails added by the principal (via "Add Teacher") can log in as teacher

---

## 3. Principal Register/Login with Password Hashing

- **File**: `app.py` — `role_login()` function
- **Change**: Principal login page now has Register and Login modes
- **Register**: Checks if email already exists in `users` table, then inserts with `generate_password_hash()`
- **Login**: Verifies email exists in `users` table, then checks password with `check_password_hash()`
- **Library**: `werkzeug.security` for password hashing (PBKDF2)

---

## 4. Student Dashboard — Full Data Display

- **File**: `templates/student/dashboard.html`
- **Change**: Reorganized into a two-column layout:
  - **Left card (Academic Details)**: Table layout showing standard, division, roll no, gender, email, month, risk status, risk reason
  - **Right card (Performance Overview)**: Compact grid tiles for attendance, monthly test, assignment, quiz, risk score, performance score, risk level
  - **Parent/Guardian Details**: Clean table with name, phone, alt phone, address
- **Data Fields Added**: gender, monthly_test_score, risk_score, risk_reason, parent_name, parent_phone, parent_alt_phone, parent_address
- **All data sourced from**: `student_performance` table (populated by teacher via "Add Student")

---

## 5. Gender "Other" in Principal Pie Chart

- **Files**: `app.py` (dashboard_principal route), `templates/dashboard_principal.html`
- **Change in app.py**: Added `other_risk` counter alongside `boys_risk` and `girls_risk`. Students with gender not "male" or "female" and risk "High" increment `other_risk`
- **Change in template**: Doughnut chart updated from 2 segments to 3 — Boys (pink `#e72191`), Girls (orange `#ff951a`), Other (purple `#8b5cf6`)

---

## 6. Student Feedback to Principal

- **New Supabase table**: `student_feedback` (columns: id, student_id, student_name, standard, division, feedback_text, teacher_name, created_at)
- **New route**: `POST /student/feedback` — validates session, fetches student info, inserts feedback with selected teacher name
- **Student dashboard**: Feedback form includes a "Select a teacher" dropdown (populated from `teachers` table)
- **Principal dashboard**: New "Student Feedback" section with table showing student name, class, division, teacher name, feedback text, date
- **Visibility**: Feedback is only visible on the Principal's page, NOT on the Teacher's page

---

## 7. Apply for Leave Backend

- **New Supabase table**: `student_leaves` (columns: id, student_id, student_name, standard, division, leave_date, reason, status, created_at)
- **New route**: `POST /student/leave` — validates session, fetches student info, inserts leave with status "Pending"
- **Student dashboard**: Leave form with date picker and reason textarea
- **Teacher dashboard**: New "Student Leave Requests" section with table showing student name, class, date, reason, status, and Approve/Reject buttons
- **Teacher action route**: `POST /teacher/leave/<leave_id>/<action>` — updates leave status to "Approved" or "Rejected"

---

## 8. NGO Admin — Approve/Reject Interventions with Proof Images

- **Files**: `app.py`, `templates/dashboard_admin.html`
- **Volunteer flow**: When status is "Completed", volunteer must upload proof image (via Cloudinary). The intervention is saved with `approval_status: "Pending"`
- **Admin dashboard**: Shows pending interventions in a table with student name, roll, type, status, notes, volunteer name, proof image thumbnail (clickable to full-size), and Approve/Reject buttons
- **Approve route**: `POST /approve-intervention/<id>` — sets `approval_status: "Approved"`
- **Reject route**: `POST /reject-intervention/<id>` — sets `approval_status: "Rejected"`

---

## 9. Financial Aid Approval Flow

- **File**: `app.py` — volunteer dashboard POST handler, approve route
- **Change**: When intervention type is "Financial Aid":
  - `approval_status` is always set to "Pending" (regardless of completion status)
  - If marked "Completed", status is saved as "Awaiting Approval" instead of "Completed"
  - Proof image upload is still required for completed Financial Aid cases
- **Admin approval**: When admin approves a Financial Aid case with status "Awaiting Approval", the status is updated to "Completed"
- **Admin template**: Financial Aid entries show "Requires Approval" label and "Awaiting Approval" badge

---

## 10. Accessibility Improvements

- **Skip Link**: Hidden "Skip to main content" link at top of page, visible on keyboard focus
- **ARIA Labels**: Added `role` attributes and `aria-label` on navigation, main content, sidebar, forms, alerts, role tiles
- **Keyboard Navigation**: Escape key closes sidebar on mobile
- **Focus Indicators**: `*:focus-visible` with accent-colored outline on all focusable elements
- **Semantic HTML**: `<main>`, `<header>`, `<nav>`, `<aside>`, `<footer>` elements with proper roles
- **Screen Reader**: `aria-hidden="true"` on decorative icons, `aria-expanded` on sidebar toggle

---

## 11. Flash Message Auto-Dismiss

- **File**: `templates/base.html`
- **Change**: Flash messages have `flash-auto-dismiss` class. JavaScript auto-removes them after 4 seconds with a 0.5s fade-out transition
- **Purpose**: Prevents flash messages from persisting when navigating between JS-based dashboard tabs (e.g., student dashboard)

---

## 12. Language Change Option (Multi-language Support)

- **Pages**: All pages — `base.html`, `base_auth.html`, `index.html`, `select_role.html`, `ngo_role.html`
- **Languages**: English, Hindi (हिन्दी), Marathi (मराठी)
- **Implementation**: Google Translate Element API integrated via hidden widget. Custom styled dropdown triggers translation
- **Persistence**: Language preference saved in `edudrop_lang` cookie (365-day expiry). On page load, saved language is restored automatically
- **UI**: Clean dropdown styled with `.lang-switcher` CSS class, placed in topbar (dashboards), header bar (auth pages), and nav (landing page)
- **Google banner hidden**: CSS hides the default Google Translate bar/banner for a clean look

---

## 13. EduDrop Logo Links to Homepage

- **Sidebar** (`base.html`): Brand changed from `<div>` to `<a>` linking to `/` (homepage)
- **Landing page** (`index.html`): Logo in nav wrapped in `<a>` linking to `/`
- **CSS**: `a.sidebar-brand` selector ensures white color is maintained on the dark sidebar

---

## 14. UI Polish & Fixes

- **Sidebar color**: Changed `--primary` from `#1e1b4b` to `#122132` (rgb(18, 33, 50)) across sidebar, landing nav, and footer
- **Landing nav**: Dark background with white text links
- **Logout button**: Moved to sidebar footer (bottom), removed duplicate logout links from all 5 sidebar blocks (student, teacher, principal, admin, volunteer)
- **Logout styling**: `.sidebar-footer a` styled with white text, flex layout, hover turns reddish
- **Student dashboard layout**: Reorganized from scattered grid to clean two-column card layout

---

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Flask (Python) |
| Database | Supabase (PostgreSQL) |
| ML Model | Scikit-learn (Random Forest), SHAP for explainability |
| Image Upload | Cloudinary |
| Frontend | Jinja2 templates, Bootstrap 5.3.3, Chart.js |
| Password Hashing | Werkzeug (PBKDF2) |
| Translation | Google Translate Element API |
| Icons | Bootstrap Icons 1.11.3 |
| Font | Plus Jakarta Sans (Google Fonts) |

---

## Supabase Tables Used

| Table | Purpose |
|---|---|
| `users` | Principal accounts (email, password hash, role) |
| `students` | Student login accounts (linked to student_performance) |
| `student_performance` | All student academic data, attendance, risk scores |
| `teachers` | Teacher records added by principal |
| `interventions` | Teacher-side interventions |
| `ngo_interventions` | NGO volunteer interventions with proof images and approval status |
| `ngo_notifications` | Notifications for NGO |
| `risk_history` | Historical risk tracking |
| `student_feedback` | Student feedback about teachers (visible to principal only) |
| `student_leaves` | Student leave applications (managed by teachers) |
