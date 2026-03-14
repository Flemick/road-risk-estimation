import joblib
import pandas as pd
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "best_model.pkl")
model = joblib.load(MODEL_PATH)

def predict_risk(feature_dict):
    """
    feature_dict: dictionary containing road conditions
    returns probability (0–1)
    """

    # Convert to DataFrame (VERY IMPORTANT)
    df = pd.DataFrame([feature_dict])

    # Predict probability
    probability = model.predict_proba(df)[0][1]

    return float(probability)