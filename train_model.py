import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
import joblib

np.random.seed(42)
n = 500

# Generate realistic synthetic student data
# Features: attendance (0-100), monthly_test_score (0-100), assignment (0-100), quiz (0-100)
attendance = np.random.normal(70, 18, n).clip(10, 100)
monthly_test = np.random.normal(55, 22, n).clip(0, 100)
assignment = np.random.normal(60, 25, n).clip(0, 100)
quiz = np.random.normal(58, 20, n).clip(0, 100)

# Risk label based on realistic rules with some noise
risk_score = (
    (100 - attendance) * 0.35 +
    (100 - monthly_test) * 0.25 +
    (100 - assignment) * 0.20 +
    (100 - quiz) * 0.20
)
noise = np.random.normal(0, 5, n)
risk_score = (risk_score + noise).clip(0, 100)

# 0 = Low Risk, 1 = Medium Risk, 2 = High Risk
labels = np.where(risk_score >= 60, 2, np.where(risk_score >= 35, 1, 0))

df = pd.DataFrame({
    "attendance": np.round(attendance, 1),
    "monthly_test": np.round(monthly_test, 1),
    "assignment": np.round(assignment, 1),
    "quiz": np.round(quiz, 1),
    "risk": labels
})

X = df[["attendance", "monthly_test", "assignment", "quiz"]]
y = df["risk"]

# Train Random Forest with tuned hyperparameters
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=8,
    min_samples_split=10,
    random_state=42
)
model.fit(X, y)

# Cross-validation accuracy
scores = cross_val_score(model, X, y, cv=5, scoring='accuracy')
print(f"Cross-validation accuracy: {scores.mean():.2f} (+/- {scores.std():.2f})")
print(f"Feature importances: {dict(zip(X.columns, model.feature_importances_.round(3)))}")

# Save model + features
joblib.dump(model, "risk_model.pkl")
joblib.dump(X.columns.tolist(), "model_features.pkl")

print("Model saved: risk_model.pkl, model_features.pkl")
