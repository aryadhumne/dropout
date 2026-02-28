# EduBot - AI Chatbot Documentation

## Overview

EduBot is an AI-powered chatbot integrated across 4 pages of the EduDrop platform. Each instance serves a different role with tailored behavior, system prompts, and contextual data.

| Page | Role | Purpose |
|------|------|---------|
| Homepage | `homepage` | Explains EduDrop features, how it works, who can use it |
| Student Dashboard | `student` | Personal academic counselor with student's own data |
| Teacher Dashboard | `teacher` | Teaching assistant with class-wide risk statistics |
| Principal Dashboard | `principal` | School analytics assistant with school-wide data |

---

## AI Model

### Model: **Gemini 2.5 Flash**

- **Provider:** Google (Gemini API)
- **Model ID:** `gemini-2.5-flash`
- **API Type:** REST API (HTTP POST)
- **Endpoint:** `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent`

### Why Gemini 2.5 Flash?

1. **Free tier** — No cost for the project. Gemini offers a generous free tier with enough quota for a school-level chatbot.
2. **Fast responses** — Flash models are optimized for speed, giving responses in 1-3 seconds, ideal for real-time chat.
3. **Lightweight** — Designed for concise, focused responses (we instruct 2-3 sentences max), not heavy reasoning tasks.
4. **REST API** — We call the REST API directly using Python `requests` instead of the `google-generativeai` library, because the older Python library (v0.8.5) had gRPC timeout issues with newer models.
5. **Availability** — Gemini 2.5 Flash is the latest available model on Google's free tier. Older models (`gemini-2.0-flash`, `gemini-2.0-flash-lite`) were deprecated for new API keys.

---

## Architecture

```
User (Browser)
    |
    |  Click robot icon -> toggleChat()
    |  Type message or speak -> sendChat() / toggleVoiceInput()
    |
    v
Frontend (chatbot.html partial)
    |
    |  POST /api/chat  { message: "...", role: "student" }
    |
    v
Flask Backend (app.py)
    |
    |  1. Validate role & session
    |  2. Build context from Supabase (role-specific data)
    |  3. Construct prompt = system_prompt + context + user_message
    |  4. Call Gemini REST API (10s timeout)
    |  5. Return AI response as JSON
    |
    v
Gemini 2.5 Flash API
    |
    |  Returns generated text
    |
    v
Frontend displays response
    |  + TTS button (speakText)
```

---

## Backend (`app.py`)

### API Route: `POST /api/chat`

**Location:** `app.py` (lines ~1058-1111)

**Request body:**
```json
{
  "message": "What is my attendance?",
  "role": "student"
}
```

**Response:**
```json
{
  "response": "Your attendance is 77%, which is above the 75% threshold..."
}
```

### Flow:

1. **Role validation** — Checks `role` is one of: `homepage`, `student`, `teacher`, `principal`
2. **Session validation** — For non-homepage roles, verifies `session['role']` matches the requested role (prevents spoofing)
3. **Context building** — Fetches real-time data from Supabase based on role:
   - `student`: Individual student's attendance, test scores, assignments, quiz, risk status
   - `teacher`: Total students, high/medium/low risk counts, pending leave requests
   - `principal`: Total students, high risk count, average attendance, gender-wise risk, teacher count
   - `homepage`: No data needed
4. **Prompt construction** — Combines: system prompt + contextual data + user's message
5. **Gemini API call** — REST POST with 10-second timeout
6. **Fallback** — If Gemini fails, returns a simple "temporarily unavailable" message and activates a 5-minute cooldown to avoid repeated failed calls

### System Prompts (per role):

| Role | Personality | Key Instructions |
|------|------------|------------------|
| `homepage` | Welcoming, informative | Answer about EduDrop features, roles, getting started |
| `student` | Friendly, supportive, encouraging | Give specific advice based on student's numbers |
| `teacher` | Professional, actionable | Help with risk scores, interventions, leave requests |
| `principal` | Strategic, data-focused | Interpret analytics, plan interventions, manage teachers |

### Context Data Passed to AI:

**Student:**
```
Student Profile:
- Name: Arya Deepak Dhumne
- Attendance: 77%
- Monthly Test Score: 90
- Assignment Score: Completed
- Quiz Score: 0
- Risk Status: Low
```

