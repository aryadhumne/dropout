# EduDrop v2 — AI Feature Updates

## Overview

Two AI features were added to make EduDrop stand out as a hackathon project. Each feature uses a different AI technique — **Natural Language Processing (NLP)** and **Generative AI** — demonstrating breadth in AI knowledge.

---

## 1. Sentiment Analysis on Student Feedback

### What It Does
When a student submits feedback about a teacher, the system automatically analyzes the sentiment of the feedback text and labels it as **Positive**, **Negative**, or **Neutral**. The principal can see these sentiment badges in a color-coded column on their dashboard's feedback table:
- Green badge = Positive feedback
- Red badge = Negative feedback
- Yellow badge = Neutral feedback

### How It Works
1. **Library**: TextBlob — a simple NLP library built on NLTK
2. **Process**: When the student submits feedback via `/student/feedback`, `TextBlob(feedback_text).sentiment.polarity` returns a score from -1.0 (very negative) to +1.0 (very positive)
3. **Thresholds**: Score > 0.1 = Positive, Score < -0.1 = Negative, else = Neutral
4. **Storage**: Both `sentiment_score` (float) and `sentiment_label` (text) are stored in the `student_feedback` table

### Files Changed
| File | Change |
|---|---|
| `app.py` | `/student/feedback` route runs TextBlob analysis before inserting into database |
| `templates/dashboard_principal.html` | New "Sentiment" column in feedback table with color-coded badges |

### Database Change Required
```sql
ALTER TABLE student_feedback ADD COLUMN sentiment_score FLOAT;
ALTER TABLE student_feedback ADD COLUMN sentiment_label TEXT;
```

### Why TextBlob Over Alternatives

| Approach | Pros | Cons | Why Not |
|---|---|---|---|
| **TextBlob (Chosen)** | Zero cost, no API key, fast, lightweight, works offline | Less accurate on complex/sarcastic text | Perfect for simple student feedback; no API dependency |
| **VADER (NLTK)** | Good for social media text, handles emojis | Designed for social media, not formal feedback; similar accuracy to TextBlob | TextBlob is simpler to integrate and sufficient for our use case |
| **Google Cloud NLP / AWS Comprehend** | Very accurate, handles nuance well | Costs money, requires API keys, adds latency, overkill for short feedback | Free tier is limited; adds complexity and a paid dependency |
| **Fine-tuned BERT / Transformer** | State-of-the-art accuracy | Requires GPU, large model size (~400MB), slow inference, complex setup | Way overkill for a hackathon; deployment would be difficult |

### Justification
TextBlob is the right tool for the job — it's **free, fast, and requires no API key or internet connection**. Student feedback is typically short and straightforward (e.g., "The teacher explains very well" or "I don't understand anything in class"), making TextBlob's simple polarity analysis more than adequate. It gives the principal an at-a-glance view of overall feedback tone without reading every single comment. For a hackathon, this is a quick win that adds genuine NLP capability.

---

## 2. AI Chatbot (EduBot) — Gemini-Powered

### What It Does
A floating chat widget appears on the **student dashboard** (bottom-right corner). Students can ask EduBot anything about:
- Their academic performance ("How am I doing?")
- Study tips ("How can I improve my quiz scores?")
- Motivation and encouragement ("I'm stressed about exams")

EduBot has access to the student's actual academic data (attendance, test scores, risk status) and gives **personalized responses**.

### How It Works
1. **Frontend**: Floating gradient button → opens a chat panel with message history, typing indicator, and input field
2. **Backend Route**: `POST /api/chat` receives the student's message
3. **Context Building**: Fetches the student's data from `student_performance` table (attendance, scores, risk status)
4. **Gemini API**: Sends a prompt to `gemini-2.0-flash` with the student's data as context + their question
5. **Prompt Engineering**: System prompt instructs Gemini to act as "EduBot, a friendly AI academic counselor" — keep responses concise (2-3 sentences), be supportive, suggest specific improvements based on data
6. **Response**: Displayed in the chat panel with smooth styling

### Files Changed
| File | Change |
|---|---|
| `app.py` | New `POST /api/chat` route — fetches student context, calls Gemini, returns JSON response |
| `templates/student/dashboard.html` | Floating chat widget UI with toggle, message history, input, and JS fetch logic |

### Why Gemini Over Alternatives

| Approach | Pros | Cons | Why Not |
|---|---|---|---|
| **Gemini 2.0 Flash (Chosen)** | Free tier (15 RPM), fast responses, good quality, Google-backed | Rate limited on free tier (15 req/min) | Best free option; fast enough for a student chatbot |
| **OpenAI GPT-4o-mini** | Very high quality, reliable | Costs money ($0.15/1M input tokens), requires credit card | Not free; adds a paid dependency |
| **Llama 3 (Self-hosted)** | Fully free, no rate limits, private | Requires GPU server, complex setup, slow without GPU | Can't deploy easily for a hackathon demo |
| **Rule-based Chatbot (no AI)** | No API needed, instant, predictable | Not real AI, limited responses, can't handle open-ended questions | Judges will immediately see it's not AI; defeats the purpose |

### Justification
Gemini 2.0 Flash on the free tier is the **best choice for a hackathon** — it's genuinely intelligent, responds quickly, and costs nothing. The chatbot is personalized because it receives the student's actual academic data as context, so responses like "Your attendance is at 65% which is below the 75% threshold — try to attend at least 4 days a week" feel genuinely useful. This is the **biggest wow factor** for judges because it's interactive, personalized, and uses cutting-edge generative AI.

---

## Tech Stack Summary

| AI Feature | Library/API | Cost | Where It Runs |
|---|---|---|---|
| Sentiment Analysis | TextBlob (NLTK) | Free | Student Feedback → Principal Dashboard |
| AI Chatbot (EduBot) | Google Gemini 2.0 Flash | Free (15 RPM) | Student Dashboard |

---

## What Makes This Stand Out for Judges

1. **Two different AI techniques** — NLP Sentiment + Generative AI — shows breadth
2. **Personalized responses** — Chatbot uses actual student data, not generic answers
3. **Everything is free** — No paid APIs, deployable without cost
4. **Practical impact** — Each feature serves a real educational purpose:
   - Sentiment helps principals spot teacher issues early
   - Chatbot gives students 24/7 academic support
