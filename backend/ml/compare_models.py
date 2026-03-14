import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, ConfusionMatrixDisplay

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

# ---------------- LOAD DATA ----------------
import os

# get absolute path to dataset
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
data_path = os.path.join(BASE_DIR, "data", "accident_risk_3class.csv")

data = pd.read_csv(data_path)

# target column
target_column = "risk_level"

leak_columns = [
    "total_accidents",
    "fatal_accidents",
    "injury_accidents",
    "severity_index",
    "overall_risk_score",
    "region_name"
]



X = data.drop(columns=[target_column] + leak_columns)
y = data[target_column]

# encode categorical columns
X = pd.get_dummies(X)

# encode labels (Low, Medium, High → numbers)
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

# split
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.25, random_state=42
)

# ---------------- MODELS ----------------
models = {
    "Logistic Regression": LogisticRegression(max_iter=2000),
    "Decision Tree": DecisionTreeClassifier(random_state=42),
    "Random Forest": RandomForestClassifier(n_estimators=200, random_state=42)
}

results = {}

# ---------------- TRAIN & EVALUATE ----------------
for name, model in models.items():
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    acc = accuracy_score(y_test, predictions)
    results[name] = acc

    print(f"\n{name} Accuracy: {acc:.4f}")
    print(classification_report(y_test, predictions, target_names=label_encoder.classes_))

    # Save confusion matrix only for Random Forest
    if name == "Random Forest":
        ConfusionMatrixDisplay.from_estimator(model, X_test, y_test,
                                              display_labels=label_encoder.classes_)
        plt.title("Random Forest Confusion Matrix")
        plt.savefig("confusion_matrix_rf.png")
        plt.close()

# ---------------- ACCURACY GRAPH ----------------
plt.bar(results.keys(), results.values())
plt.ylabel("Accuracy")
plt.title("Algorithm Accuracy Comparison")
plt.xticks(rotation=20)
plt.tight_layout()
plt.savefig("accuracy_comparison.png")
plt.close()

print("\nGraphs saved as:")
print(" - accuracy_comparison.png")
print(" - confusion_matrix_rf.png")