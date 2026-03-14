print("Starting Flask app...")
from flask import Flask, request, jsonify, render_template
import os
import joblib


# --- New ML pipeline imports ---
from ml.predict_segment import predict_risk
from utils.feature_extractor import build_feature_dict
from utils.risk_mapping import risk_category, risk_score

app = Flask(__name__)

# ---------------- FACTOR SCORING ----------------
def calculate_route_factors(all_segment_features):
    """
    Computes average impact scores for various risk factors
    across all segments of the route.
    """
    if not all_segment_features:
        return []

    # Initialize aggregators
    sums = {
        "Road Curvature": 0,
        "Traffic Density": 0,
        "Weather Conditions": 0,
        "Lighting & Visibility": 0,
        "Road Condition": 0
    }
    # Track which segments are 'risky' for each factor
    risky_segments = {
        "Road Curvature": [],
        "Traffic Density": [],
        "Weather Conditions": [],
        "Lighting & Visibility": [],
        "Road Condition": []
    }
    
    # Track worst severity to define the reason
    max_scores = {
        "Road Curvature": 0,
        "Traffic Density": 0,
        "Weather Conditions": 0,
        "Lighting & Visibility": 0,
        "Road Condition": 0
    }
    
    count = len(all_segment_features)

    for i, feat in enumerate(all_segment_features):
        # 1. Curvature
        c = feat.get("road_curvature", "straight")
        curv_score = 90 if c == "sharp" else 45 if c == "moderate" else 10
        sums["Road Curvature"] += curv_score
        max_scores["Road Curvature"] = max(max_scores["Road Curvature"], curv_score)
        if curv_score > 40: risky_segments["Road Curvature"].append(i)

        # 2. Traffic
        t = feat.get("traffic_density", "low")
        traf_score = 85 if t == "high" else 50 if t == "medium" else 15
        sums["Traffic Density"] += traf_score
        max_scores["Traffic Density"] = max(max_scores["Traffic Density"], traf_score)
        if traf_score > 40: risky_segments["Traffic Density"].append(i)

        # 3. Weather
        w = feat.get("weather", "clear")
        weat_score = 95 if w == "heavy_rain" else 70 if w == "rain" else 40 if w == "fog" else 10
        sums["Weather Conditions"] += weat_score
        max_scores["Weather Conditions"] = max(max_scores["Weather Conditions"], weat_score)
        if weat_score > 30: risky_segments["Weather Conditions"].append(i)

        # 4. Lighting/Visibility
        l = feat.get("lighting", "good")
        v = feat.get("visibility", "good")
        lv_score = 0
        if l == "poor": lv_score += 40
        if v == "poor": lv_score += 40
        final_lv = max(10, lv_score)
        sums["Lighting & Visibility"] += final_lv
        max_scores["Lighting & Visibility"] = max(max_scores["Lighting & Visibility"], final_lv)
        if final_lv > 30: risky_segments["Lighting & Visibility"].append(i)

        # 5. Road Condition
        rc = feat.get("road_condition", "dry")
        cond_score = 80 if rc == "damaged" else 60 if rc == "wet" else 10
        sums["Road Condition"] += cond_score
        max_scores["Road Condition"] = max(max_scores["Road Condition"], cond_score)
        if cond_score > 40: risky_segments["Road Condition"].append(i)

    def get_context(factor, score):
        if factor == "Road Curvature":
            if score >= 90: return "Sharp curves detected.", "Reduce speed significantly before entering bends. Avoid overtaking."
            if score >= 45: return "Moderate curves present.", "Maintain a steady speed and stay alert."
            return "Mostly straight roads.", "Standard driving precautions apply."
        if factor == "Traffic Density":
            if score >= 85: return "High traffic density.", "Expect delays. Maintain safe following distance."
            if score >= 50: return "Moderate traffic.", "Stay alert for sudden braking."
            return "Light traffic.", "Standard driving precautions apply."
        if factor == "Weather Conditions":
            if score >= 95: return "Heavy rain detected.", "Turn on headlights, reduce speed, and beware of hydroplaning."
            if score >= 70: return "Rain on route.", "Wipers and headlights on. Increase stopping distance."
            if score >= 40: return "Foggy conditions.", "Use fog lights or low beams. Reduce speed significantly."
            return "Clear weather.", "Standard driving precautions apply."
        if factor == "Lighting & Visibility":
            if score >= 30: return "Poor lighting or visibility.", "Use high beams where legal and safe. Stay extra vigilant."
            return "Good visibility.", "Standard driving precautions apply."
        if factor == "Road Condition":
            if score >= 80: return "Damaged roads (potholes/uneven).", "Drive slowly to avoid vehicle damage and maintain control."
            if score >= 60: return "Wet slippery roads.", "Avoid sudden braking or sharp turns."
            return "Good road conditions.", "Standard driving precautions apply."

    # Average and Format
    results = []
    for name, total in sums.items():
        avg = round(total / count)
        color = "red" if avg > 70 else "orange" if avg > 40 else "green"
        reason, tip = get_context(name, max_scores[name])
        results.append({
            "name": name,
            "score": avg,
            "color": color,
            "riskySegments": risky_segments[name],
            "reason": reason,
            "tip": tip
        })

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


