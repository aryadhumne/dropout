# EduDrop - Complete Documentation

## What is EduDrop?

EduDrop is a web-based platform that helps schools identify students at risk of dropping out. It provides dashboards for **Students**, **Teachers**, **Principals**, **NGO Admins**, and **Volunteers** — each with role-specific features, analytics, and an AI chatbot.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask (Python 3.12) |
| Database | Supabase (PostgreSQL) |
| AI Chatbot | Google Gemini 2.5 Flash (REST API) |
| ML Model | Random Forest Classifier (scikit-learn) |
| Explainability | SHAP (TreeExplainer) |
| Sentiment Analysis | TextBlob |
| Image Upload | Cloudinary |
| Frontend | HTML/CSS/JS, Bootstrap 5, Chart.js |
| Translations | Google Translate (20+ Indian languages) |
| Offline Support | Service Worker (PWA) |

---

## Database Tables (Supabase)

| Table | Purpose |
|-------|---------|
| `users` | All user accounts (NGO admins, volunteers, principals) — email, password, role, name, district |
| `students` | Student login credentials — email, password, linked `student_performance_id` |
| `student_performance` | Academic data — name, roll, standard, division, attendance, test scores, assignment, quiz, risk_score, risk_status, risk_reason, parent info, subjects |
| `teachers` | Teacher profiles — name, email, assigned_class |
| `student_feedback` | Student feedback with sentiment — text, sentiment_score, sentiment_label |
| `student_leaves` | Leave applications — date, reason, status (Pending/Approved/Rejected) |
| `ngo_interventions` | NGO volunteer interventions — type, status, proof image, approval_status |
| `ngo_notifications` | High-risk alerts sent to NGOs |
| `risk_history` | Historical risk score data for trend charts |

---

## Risk Score Calculation

Risk is calculated when a teacher adds or edits a student. The formula assigns points based on 4 factors:

| Factor | Threshold | Points |
|--------|-----------|--------|
| Monthly Test Score | < 35 | +40 |
| Attendance | < 60% | +30 |
| Assignment Status | Incomplete/Poor | +15 |
| Quiz Status | Incomplete/Poor | +15 |

**Maximum score: 100**

| Score Range | Category | Status |
|-------------|----------|--------|
| 60–100 | High Risk | At Risk |
| 40–59 | Medium Risk | Medium Risk |
| 0–39 | Low Risk | Safe |

The score is stored in the `risk_score` field of `student_performance`. For older students that don't have it stored, it's recalculated on-the-fly from their existing data using the `_recalc_risk()` helper function.

### ML Model (for NGO Dashboard)

A **Random Forest Classifier** is also trained for risk prediction:
- **Features**: attendance, monthly_test_score, assignment, quiz
- **Classes**: 0=Low, 1=Medium, 2=High
- **Config**: 100 trees, max_depth=8, min_samples_split=10
- **Files**: `risk_model.pkl`, `model_features.pkl`
- **Explainability**: SHAP TreeExplainer shows top 3 contributing factors per student

---

## AI Chatbot

### Model
**Google Gemini 2.5 Flash** via REST API (not the Python library — gRPC had timeout issues).

### Why Gemini 2.5 Flash?
- Free tier available (no cost)
- Fast response times (~2-3 seconds)
- Good at understanding educational context
- REST API is reliable (unlike the gRPC-based Python library which timed out)

### How It Works

1. User sends a message from any page
2. Frontend sends `POST /api/chat` with `{message, role}`
3. Backend validates the role and session
4. Builds role-specific context from Supabase data
5. Constructs a prompt: system prompt + context + user message
6. Calls Gemini 2.5 Flash REST API
7. Returns AI response (falls back to a generic error if Gemini fails)

### Roles & Context

| Role | System Prompt | Context Data |
|------|--------------|-------------|
| **Homepage** | Explain EduDrop features, how to get started | None (public) |
| **Student** | Friendly academic counselor | Student's name, attendance, test score, assignment, quiz, risk status |
| **Teacher** | Professional teaching assistant | Summary stats + every student's full details (name, class, attendance, scores, risk) |
| **Principal** | Strategic analytics assistant | School-wide stats: avg attendance, gender risk breakdown, teacher count |

### Speech Features
- **Text-to-Speech (TTS)**: Web Speech API `speechSynthesis` — speaker button on each bot message. Prefers high-quality voices (Google UK English Female, Samantha, etc.). Rate: 0.9, Pitch: 1.05.
- **Speech-to-Text (STT)**: Web Speech API `SpeechRecognition` — mic button in input area. Language: `en-IN`. Auto-sends message after transcription.

