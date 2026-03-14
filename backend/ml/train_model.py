import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, recall_score, roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
import joblib
import os

# Load dataset
df = pd.read_csv("backend/ml/data/synthetic_road_risk_dataset.csv")

X = df.drop("accident_occured", axis=1)
y = df["accident_occured"]

categorical_cols = X.select_dtypes(include="object").columns

preprocessor = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols)
    ],
    remainder="passthrough"
)

models = {
    "Logistic Regression": LogisticRegression(max_iter=1000, class_weight="balanced"),
    "Decision Tree": DecisionTreeClassifier(max_depth=10, class_weight="balanced"),
    "Random Forest": RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        min_samples_leaf=8,
        class_weight="balanced_subsample",
        random_state=42
    )
}

results = {}

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

best_auc = 0
best_model = None

for name, model in models.items():
    pipe = Pipeline([
        ("prep", preprocessor),
        ("model", model)
    ])

    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)
    y_prob = pipe.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)

    results[name] = (acc, rec, auc)

    print(f"\n{name}")
    print("Accuracy:", acc)
    print("Recall:", rec)
    print("ROC-AUC:", auc)

    if auc > best_auc:
        best_auc = auc
        best_model = pipe

# Save best model
os.makedirs("backend/ml/models", exist_ok=True)
joblib.dump(best_model, "backend/ml/models/best_model.pkl")

# Plot comparison graph
names = list(results.keys())
accuracy = [results[m][0] for m in names]
recall = [results[m][1] for m in names]
auc = [results[m][2] for m in names]

plt.figure(figsize=(10,6))
plt.bar(names, accuracy, alpha=0.6, label="Accuracy")
plt.bar(names, recall, alpha=0.6, label="Recall")
plt.bar(names, auc, alpha=0.6, label="ROC-AUC")
plt.legend()
plt.xticks(rotation=20)
plt.title("Model Comparison")
plt.tight_layout()
plt.savefig("backend/ml/models/model_comparison.png")
plt.show()

print("\nBest model saved as best_model.pkl")