import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

# Sample data
data = {
    "attendance": [95, 40, 85, 30, 75, 20],
    "marks": [88, 35, 72, 25, 60, 15],
    "dropout": [0, 1, 0, 1, 0, 1]
}

df = pd.DataFrame(data)

X = df[["attendance", "marks"]]
y = df["dropout"]

# Use RandomForest (Tree Model)
model = RandomForestClassifier()
model.fit(X, y)

# Save model + features
joblib.dump(model, "risk_model.pkl")
joblib.dump(X.columns.tolist(), "model_features.pkl")

print("✅ RandomForest Model Saved Successfully!")