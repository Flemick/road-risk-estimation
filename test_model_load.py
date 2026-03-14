import joblib
import os
import sys

MODELS_DIR = os.path.join("backend", "ml", "models")
model_path = os.path.join(MODELS_DIR, "best_model.pkl")

print(f"Checking {model_path}...")
if os.path.exists(model_path):
    print("File exists.")
else:
    print("File does NOT exist.")
    sys.exit(1)

try:
    print("Loading model...")
    model = joblib.load(model_path)
    print("Model loaded successfully!")
    print(f"Model type: {type(model)}")
except Exception as e:
    print(f"Failed to load model: {e}")