**Teacher:**
```
Teacher Dashboard Summary:
- Total Students: 15
- High Risk: 3
- Medium Risk: 5
- Low Risk: 7
- Pending Leave Requests: 2
```

**Principal:**
```
School Analytics:
- Total Students: 15
- High Risk: 3
- Average Attendance: 72%
- Boys at High Risk: 2, Girls at High Risk: 1
- Total Teachers: 3
```

### Error Handling:

- **Gemini timeout/failure** — 5-minute cooldown (`_gemini_cooldown`), falls back to a simple unavailable message
- **Non-numeric data** — `_safe_int()` helper prevents crashes when database fields contain text instead of numbers
- **Missing session** — Returns 401 Unauthorized for non-homepage roles
- **Empty message** — Returns 400 Bad Request

---

## Frontend (`templates/partials/chatbot.html`)

### Reusable Jinja2 Partial

The chatbot widget is a single file included in all 4 pages using `{% include 'partials/chatbot.html' %}`. Each page sets 3 variables before including:

```html
{% set chatbot_greeting = "Hi! I'm EduBot..." %}
{% set chatbot_subtitle = "AI Academic Counselor" %}
{% set chatbot_role = "student" %}
{% include 'partials/chatbot.html' %}
```

### UI Components:

1. **Toggle Button** — Floating robot icon (bottom-right corner), click to open/close
2. **Chat Panel** — Header (title + subtitle), message area, input row
3. **Input Row** — Mic button (STT) + text input + send button
4. **Bot Messages** — Each response includes a speaker button (TTS)

### JavaScript Functions:

| Function | Purpose |
|----------|---------|
| `toggleChat()` | Opens/closes the chat panel |
| `sendChat()` | Sends message to `/api/chat`, displays response |
| `speakText(btn)` | Text-to-Speech — reads bot response aloud |
| `toggleVoiceInput()` | Speech-to-Text — records voice and auto-sends |
| `_getBestVoice()` | Selects the best available TTS voice |

---

## Speech Features

### Text-to-Speech (TTS)

- **API:** Browser Web Speech API (`window.speechSynthesis`)
- **Cost:** Free (built into browser)
- **Voice Selection:** Prioritizes high-quality voices: Google UK English Female > Samantha (Mac) > Karen > Daniel > Rishi > Microsoft Zira
- **Settings:** Rate 0.9, Pitch 1.05, Volume 1.0
- **Toggle:** Click speaker icon to play, click again to stop

### Speech-to-Text (STT)

- **API:** Browser Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`)
- **Cost:** Free (built into browser)
- **Language:** `en-IN` (Indian English)
- **Behavior:** Click mic -> speak -> transcript auto-fills input -> auto-sends message
- **Visual:** Mic button turns red with pulse animation while listening
- **Browser Support:** Works best in Chrome

---

## Files

| File | Role |
|------|------|
| `app.py` (lines 935-1111) | Backend: route, prompts, context builders, Gemini API call |
| `templates/partials/chatbot.html` | Frontend: reusable chat widget (HTML + JS) |
| `templates/index.html` | Includes chatbot with `role=homepage` |
| `templates/student/dashboard.html` | Includes chatbot with `role=student` |
| `templates/teacher/dashboard.html` | Includes chatbot with `role=teacher` |
| `templates/dashboard_principal.html` | Includes chatbot with `role=principal` |
| `static/css/main.css` | Chatbot styling (lines ~1401-1564) |
| `.env` | `GEMINI_API_KEY` environment variable |

---

## Security

1. **Role validation** — Homepage chatbot works without login; all other roles require matching session
2. **No role spoofing** — Backend verifies `session['role'] == requested_role`
3. **API key protection** — Gemini key stored in `.env`, never exposed to frontend
4. **Input sanitization** — Bot responses are HTML-escaped before rendering (`txt.replace(/</g,'&lt;')`)

---

## Cost

| Component | Cost |
|-----------|------|
| Gemini 2.5 Flash API | Free (free tier) |
| Text-to-Speech | Free (browser API) |
| Speech-to-Text | Free (browser API) |
| **Total** | **$0** |
