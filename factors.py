import json
import requests
import datetime
import time
from datetime import datetime as dt

# === CONFIG ===
API_KEY = "3c2b2ba5c3a0ccad7f273e8ca96bba5f"
FIXTURES_FILE = "fixtures.json"
OUTPUT_FILE = "env_factors.json"

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
headers = {"x-apisports-key": API_KEY}


# === HELPERS ===
def get_coordinates(team_name):
    """Fetch coordinates for stadium or city."""
    try:
        params = {"name": team_name, "count": 1}
        r = requests.get(GEOCODE_URL, params=params, timeout=10)
        data = r.json()
        if "results" in data and data["results"]:
            lat = data["results"][0]["latitude"]
            lon = data["results"][0]["longitude"]
            return lat, lon
    except Exception as e:
        print(f"⚠️ Geocode error for {team_name}: {e}")
    return (51.5, -0.1)  # fallback to London


def get_weather(lat, lon, date):
    """Fetch hourly weather forecast for match day."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation,wind_speed_10m",
        "start_date": date,
        "end_date": date,
        "timezone": "Europe/London"
    }
    try:
        r = requests.get(WEATHER_URL, params=params, timeout=10)
        data = r.json().get("hourly", {})
        temps = data.get("temperature_2m", [])
        prec = data.get("precipitation", [])
        wind = data.get("wind_speed_10m", [])
        if not temps:
            return None
        return {
            "temp": sum(temps) / len(temps),
            "prec": sum(prec) / len(prec),
            "wind": sum(wind) / len(wind)
        }
    except Exception as e:
        print(f"⚠️ Weather fetch error: {e}")
        return None


def weather_score(w):
    score = 0
    icon = "☀️"
    if w["prec"] > 2:
        score -= 5
        icon = "🌧️"
    elif w["prec"] > 0.5:
        score -= 2
        icon = "🌦️"
    if w["wind"] > 20:
        score -= 3
        icon = "🌬️"
    if w["temp"] < 5:
        score -= 2
    if 15 <= w["temp"] <= 25:
        score += 3
    return score, icon


def travel_penalty(home, away):
    """Crude travel proxy — larger gap = more fatigue."""
    if home == away:
        return 0
    if any(c in home or c in away for c in ["United", "City", "FC"]):
        return -2
    return -4


def get_last_matches(team_id):
    """Fetch the team's last 3 real fixtures."""
    url = f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=3"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json().get("response", [])
        dates = sorted([m["fixture"]["date"] for m in data])
        return dates
    except Exception as e:
        print(f"⚠️ Error fetching matches for team {team_id}: {e}")
        return []


def calc_rest_score(match_dates):
    """Convert match gaps into a rest performance score."""
    if len(match_dates) < 2:
        return {"avg_rest": None, "rest_score": 0}

    fmt = [dt.fromisoformat(d.replace("Z", "+00:00")) for d in match_dates]
    gaps = [(fmt[i] - fmt[i + 1]).days for i in range(len(fmt) - 1)]
    avg_rest = sum(gaps) / len(gaps)

    # Neutral rest benchmark = 5 days
    diff = avg_rest - 5.0
    score = max(min(diff * 1.5, 8), -8)  # stronger weight now ±8%
    return {"avg_rest": round(avg_rest, 1), "rest_score": round(score, 1)}


# === MAIN ===
def main():
    today = datetime.date.today().isoformat()

    with open(FIXTURES_FILE, "r") as f:
        fixtures = json.load(f)

    results = {}
    all_outputs = []

    for fxt in fixtures:
        home = fxt["home"]["name"]
        away = fxt["away"]["name"]
        home_id = fxt["home"]["id"]
        away_id = fxt["away"]["id"]

        # --- REST FACTOR ---
        home_last = get_last_matches(home_id)
        away_last = get_last_matches(away_id)
        home_rest = calc_rest_score(home_last)
        away_rest = calc_rest_score(away_last)
        rest_adv = home_rest["rest_score"] - away_rest["rest_score"]

        # --- WEATHER ---
        lat, lon = get_coordinates(home)
        time.sleep(0.3)
        weather = get_weather(lat, lon, today)
        if not weather:
            continue
        wscore, wicon = weather_score(weather)

        # --- TRAVEL ---
        travel = travel_penalty(home, away)

        # --- COMBINE ---
        combined = round(rest_adv + travel + wscore, 1)
        delta_goals = round(combined * 0.02, 2)

        row = {
            "fixture_id": fxt["fixture_id"],
            "league": fxt["league"]["name"],
            "home": home,
            "away": away,
            "delta_goals_pct": combined,
            "delta_goals": delta_goals,
            "rest": round(rest_adv, 1),
            "travel": travel,
            "weather": wscore,
            "weather_icon": wicon,
        }

        all_outputs.append(row)
        print(f"{home} vs {away} → Rest {rest_adv:+}, Weather {wscore:+}, Travel {travel:+}, Total {combined:+}")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_outputs, f, indent=2)

    print(f"\n✅ Saved {len(all_outputs)} matches to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()