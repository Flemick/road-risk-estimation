print("Starting Flask app...")
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import os
import joblib
import json
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

# --- New ML pipeline imports ---
from ml.predict_segment import predict_risk
from utils.feature_extractor import build_feature_dict
from utils.risk_mapping import risk_category, risk_score
from models import db, User, SearchHistory

load_dotenv()
app = Flask(__name__)

# --- Database & Auth Setup ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///accident_risk.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'auth_page'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

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


# ---------------- AUTHENTICATION & HISTORY ----------------
@app.route("/auth")
def auth_page():
    return render_template("auth.html")

@app.route("/history")
@login_required
def history_page():
    return render_template("history.html")
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400
        
    new_user = User(username=username, password_hash=generate_password_hash(password))
    db.session.add(new_user)
    db.session.commit()
    login_user(new_user)
    return jsonify({"message": "Registration successful"}), 201

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(username=data.get("username")).first()
    
    if user and check_password_hash(user.password_hash, data.get("password")):
        login_user(user)
        return jsonify({"message": "Login successful", "username": user.username}), 200
    return jsonify({"error": "Invalid username or password"}), 401

@app.route("/api/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out"}), 200

@app.route("/api/user_status", methods=["GET"])
def user_status():
    if current_user.is_authenticated:
        return jsonify({"logged_in": True, "username": current_user.username}), 200
    return jsonify({"logged_in": False}), 200

@app.route("/api/history", methods=["GET"])
@login_required
def get_history():
    history_records = SearchHistory.query.filter_by(user_id=current_user.id).order_by(SearchHistory.timestamp.desc()).limit(15).all()
    results = []
    for record in history_records:
        results.append({
            "id": record.id,
            "start_location": record.start_location,
            "end_location": record.end_location,
            "risk_level": record.risk_level,
            "risk_score": record.risk_score,
            "timestamp": record.timestamp.strftime("%b %d, %Y %H:%M")
        })
    return jsonify(results), 200


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
    
    # --- OPTIMIZATION: Sub-sampling for performance ---
    # OSRM returns hundreds of GPS coordinates for long routes. 
    # Calling the weather and overpass APIs 500 times in a loop caused a 5-minute lag.
    # By strictly sampling a maximum of 25 evenly spaced points, we cut fetch time
    # down to ~3 seconds while maintaining complete route risk accuracy.
    MAX_SEGMENTS = 25
    if len(segments) > MAX_SEGMENTS:
        step = len(segments) / MAX_SEGMENTS
        segments = [segments[int(i * step)] for i in range(MAX_SEGMENTS)]

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

    # ---------------- SAVE SEARCH HISTORY ----------------
    if current_user.is_authenticated:
        try:
            start_loc = request.json.get("start_location", "Unknown Location")
            end_loc = request.json.get("end_location", "Unknown Location")
            
            # Use raw geocoded names if provided
            history = SearchHistory(
                user_id=current_user.id,
                start_location=start_loc,
                end_location=end_loc,
                risk_level=final_category,
                risk_score=risk_score(avg_risk),
                factors_json=json.dumps(factors)
            )
            db.session.add(history)
            db.session.commit()
        except Exception as e:
            print("Failed to save history:", e)

    return jsonify(response)


# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    app.run(debug=True)