# ---------------- LOAD MODEL ----------------
MODELS_DIR = os.path.join("backend", "ml", "models")

try:
    model = joblib.load(os.path.join(MODELS_DIR, "best_model.pkl"))
    print("Best trained ML model loaded successfully.")
except Exception as e:
    print("Model loading failed:", e)
    model = None


# ---------------- HOME PAGE ----------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------- ROUTE ANALYSIS ----------------
@app.route("/analyze_route", methods=["POST"])
def analyze_route():

    if model is None:
        return jsonify({"error": "Model not loaded"}), 500

    data = request.json

    if not data or "segments" not in data:
        return jsonify({"error": "Invalid route data"}), 400

    segments = data["segments"]
    segment_results = []
    segment_risks = []
    all_features = []

    for idx, seg in enumerate(segments):

        lat = seg.get("lat")
        lon = seg.get("lon")

        if lat is None or lon is None:
            continue

        # For curvature estimation we need next point
        if idx + 1 < len(segments):
            next_seg = segments[idx + 1]
            lat2 = next_seg.get("lat", lat)
            lon2 = next_seg.get("lon", lon)
        else:
            lat2, lon2 = lat, lon

        try:
            # ---- FEATURE EXTRACTION ----
            feature_dict = build_feature_dict(lat, lon, lat2, lon2)

            # ---- ML PREDICTION ----
            probability = predict_risk(feature_dict)

            # ---- RISK CATEGORY ----
            category = risk_category(probability)

            segment_results.append({
                "lat": lat,
                "lon": lon,
                "riskLevel": category,
                "riskProbability": probability
            })

            segment_risks.append(probability)
            all_features.append(feature_dict)

        except Exception as e:
            print("Segment prediction error:", e)

            # Fallback safe value
            segment_results.append({
                "lat": lat,
                "lon": lon,
                "riskLevel": "Low",
                "riskProbability": 0.1
            })
            segment_risks.append(0.1)

    if len(segment_risks) == 0:
        return jsonify({"error": "No valid segments"}), 400

    # ---------------- FINAL ROUTE RISK ----------------
    avg_risk = sum(segment_risks) / len(segment_risks)
    final_category = risk_category(avg_risk)

    # ---------------- CALCULATE FACTORS ----------------
    factors = calculate_route_factors(all_features)

    response = {
        "segments": segment_results,
        "riskLevel": final_category,
        "riskScore": risk_score(avg_risk),
        "riskColor": "red" if final_category=="High"
                 else "orange" if final_category=="Medium"
                 else "green",
         "warning": f"Predicted {final_category} risk conditions along this route.",
         "factors": factors
    }

    return jsonify(response)


# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    app.run(debug=True)
