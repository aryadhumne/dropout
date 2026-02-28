# EduDrop - AI/ML Features Documentation

A comprehensive guide to every AI and Machine Learning feature used in EduDrop, covering what each feature does, which model/library/API it uses, why that approach was chosen, and how it was trained or configured.

---

## Table of Contents

1. [Student Dropout Risk Prediction](#1-student-dropout-risk-prediction)
2. [SHAP Explainability](#2-shap-explainability)
3. [Sentiment Analysis on Student Feedback](#3-sentiment-analysis-on-student-feedback)
4. [Generative AI Chatbot (EduBot)](#4-generative-ai-chatbot-edubot)
5. [AI-Powered Volunteer Suggestions](#5-ai-powered-volunteer-suggestions)
6. [Text-to-Speech (TTS)](#6-text-to-speech-tts)
7. [Speech-to-Text (STT)](#7-speech-to-text-stt)
8. [Risk Score Calculation Engine](#8-risk-score-calculation-engine)

---

## 1. Student Dropout Risk Prediction

### What It Does
Predicts whether a student is at **Low**, **Medium**, or **High** risk of dropping out based on their academic performance metrics. This prediction is shown on the volunteer dashboard alongside each at-risk student, helping NGO workers prioritize interventions.

### Model Used
**Random Forest Classifier** from scikit-learn (`sklearn.ensemble.RandomForestClassifier`)

### Why Random Forest?
- **Handles tabular data well** — academic metrics are structured numeric features, which tree-based models excel at
- **No neural network overhead** — fast inference on a single server, no GPU required
- **Interpretable** — works natively with SHAP for feature importance explanations (see Section 2)
- **Robust to outliers** — student data can have extreme values (0% attendance, 100% scores), and ensemble methods handle this gracefully
- **Zero cost** — scikit-learn is fully open-source

### How It Was Trained

**Training script:** `train_model.py`

**Data generation:**
- 500 synthetic student records generated with realistic distributions
- Features follow normal distributions clipped to valid ranges:
  - `attendance`: mean=70, std=18, range [10, 100]
  - `monthly_test`: mean=55, std=22, range [0, 100]
  - `assignment`: mean=60, std=25, range [0, 100]
  - `quiz`: mean=58, std=20, range [0, 100]

**Label creation (ground truth):**
A weighted risk score formula determines each student's label:
```
risk_score = (100 - attendance) * 0.35
           + (100 - monthly_test) * 0.25
           + (100 - assignment) * 0.20
           + (100 - quiz) * 0.20
           + Gaussian noise (mean=0, std=5)
```
Labels assigned:
- **High Risk (2):** risk_score >= 60
- **Medium Risk (1):** 35 <= risk_score < 60
- **Low Risk (0):** risk_score < 35

**Hyperparameters:**
| Parameter | Value | Reason |
|-----------|-------|--------|
| n_estimators | 100 | Enough trees for stable predictions |
| max_depth | 8 | Prevents overfitting on 500 samples |
| min_samples_split | 10 | Ensures leaf nodes have meaningful sample sizes |
| random_state | 42 | Reproducible results |

**Validation:**
- 5-fold cross-validation with accuracy scoring
- Feature importances printed after training

**Output files:**
- `risk_model.pkl` — serialized trained model (loaded at app startup via `joblib.load`)
- `model_features.pkl` — feature name list `["attendance", "monthly_test", "assignment", "quiz"]`

### How It's Used at Runtime
1. When the volunteer dashboard loads, each student's metrics are extracted
2. A NumPy array `[[attendance, monthly_test, assignment, quiz]]` is created
3. `model.predict()` returns the risk class (0/1/2)
4. `model.predict_proba()` returns confidence percentages for each class
5. The highest probability becomes the displayed confidence score

**Code location:** `app.py` — function `predict_student_risk()` inside the volunteer dashboard route

---

## 2. SHAP Explainability

### What It Does
Provides human-readable explanations for each risk prediction. Instead of just saying "High Risk", it tells volunteers **why** — e.g., "Key factors: Attendance (-0.5), Monthly Test (-0.3), Assignment (-0.2)".

### Library Used
**SHAP** (SHapley Additive exPlanations) — `shap.TreeExplainer`

### Why SHAP?
- **Theoretically grounded** — based on Shapley values from cooperative game theory, the only method that satisfies local accuracy, missingness, and consistency axioms
- **Tree-optimized** — `TreeExplainer` is specifically designed for tree-based models (like Random Forest), making it fast (polynomial time instead of exponential)
- **Per-feature contribution** — shows exactly how much each feature pushed the prediction toward or away from a risk class
- **Builds trust** — NGO volunteers and teachers can understand and trust AI predictions when they see the reasoning

### How It Works
1. At app startup, a `TreeExplainer` is initialized with the trained Random Forest model:
   ```python
   explainer = shap.TreeExplainer(model)
   ```
2. For each student prediction, SHAP values are computed:
   ```python
   shap_values = explainer.shap_values(input_data)
   ```
3. SHAP returns a list of arrays (one per class). The predicted class's SHAP array is selected.
4. The top 3 contributing features are sorted by absolute SHAP value and displayed:
   ```
   AI predicts High Risk. Key factors: Attendance (-0.5012), Monthly Test (-0.2893), Quiz (-0.1247).
   ```

### Output Format
Each student on the volunteer dashboard gets:
- **AI Reason:** Natural language explanation with top 3 SHAP factors
- **Confidence:** Percentage from `predict_proba`
- **SHAP Values:** Raw dictionary of all 4 feature contributions

**Code location:** `app.py` — inside `predict_student_risk()`, lines ~370-377

---

## 3. Sentiment Analysis on Student Feedback

### What It Does
When a student submits written feedback about a teacher, the system automatically analyzes the emotional tone and labels it as **Positive**, **Negative**, or **Neutral**. This helps principals quickly identify teachers who may need support or recognition.

### Library Used
**TextBlob** (`textblob==0.18.0`), built on top of NLTK (Natural Language Toolkit)

### Why TextBlob?
- **Zero cost** — no API calls, no external dependencies at runtime
- **Works offline** — purely local computation using a built-in lexicon
- **Fast** — dictionary lookup is near-instantaneous, even for batch processing
- **Good enough for short text** — student feedback is typically 1-3 sentences, which lexicon-based approaches handle well
- **No training required** — uses a pre-built sentiment lexicon of ~2,900 words with assigned polarity scores

### How It Works
TextBlob uses a **lexicon-based approach**:

1. **Tokenization:** Breaks feedback text into individual words
2. **Lexicon lookup:** Each word is checked against a built-in sentiment dictionary where words have pre-assigned polarity scores (e.g., "excellent" = +1.0, "terrible" = -1.0)
3. **Modifier handling:** Applies intensifiers ("very good" = stronger positive) and negations ("not good" = flipped polarity)
4. **Averaging:** Computes the mean polarity across all sentiment-bearing words
5. **Output:** Returns `polarity` (-1.0 to +1.0) and `subjectivity` (0.0 to 1.0)

### Classification Thresholds
```
Positive:  polarity > 0.1
Neutral:   -0.1 <= polarity <= 0.1
Negative:  polarity < -0.1
```

### What Gets Stored
| Column | Type | Example |
|--------|------|---------|
| feedback_text | TEXT | "The teacher explains concepts very clearly" |
| sentiment_score | FLOAT | 0.45 |
| sentiment_label | TEXT | "Positive" |

### Known Limitations
- Struggles with sarcasm ("Oh, what a wonderful class" said sarcastically)
- Limited with non-English or code-mixed text (Hindi-English mix)
- Context-unaware (doesn't understand "not bad" perfectly)
- Short text can sometimes be misclassified

**Code location:** `app.py` — lines ~970-982 in the `/student/feedback` POST route

---

## 4. Generative AI Chatbot (EduBot)

### What It Does
A conversational AI assistant available on every dashboard. EduBot answers questions, provides advice, and interprets data — all personalized to the user's role and their actual data from the database.

### Model Used
**Google Gemini 2.5 Flash** via REST API

### Why Gemini 2.5 Flash?
- **Free tier** — generous quota (15 requests/minute) perfect for school-level usage
- **Fast responses** — 1-3 second response times for concise answers
- **Multi-language** — natively supports 20+ Indian languages
- **No library dependency issues** — uses direct REST API calls instead of the `google-generativeai` Python package (which had gRPC timeout issues)

### API Details
| Property | Value |
|----------|-------|
| Endpoint | `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent` |
| Method | POST |
| Auth | API key via query parameter |
| Timeout | 10 seconds |
| Cooldown | 5 minutes on failure |

### Multi-Role Architecture
EduBot serves **6 different user roles**, each with a customized system prompt and real-time contextual data:

| Role | Context Data Provided | Use Case |
|------|----------------------|----------|
| **Homepage** | None (public) | Explain EduDrop features to visitors |
| **Student** | Individual attendance, test scores, assignments, quiz, risk status | Academic counseling and encouragement |
| **Teacher** | Class-wide stats (total students, risk counts, pending leaves, per-student details) | Classroom management, intervention planning |
| **Principal** | School-wide analytics (totals, averages, gender-wise risk, teacher count) | Strategic decision-making, school-wide insights |
| **Volunteer** | At-risk student profiles (up to 15 students with full metrics) | Intervention strategies, sensitive approaches |
| **NGO Admin** | Pending approvals, completed/ongoing intervention counts | Volunteer management, resource allocation |

### How Context Is Built
Each role has a dedicated context builder function that queries Supabase in real-time:
- `_get_student_context()` — fetches individual student's performance record
- `_get_teacher_context()` — fetches all students, recalculates risk scores, counts by category
- `_get_principal_context()` — aggregates school-wide statistics
- `_get_volunteer_context()` — fetches at-risk students and recent interventions
- `_get_ngo_admin_context()` — fetches pending approvals and intervention statistics

### Prompt Structure
```
[System Prompt for Role]
[Language instruction if non-English]
Available data:
[Real-time context from Supabase]

User's message: [user input]
```

### Multi-Language Support
Supports **22 Indian languages** via a language instruction injected into the prompt:
```
IMPORTANT: You MUST respond entirely in Hindi. The user's preferred language is Hindi. Do not use English.
```
Languages: English, Hindi, Bengali, Telugu, Marathi, Tamil, Gujarati, Kannada, Malayalam, Punjabi, Odia, Assamese, Urdu, Sanskrit, Nepali, Sindhi, Kashmiri, Dogri, Maithili, Manipuri, Santali, Konkani

### Error Handling
- **5-minute cooldown** on API failure — prevents hammering a broken API
- **Graceful fallback message:** "Sorry, I'm temporarily unavailable. Please try again in a few minutes."
- **Session validation** — prevents role spoofing (trusts server session, not frontend request)

**Code location:** `app.py` — lines ~1043-1361

---

## 5. AI-Powered Volunteer Suggestions

### What It Does
Generates a personalized, one-liner intervention suggestion for each at-risk student on the volunteer dashboard. The suggestion is stored in the database so it persists across sessions and is only generated once per student (not on every page load).

### Model Used
**Google Gemini 2.5 Flash** (same API as chatbot)

### Why Gemini for Suggestions?
- **Context-aware** — considers gender, academic weaknesses, attendance patterns, and cultural context
- **Practical** — trained on vast data about education, child welfare, and intervention strategies
- **Satisfies ML requirement** — uses a machine learning model (large language model) rather than hardcoded if/else rules
- **Persistent** — generated once and stored in the database, avoiding redundant API calls

### How It Works
1. When the volunteer dashboard loads, for each at-risk student:
2. **Check DB first** — if `student_performance.ai_suggestion` already has a value, use it directly (no API call)
3. **Generate if missing** — if no stored suggestion exists, a prompt is sent to Gemini with the student's profile:
   ```
   Student: [name] | Gender: [gender] | Class: [standard] | Risk: [risk] |
   Attendance: [value] | Test: [value] | Assignment: [value] | Quiz: [value]
   ```
4. The prompt asks for exactly **ONE actionable sentence** (max 15 words)
5. Gemini returns the one-liner, which is:
   - Displayed on the volunteer dashboard under the AI Insight column
   - **Saved to `student_performance.ai_suggestion`** in Supabase so it's not regenerated next time

### Database Storage
| Table | Column | Type | Purpose |
|-------|--------|------|---------|
| `student_performance` | `ai_suggestion` | TEXT | Stores the one-liner suggestion per student |

### Example Output
```
Schedule weekly home visits to improve attendance and build family trust.
```
```
Arrange peer tutoring sessions focused on math and science fundamentals.
```
```
Connect parents with scholarship programs to address financial barriers.
```

### Error Handling
- **8-second timeout** per student (shorter than chatbot to keep page load reasonable)
- If Gemini API fails, suggestion is silently skipped (no error shown to volunteer)
- If DB save fails, suggestion is still displayed for the current session but won't persist
- The feature degrades gracefully — the rest of the dashboard works without suggestions

**Code location:** `app.py` — lines ~590-640

---

## 6. Text-to-Speech (TTS)

### What It Does
Converts EduBot chatbot responses into spoken audio, allowing users to listen to responses. Supports English and 20+ Indian regional languages.

### Dual Implementation

#### Implementation 1: Browser Web Speech API (English)
| Property | Value |
|----------|-------|
| API | `window.speechSynthesis` (W3C Web Speech API) |
| Cost | Free (built into browser) |
| Language | `en-IN` (Indian English) |
| Rate | 0.9 (slightly slower for clarity) |
| Pitch | 1.05 |

**Voice selection priority:**
1. Google UK English Female
2. Google US English
3. Samantha (macOS)
4. Karen
5. Daniel
6. Any available fallback

#### Implementation 2: Google Translate TTS (Regional Languages)
| Property | Value |
|----------|-------|
| API | Google Translate TTS via backend proxy |
| Route | `/api/tts?tl={lang}&q={text}` |
| Cost | Free |
| Char limit | 200 characters per request |
| Format | audio/mpeg stream |

**Smart chunking:** Long text is automatically split at sentence boundaries (`.`) or spaces, then played sequentially as audio chunks.

### Why Dual Implementation?
- **Web Speech API** offers better voice quality for English with zero latency and offline capability
- **Google Translate TTS** is the only free option that supports 20+ Indian languages
- The backend proxy (`/api/tts`) is needed because Google Translate TTS blocks direct browser requests (CORS)

### Language Mapping
Languages without direct TTS support fall back to a related language:
- Kashmiri, Dogri, Maithili, Santali → Hindi TTS
- Manipuri → Bengali TTS
- Konkani → Hindi TTS

**Code location:**
- Frontend: `templates/partials/chatbot.html` — lines ~133-226
- Backend proxy: `app.py` — lines ~2389-2408

---

## 7. Speech-to-Text (STT)

### What It Does
Allows users to speak their messages to EduBot instead of typing. Supports voice input in 22 Indian languages.

### API Used
**W3C Web Speech API** (`window.SpeechRecognition` / `window.webkitSpeechRecognition`)

### Why Browser STT?
- **Free** — no API costs
- **Real-time** — processes speech as it's spoken
- **Multi-language** — supports Indian language STT codes (`hi-IN`, `bn-IN`, `te-IN`, etc.)
- **Best on Chrome** — Google's speech recognition backend is the most accurate

### How It Works
1. User clicks the microphone button in the chatbot
2. Browser requests microphone access
3. `SpeechRecognition` starts listening with the user's selected language code
4. When speech is detected, the transcript fills the input box
5. Message is automatically sent to EduBot via `sendChat()`

### Configuration
| Setting | Value |
|---------|-------|
| interimResults | false (only final transcript) |
| maxAlternatives | 1 (single best result) |
| Language | Dynamic based on `edudrop_lang` cookie |

### STT Language Codes
Each language maps to a region-specific recognition code:
```
English → en-IN    Hindi → hi-IN      Bengali → bn-IN
Telugu → te-IN     Marathi → mr-IN    Tamil → ta-IN
Gujarati → gu-IN   Kannada → kn-IN    Malayalam → ml-IN
Punjabi → pa-IN    Odia → or-IN       Nepali → ne-NP
... (22 languages total)
```

### UI Behavior
- Mic button turns **red with pulse animation** while listening
- Icon changes from microphone to mute icon during recording
- Automatically stops and resets after speech ends
- Shows alert on error (unless user manually aborted)

**Code location:** `templates/partials/chatbot.html` — lines ~228-274

---

## 8. Risk Score Calculation Engine

### What It Does
Computes a deterministic risk score (0-100) for each student based on their academic metrics. This is used by the teacher and principal dashboards to classify students and power the chatbot context.

### Type
**Rule-based heuristic** (not ML) — deterministic formula that consistently maps metrics to risk scores.

### Why Rule-Based?
- **Instant calculation** — no model loading or inference needed
- **Transparent** — teachers and principals can understand exactly why a score was assigned
- **Consistent** — same inputs always produce the same score (important for dashboards)
- **Complementary to ML** — the Random Forest model (Section 1) handles nuanced predictions on the volunteer side, while this formula handles dashboard display

### Formula
```
risk_score = 0

If monthly_test_score < 35:   risk_score += 40
If attendance < 60:           risk_score += 30
If assignment is poor*:       risk_score += 15
If quiz is poor*:             risk_score += 15

Maximum possible: 100
```

*"Poor" is defined as: score text in `["not completed", "incomplete", "pending", "poor"]` OR numeric score < 50

### Risk Classification
| Score Range | Status |
|------------|--------|
| >= 60 | **At Risk** |
| < 60 | **Safe** |

### Dropout Probability Mapping
An additional heuristic maps risk scores to dropout probability percentages:
| Risk Score | Dropout Probability |
|-----------|-------------------|
| >= 80 | 85% |
| >= 60 | 60% |
| >= 40 | 35% |
| < 40 | 10% |

This probability is used for SMS alerts and intervention prioritization.

**Code location:** `app.py` — `_recalc_risk()` function at lines ~1255-1279, `calculate_dropout_probability()` at lines ~49-58

---

## Summary

| # | Feature | Technology | Type | Cost | Offline? |
|---|---------|-----------|------|------|----------|
| 1 | Risk Prediction | scikit-learn RandomForest | ML Classification | Free | Yes |
| 2 | SHAP Explainability | SHAP TreeExplainer | ML Interpretability | Free | Yes |
| 3 | Sentiment Analysis | TextBlob (NLTK) | NLP Lexicon-based | Free | Yes |
| 4 | Chatbot (EduBot) | Gemini 2.5 Flash | Generative AI | Free tier | No |
| 5 | Volunteer Suggestions | Gemini 2.5 Flash | Generative AI | Free tier | No |
| 6 | Text-to-Speech | Web Speech API + Google TTS | Browser + API | Free | Partial |
| 7 | Speech-to-Text | Web Speech API | Browser API | Free | No |
| 8 | Risk Score Engine | Custom formula | Rule-based | Free | Yes |

### Key Design Principles
- **All features are free** — no paid API subscriptions required
- **Graceful degradation** — every AI feature has a fallback if unavailable
- **Multi-language** — 22 Indian languages supported across chatbot, TTS, and STT
- **Interpretable AI** — SHAP values explain predictions; rule-based scores are transparent
- **Privacy-first** — sentiment analysis runs locally; no student data sent to external services except Gemini (for chatbot context only)

### Dependencies
```
scikit-learn==1.4.0     # Random Forest model
joblib==1.3.2           # Model serialization
shap==0.44.1            # SHAP explainability
numpy==1.26.4           # Numerical operations
pandas==2.2.0           # Data manipulation
textblob==0.18.0        # Sentiment analysis
```
