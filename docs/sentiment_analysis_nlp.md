# Sentiment Analysis & NLP — How It Works in EduDrop

---

## What is NLP (Natural Language Processing)?

NLP is a branch of Artificial Intelligence that deals with the interaction between computers and human language. It enables machines to **read, understand, and derive meaning** from text or speech.

### Real-World Examples of NLP
| Application | What It Does |
|---|---|
| Google Translate | Translates text from one language to another |
| Siri / Alexa | Understands voice commands and responds |
| Gmail Smart Reply | Suggests short replies to emails |
| Spam Filters | Detects spam emails by analyzing text patterns |
| Autocorrect / Autocomplete | Predicts and corrects words as you type |

### Key NLP Tasks
1. **Tokenization** — Breaking text into individual words or sentences
   - Input: `"The teacher is great"` → Output: `["The", "teacher", "is", "great"]`
2. **Part-of-Speech Tagging** — Identifying nouns, verbs, adjectives, etc.
   - `"great"` → Adjective
3. **Named Entity Recognition (NER)** — Identifying names, places, dates
   - `"Mr. Sharma teaches in Mumbai"` → Person: Mr. Sharma, Location: Mumbai
4. **Sentiment Analysis** — Determining if text is positive, negative, or neutral
5. **Text Classification** — Categorizing text into predefined labels (e.g., spam/not spam)
6. **Text Summarization** — Condensing long text into a shorter version

---

## What is Sentiment Analysis?

Sentiment Analysis is a specific NLP technique that determines the **emotional tone** behind a piece of text. It answers the question: *Is this text positive, negative, or neutral?*

### How Sentiment Analysis Works (General Concept)

```
Input Text  →  NLP Processing  →  Polarity Score  →  Label
"I love this class"  →  TextBlob  →  +0.50  →  Positive
"The class is boring"  →  TextBlob  →  -0.40  →  Negative
"The class started at 9am"  →  TextBlob  →  0.00  →  Neutral
```

The system assigns a **polarity score** ranging from:
- **-1.0** = Very Negative
- **0.0** = Completely Neutral
- **+1.0** = Very Positive

---

## How Sentiment Analysis Works in EduDrop

### The Flow

```
Student submits feedback (text)
        ↓
Flask route: POST /student/feedback
        ↓
TextBlob analyzes the text
        ↓
Polarity score calculated (-1.0 to +1.0)
        ↓
Label assigned: Positive / Negative / Neutral
        ↓
Score + Label stored in Supabase (student_feedback table)
        ↓
Principal sees sentiment badges on dashboard
```

### Step-by-Step Code Walkthrough

#### Step 1: Student Submits Feedback
The student fills out a feedback form on their dashboard and clicks submit. The form sends a POST request to `/student/feedback`.

#### Step 2: TextBlob Analyzes the Text
```python
from textblob import TextBlob

feedback_text = "The teacher explains concepts very clearly and is always helpful"

sentiment = TextBlob(feedback_text).sentiment
# sentiment.polarity = 0.55 (positive)
# sentiment.subjectivity = 0.65 (subjective)
```

**What TextBlob does internally:**
1. Tokenizes the text into words
2. Looks up each word in its built-in sentiment lexicon (dictionary of ~2,900 words with pre-assigned polarity scores)
3. Words like "clearly" = +0.4, "helpful" = +0.5, "always" acts as an intensifier
4. Averages the scores of all sentiment-bearing words
5. Returns a final polarity score

#### Step 3: Thresholds Applied
```python
sentiment_score = round(sentiment.polarity, 2)  # e.g., 0.55

if sentiment_score > 0.1:
    sentiment_label = "Positive"    # Score > 0.1
elif sentiment_score < -0.1:
    sentiment_label = "Negative"    # Score < -0.1
else:
    sentiment_label = "Neutral"     # Score between -0.1 and 0.1
```

**Why 0.1 as threshold (not 0.0)?**
Many factual/neutral statements score slightly above or below zero (e.g., "The class is in room 5" might score +0.05). The 0.1 buffer prevents these from being mislabeled.

#### Step 4: Stored in Database
```python
supabase.table("student_feedback").insert({
    "student_id": student_id,
    "student_name": student_name,
    "feedback_text": feedback_text,
    "teacher_name": teacher_name,
    "sentiment_score": 0.55,        # Float
    "sentiment_label": "Positive"   # Text
}).execute()
```

#### Step 5: Principal Sees Results
On the principal dashboard, each feedback row shows a color-coded badge:
- **Green** badge → Positive sentiment
- **Red** badge → Negative sentiment
- **Yellow** badge → Neutral sentiment

This lets the principal quickly scan feedback tone without reading every message.

---

## Examples with Actual Scores

| Student Feedback | Polarity Score | Label |
|---|---|---|
| "The teacher is amazing and very supportive" | +0.75 | Positive |
| "I really enjoy the math classes" | +0.35 | Positive |
| "Classes are okay" | +0.10 | Neutral |
| "The teacher did not explain the topic" | -0.05 | Neutral |
| "I don't understand anything in class" | -0.20 | Negative |
| "The teacher is rude and unhelpful" | -0.65 | Negative |
| "The class starts at 10am on Monday" | 0.00 | Neutral |

---

## What is TextBlob?