### Cooldown
If Gemini fails (timeout, 429 rate limit, etc.), there's a **5-minute cooldown** before retrying. During cooldown, the chatbot returns a "temporarily unavailable" message.

---

## Offline Support (PWA)

### Service Worker (`/sw.js`)

The app uses a Service Worker for offline access:

| Content Type | Strategy | Behavior |
|-------------|----------|----------|
| HTML pages | Network-first | Fetches fresh page, caches it. If offline, serves cached version. |
| Static assets (CSS, JS, fonts, images) | Cache-first | Serves from cache instantly. Falls back to network if not cached. |
| API calls (`/api/*`) | Network only | Not cached (chatbot, data APIs). |

### Pre-cached Assets
On install, the SW pre-caches: `main.css`, `manifest.json`, Bootstrap CSS, Bootstrap Icons, Chart.js.

### Offline Fallback
If a user visits an uncached page while offline, they see a friendly "You're Offline" page with a retry button.

### How to Use
1. Visit pages while online — they get cached automatically
2. Go offline — those pages still load with all their data
3. The app can also be "installed" as a standalone PWA on mobile/desktop

---

## Authentication & Roles

### Login Flow
1. User goes to `/select_role` and picks their role
2. Redirected to role-specific login page
3. Credentials checked against Supabase
4. Session is set: `session['role']`, `session['email']`, `session['student_id']` (if student)
5. Redirected to role dashboard

### Roles & Access

| Role | Dashboard | Key Features |
|------|-----------|-------------|
| **Student** | `/student/dashboard` | View performance, attendance chart, submit feedback (sentiment analyzed), apply for leave |
| **Teacher** | `/teacher/dashboard` | View risk stats, add/edit/delete students, manage leave requests, risk-by-class charts |
| **Principal** | `/dashboard/principal` | School-wide analytics, filter by class/risk/gender, manage teachers, export CSV, red flags |
| **NGO Admin** | `/ngo/admin/dashboard` | Approve/reject volunteer interventions, add volunteers |
| **Volunteer** | `/volunteer/dashboard` | View at-risk students with ML predictions + SHAP explanations, create interventions with proof images |

---

## All Routes

### Public
| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Homepage |
| `/select_role` | GET | Role selection |
| `/about` | GET | About page |
| `/forgot-password` | GET/POST | Password reset (email lookup) |
| `/reset-password` | GET/POST | Set new password |
| `/offline` | GET | Offline fallback page |
| `/sw.js` | GET | Service worker JS |

### Student
| Route | Method | Purpose |
|-------|--------|---------|
| `/student/register` | GET/POST | Register student account |
| `/student/login` | GET/POST | Student login |
| `/student/dashboard` | GET | Dashboard with performance data |
| `/student/feedback` | POST | Submit feedback (sentiment analysis) |
| `/student/leave` | POST | Apply for leave |
| `/student/set_password` | GET/POST | Initial password setup |

### Teacher
| Route | Method | Purpose |
|-------|--------|---------|
| `/teacher/dashboard` | GET | Dashboard with risk charts |
| `/teacher/add_student` | GET/POST | Add new student |
| `/teacher/student_records` | GET | View all students by class |
| `/teacher/edit_student/<id>` | GET/POST | Edit student details |
| `/teacher/delete_student/<id>` | POST | Soft-delete student |
| `/teacher/leave_requests` | GET | View/manage leave requests |
| `/teacher/leave/<id>/<action>` | POST | Approve/reject leave |

### Principal
| Route | Method | Purpose |
|-------|--------|---------|
| `/dashboard/principal` | GET | School analytics dashboard |
| `/add_teacher` | POST | Add teacher |
| `/remove_teacher/<id>` | GET | Remove teacher |
| `/export_high_risk_csv` | GET | Download high-risk CSV |
| `/send_ngo` | GET | Send alerts to NGO |

### NGO
| Route | Method | Purpose |
|-------|--------|---------|
| `/ngo` | GET | NGO role selection |
| `/ngo/admin/login` | GET/POST | Admin login |
| `/ngo/admin/register` | GET/POST | Admin registration |
| `/ngo/admin/dashboard` | GET | Admin dashboard |
| `/admin/add-volunteer` | GET/POST | Add volunteer |
| `/volunteer/login` | GET/POST | Volunteer login |
| `/volunteer/register` | GET/POST | Volunteer registration |
| `/volunteer/dashboard` | GET/POST | Volunteer dashboard + interventions |
| `/approve-intervention/<id>` | POST | Approve intervention |
| `/reject-intervention/<id>` | POST | Reject intervention |

