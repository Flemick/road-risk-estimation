import pandas as pd
import random
import os

ROWS = 5000

time_of_day = ["morning", "afternoon", "evening", "night"]
day_type = ["weekday", "weekend"]
season = ["summer", "monsoon", "winter"]

weather = ["clear", "cloudy", "rain", "heavy_rain", "fog"]
visibility = ["good", "medium", "poor"]

road_type = ["highway", "urban", "rural"]
road_curvature = ["straight", "moderate", "sharp"]

traffic_density = ["low", "medium", "high"]

lighting = ["good", "poor"]
road_condition = ["dry", "wet", "damaged"]

data = []

for _ in range(ROWS):

    # -------- Random Environment ----------
    t = random.choice(time_of_day)
    d = random.choice(day_type)
    s = random.choice(season)

    w = random.choice(weather)
    v = random.choice(visibility)

    r_type = random.choice(road_type)
    curvature = random.choice(road_curvature)
    junction = random.choice([0, 1])

    traffic = random.choice(traffic_density)
    heavy_vehicle = random.choice([0, 1])

    light = random.choice(lighting)
    road_cond = random.choice(road_condition)

    speed = random.randint(20, 90)

    # -------- Base Risk ----------
    risk = 0.04

    if t == "night":
        risk += 0.08
    elif t == "evening":
        risk += 0.03

    if w == "rain":
        risk += 0.07
    elif w == "heavy_rain":
        risk += 0.12
    elif w == "fog":
        risk += 0.10

    if r_type == "highway":
        risk += 0.05

    if curvature == "sharp":
        risk += 0.10
    elif curvature == "moderate":
        risk += 0.04

    if junction == 1:
        risk += 0.06

    if traffic == "high":
        risk += 0.05

    if heavy_vehicle == 1:
        risk += 0.05

    if light == "poor":
        risk += 0.08

    if road_cond == "wet":
        risk += 0.06
    elif road_cond == "damaged":
        risk += 0.09

    if speed > 70:
        risk += 0.12
    elif speed > 50:
        risk += 0.05

    # -------- Interaction Rules (IMPORTANT) --------

    # Rainy night
    if (t == "night") and (w in ["rain", "heavy_rain"]):
        risk += 0.18

    # Night highway speeding
    if (t == "night") and (r_type == "highway") and (speed > 70):
        risk += 0.20

    # Trucks on sharp curves
    if (heavy_vehicle == 1) and (curvature == "sharp"):
        risk += 0.22

    # Busy junction
    if (junction == 1) and (traffic == "high"):
        risk += 0.18

    # Rural + poor lighting
    if (r_type == "rural") and (light == "poor"):
        risk += 0.16

    # Wet + speed
    if (road_cond == "wet") and (speed > 60):
        risk += 0.18

    # Fog + traffic
    if (w == "fog") and (traffic != "low"):
        risk += 0.17

    # -------- Convert to Probability --------
    probability = risk * 0.55
    probability = min(probability, 0.60)

    accident = 1 if random.random() < probability else 0

    # -------- Save Row --------
    data.append([
        t, d, s, w, v, r_type, curvature, junction,
        traffic, speed, heavy_vehicle, light, road_cond, accident
    ])

# -------- Create DataFrame --------
columns = [
    "time_of_day", "day_type", "season",
    "weather", "visibility",
    "road_type", "road_curvature", "junction",
    "traffic_density", "avg_speed", "heavy_vehicle_presence",
    "lighting", "road_condition",
    "accident_occured"
]

df = pd.DataFrame(data, columns=columns)

os.makedirs("backend/ml/data", exist_ok=True)
save_path = "backend/ml/data/synthetic_road_risk_dataset.csv"
df.to_csv(save_path, index=False)

print("Dataset generated successfully!")
print("Saved at:", save_path)
print("\nClass Distribution:")
print(df["accident_occured"].value_counts(normalize=True))