TextBlob is a Python library for processing textual data. It is built on top of **NLTK (Natural Language Toolkit)** and provides a simple API for common NLP tasks.

### Installation
```bash
pip install textblob
```

### Key Features
```python
from textblob import TextBlob

text = TextBlob("The teacher explains very well and is always kind")

# 1. Sentiment Analysis
text.sentiment.polarity      # 0.65 (positive)
text.sentiment.subjectivity  # 0.70 (subjective, not factual)

# 2. Tokenization
text.words    # ['The', 'teacher', 'explains', 'very', 'well', 'and', 'is', 'always', 'kind']
text.sentences  # [Sentence("The teacher explains very well and is always kind")]

# 3. Part-of-Speech Tagging
text.tags   # [('The', 'DT'), ('teacher', 'NN'), ('explains', 'VBZ'), ('very', 'RB'), ...]

# 4. Noun Phrase Extraction
text.noun_phrases  # ['teacher']

# 5. Word Counts
text.word_counts['teacher']  # 1
```

### How TextBlob Calculates Sentiment (Under the Hood)

TextBlob uses a **pattern-based approach**:

1. **Lexicon Lookup**: Each word has a pre-defined polarity in a dictionary
   - "good" → +0.7
   - "bad" → -0.7
   - "excellent" → +0.8
   - "terrible" → -1.0
   - "the", "is", "a" → 0.0 (no sentiment)

2. **Modifiers**: Certain words modify the score of the next word
   - "very good" → 0.7 × 1.3 = 0.91 (intensifier)
   - "not good" → 0.7 × -1 = -0.7 (negation)

3. **Averaging**: Final score = average of all word-level sentiment scores in the text

---

## Polarity vs Subjectivity

TextBlob returns two values:

| Metric | Range | Meaning |
|---|---|---|
| **Polarity** | -1.0 to +1.0 | How positive or negative the text is |
| **Subjectivity** | 0.0 to 1.0 | How opinionated vs factual the text is |

Examples:
- "The exam was very difficult" → Polarity: -0.5, Subjectivity: 0.75 (opinion)
- "The exam was on Monday" → Polarity: 0.0, Subjectivity: 0.0 (fact)
- "I love this school" → Polarity: 0.5, Subjectivity: 0.6 (opinion)

In EduDrop, we only use **polarity** (not subjectivity) because we care about whether the feedback is positive or negative.

---

## Why Sentiment Analysis Matters in EduDrop

### Problem It Solves
A principal managing hundreds of students receives many feedback submissions. Reading every single feedback message is time-consuming. Sentiment analysis provides an **instant overview**:
- Are students generally happy? (mostly green badges)
- Is there a problem with a specific teacher? (many red badges for one teacher)
- Are students neutral/disengaged? (many yellow badges)

### Practical Use Cases
1. **Early Warning**: If multiple students give negative feedback about the same teacher, the principal can investigate early
2. **Teacher Performance**: Track sentiment trends over time — is teacher feedback improving or declining?
3. **Student Wellbeing**: Negative sentiment may indicate students are struggling or unhappy
4. **Data-Driven Decisions**: Instead of subjective judgment, use actual sentiment data to make decisions

---

## Database Schema

### student_feedback Table
| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key (auto-generated) |
| student_id | UUID | Foreign key to students table |
| student_name | TEXT | Name of the student |
| standard | INT | Class/standard of the student |
| division | TEXT | Division (A, B, C, etc.) |
| feedback_text | TEXT | The actual feedback message |
| teacher_name | TEXT | Teacher the feedback is about |
| sentiment_score | FLOAT | Polarity score (-1.0 to +1.0) |
| sentiment_label | TEXT | "Positive", "Negative", or "Neutral" |
| created_at | TIMESTAMPTZ | Timestamp (auto-generated) |

---

## Limitations of TextBlob Sentiment Analysis

| Limitation | Example |
|---|---|
| **Sarcasm** | "Oh great, another boring class" → TextBlob reads "great" as positive |
| **Context** | "The teacher is not bad" → Double negation may confuse it |
| **Hindi/Regional text** | TextBlob only works well with English text |
| **Short text** | "ok" or "fine" may not have enough signal for accurate analysis |
| **Domain-specific words** | "dropout" has negative general sentiment but is neutral in our context |

### Why These Limitations Are Acceptable
Student feedback in EduDrop is typically:
- Written in English (the app's primary language)
- Short and straightforward ("The teacher explains well", "I need more help")
- Rarely sarcastic (students writing to their principal)
- Sufficient for a quick positive/negative/neutral classification

For a production system with thousands of feedback entries in multiple languages, a more advanced model (like a fine-tuned BERT) would be better. For EduDrop's hackathon scope, TextBlob is the right balance of simplicity and effectiveness.

---

## Summary

| Concept | Description |
|---|---|
| **NLP** | AI branch that enables computers to understand human language |
| **Sentiment Analysis** | NLP technique to detect positive/negative/neutral tone in text |
| **TextBlob** | Python library we use for sentiment analysis (built on NLTK) |
| **Polarity Score** | Numeric score from -1.0 (negative) to +1.0 (positive) |
| **How we use it** | Analyze student feedback → store score + label → show on principal dashboard |
| **Thresholds** | > 0.1 = Positive, < -0.1 = Negative, else Neutral |