### API
| Route | Method | Purpose |
|-------|--------|---------|
| `/api/chat` | POST | AI chatbot (multi-role) |
| `/get-ngos/<district>` | GET | List NGOs by district |

---

## Multi-Language Support

EduDrop supports **20+ Indian languages** via Google Translate:

Hindi, Bengali, Telugu, Marathi, Tamil, Gujarati, Kannada, Malayalam, Punjabi, Odia, Assamese, Urdu, Sanskrit, Nepali, Sindhi, Kashmiri, Dogri, Maithili, Manipuri, Santali, Konkani

The language selector is in the top navbar. Selection is saved as a cookie (`edudrop_lang`) and persists across page loads.

---

## External Services

| Service | Purpose | Config |
|---------|---------|--------|
| **Supabase** | Database + Auth backend | `SUPABASE_URL`, `SUPABASE_ANON_KEY` in `.env` |
| **Google Gemini** | AI chatbot responses | `GEMINI_API_KEY` in `.env` |
| **Cloudinary** | Upload intervention proof images | Hardcoded in `app.py` (cloud: `de20jxqpu`) |
| **Google Translate** | Multi-language support | Free JS embed |
| **TextBlob** | Sentiment analysis on student feedback | Python library (no API key) |

---

## File Structure

```
dropout/
├── app.py                          # Main Flask app (~1900 lines)
├── supabase_client.py              # Supabase connection
├── train_model.py                  # ML model training script
├── risk_model.pkl                  # Trained Random Forest model
├── model_features.pkl              # Feature names
├── .env                            # Environment variables
├── requirements.txt                # Python dependencies
│
├── static/
│   ├── css/
│   │   ├── main.css                # Primary stylesheet
│   │   ├── style.css               # Legacy styles
│   │   └── teacher.css             # Teacher-specific styles
│   ├── js/
│   │   ├── app.js                  # Client-side offline/sync logic
│   │   └── teacher.js              # Teacher page interactions
│   ├── service-worker.js           # PWA service worker
│   ├── manifest.json               # PWA manifest
│   ├── icons/                      # App icons
│   └── images/                     # UI images
│
├── templates/
│   ├── base.html                   # Main layout (sidebar, topbar, navbar)
│   ├── base_auth.html              # Auth page layout
│   ├── index.html                  # Homepage/landing
│   ├── select_role.html            # Role selection
│   ├── about.html                  # About page
│   ├── offline.html                # Offline fallback
│   │
│   ├── student/
│   │   ├── dashboard.html          # Student dashboard
│   │   ├── login.html              # Student login
│   │   └── set_password.html       # Password setup
│   │
│   ├── teacher/
│   │   ├── base.html               # Teacher layout (sidebar links)
│   │   ├── dashboard.html          # Teacher dashboard + charts
│   │   ├── add_student.html        # Add student form
│   │   ├── student_records.html    # Student list by class
│   │   ├── edit_student.html       # Edit student
│   │   ├── leave_requests.html     # Leave management
│   │   └── students.html           # Alternative student list
│   │
│   ├── dashboard_principal.html    # Principal dashboard
│   ├── dashboard_admin.html        # NGO admin dashboard
│   ├── dashboard_volunteer.html    # Volunteer dashboard
│   │
│   ├── partials/
│   │   └── chatbot.html            # Reusable AI chatbot widget
│   │
│   └── (login/register pages for each role)
│
└── DOCUMENTATION.md                # This file
```

---

## How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Set up .env with Supabase and Gemini keys
# SUPABASE_URL=...
# SUPABASE_ANON_KEY=...
# SECRET_KEY=...
# GEMINI_API_KEY=...

# Run the server
python app.py
# Server starts at http://127.0.0.1:5001
```

---

## Key Design Decisions

1. **Gemini REST API over Python library** — The `google-generativeai` Python library (v0.8.5) uses gRPC which caused `DeadlineExceeded` timeouts. Direct REST API via `requests.post()` works reliably.

2. **Jinja2 partials for chatbot** — Instead of copy-pasting chatbot code in 4 templates, a reusable `partials/chatbot.html` is parameterized with role, greeting, and subtitle.

3. **`_recalc_risk()` helper** — Older students in the DB don't have `risk_score` stored (it was calculated but not saved). This helper recalculates it from existing fields on-the-fly.

4. **Network-first caching for pages** — Ensures users always see fresh data when online, but can still access cached pages offline.

5. **Soft-delete for students** — Students are marked `is_deleted=True` rather than actually removed, preserving data integrity.
