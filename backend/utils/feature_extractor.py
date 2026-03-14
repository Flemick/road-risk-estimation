import requests
from datetime import datetime
import math
import random
from functools import lru_cache 

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


# ---------------- TIME FEATURES ----------------
def get_time_features():
    now = datetime.now()
    hour = now.hour

    if 5 <= hour < 12:
        time_of_day = "morning"
    elif 12 <= hour < 17:
        time_of_day = "afternoon"
    elif 17 <= hour < 20:
        time_of_day = "evening"
    else:
        time_of_day = "night"

    day_type = "weekend" if now.weekday() >= 5 else "weekday"

    month = now.month
    if month in [6, 7, 8, 9]:
        season = "monsoon"
    elif month in [3, 4, 5]:
        season = "summer"
    else:
        season = "winter"

    return time_of_day, day_type, season


# ---------------- WEATHER FROM API ----------------
@lru_cache(maxsize=200)
def get_weather(lat, lon):
    """
    Uses Open-Meteo free API
    """
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=weathercode,visibility,precipitation"
        )

        response = requests.get(url, timeout=8)
        data = response.json()["current"]

        code = data["weathercode"]

        # Map Open-Meteo weather codes to our dataset categories
        if code in [0]:
            weather = "clear"
        elif code in [1, 2, 3]:
            weather = "cloudy"
        elif code in [45, 48]:
            weather = "fog"
        elif code in [51, 53, 55, 61, 63, 65, 80, 81]:
            weather = "rain"
        elif code in [82]:
            weather = "heavy_rain"
        else:
            weather = "cloudy"

        # derive visibility
        visibility = "poor" if weather in ["fog", "heavy_rain"] else "good"

        return weather, visibility

    except:
        # fallback if API fails
        return "clear", "good"


# ---------------- ROAD TYPE FROM OSM ----------------
@lru_cache(maxsize=200)
def get_road_type(lat, lon):
    query = f"""
    [out:json];
    way(around:30,{lat},{lon})["highway"];
    out tags;
    """

    try:
        response = requests.get(OVERPASS_URL, params={"data": query}, timeout=10)
        data = response.json()

        if len(data["elements"]) == 0:
            return "urban"

        highway = data["elements"][0]["tags"].get("highway", "")

        if highway in ["motorway", "trunk", "primary"]:
            return "highway"
        elif highway in ["residential", "living_street"]:
            return "urban"
        else:
            return "rural"

    except:
        return "urban"


# ---------------- CURVATURE ESTIMATION ----------------
def estimate_curvature(lat1, lon1, lat2, lon2):
    dx = lat2 - lat1
    dy = lon2 - lon1
    distance = math.sqrt(dx*dx + dy*dy)

    if distance < 0.0003:
        return "sharp"
    elif distance < 0.0008:
        return "moderate"
    else:
        return "straight"


# ---------------- TRAFFIC ESTIMATION ----------------
def estimate_traffic(road_type, time_of_day):
    if road_type == "highway" and time_of_day in ["morning", "evening"]:
        return "high"
    elif road_type == "urban":
        return "medium"
    else:
        return "low"


# ---------------- LIGHTING ----------------
def estimate_lighting(time_of_day):
    if time_of_day == "night":
        return "poor"
    return "good"


# ---------------- MAIN FEATURE BUILDER ----------------
def build_feature_dict(lat1, lon1, lat2, lon2):

    time_of_day, day_type, season = get_time_features()

    # REAL WEATHER - Round coordinates to ~11km for aggressive API caching
    weather, visibility = get_weather(round(lat1, 1), round(lon1, 1))

    # derive road condition from weather
    if weather in ["rain", "heavy_rain"]:
        road_condition = "wet"
    else:
        road_condition = "dry"

    # ROAD TYPE - Round coordinates to ~110m for moderate API caching
    road_type = get_road_type(round(lat1, 3), round(lon1, 3))

    curvature = estimate_curvature(lat1, lon1, lat2, lon2)

    traffic = estimate_traffic(road_type, time_of_day)
    lighting = estimate_lighting(time_of_day)

    # probabilistic but realistic
    junction = 1 if random.random() < 0.2 else 0
    heavy_vehicle = 1 if road_type == "highway" and random.random() < 0.35 else 0

    speed = 70 if road_type == "highway" else 40

    return {
        "time_of_day": time_of_day,
        "day_type": day_type,
        "season": season,
        "weather": weather,
        "visibility": visibility,
        "road_type": road_type,
        "road_curvature": curvature,
        "junction": junction,
        "traffic_density": traffic,
        "avg_speed": speed,
        "heavy_vehicle_presence": heavy_vehicle,
        "lighting": lighting,
        "road_condition": road_condition
    }