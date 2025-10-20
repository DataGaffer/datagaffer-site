import json
import requests
from datetime import datetime
from statistics import mean

# ---------- SETTINGS ----------
API_KEY = "3c2b2ba5c3a0ccad7f273e8ca96bba5f"
FIXTURES_FILE = "fixtures.json"     # yesterday’s fixtures (with sim data)
OUTPUT_FILE = "daily_accuracy.json"           # main output file
HEADERS = {"x-apisports-key": API_KEY}
API_URL = "https://v3.football.api-sports.io/fixtures"
TODAY = datetime.utcnow().strftime("%Y-%m-%d")

# ---------- HELPERS ----------
def to_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

def fetch_result(fixture_id):
    """Fetch final match result from API-Football"""
    try:
        res = requests.get(f"{API_URL}?id={fixture_id}", headers=HEADERS).json()
        if not res.get("response"):
            return None, None
        game = res["response"][0]
        return game["goals"]["home"], game["goals"]["away"]
    except Exception as e:
        print(f"⚠️ Error fetching fixture {fixture_id}: {e}")
        return None, None

def load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# ---------- LEAGUE AVERAGING ----------
def update_league_averages(data):
    """Rebuild rolling league averages from all daily matches"""
    all_matches = [m for d in data if "matches" in d for m in d["matches"] if "league" in m]
    leagues = {}

    for m in all_matches:
        league = m["league"]
        leagues.setdefault(league, {"accuracy": [], "diffs": [], "sim_goals": [], "actual_goals": [], "btts": [], "over25": []})

        if m.get("accuracy_score"):
            leagues[league]["accuracy"].append(float(m["accuracy_score"]))
        if m.get("avg_diff"):
            leagues[league]["diffs"].append(float(m["avg_diff"]))

        if m.get("projected_score"):
            try:
                sim_home, sim_away = [float(x) for x in m["projected_score"].split(" - ")]
                leagues[league]["sim_goals"].append(sim_home + sim_away)
            except:
                pass

        if m.get("actual_score"):
            try:
                act_home, act_away = [float(x) for x in m["actual_score"].split(" - ")]
                leagues[league]["actual_goals"].append(act_home + act_away)
                leagues[league]["btts"].append(1 if act_home > 0 and act_away > 0 else 0)
                leagues[league]["over25"].append(1 if (act_home + act_away) > 2.5 else 0)
            except:
                pass

    league_stats = []
    for league, s in leagues.items():
        total = len(s["actual_goals"])
        if total == 0:
            continue
        league_stats.append({
            "league": league,
            "games_tracked": total,
            "dg_score": round(mean(s["accuracy"]), 1) if s["accuracy"] else 0,
            "sim_avg_goals": round(mean(s["sim_goals"]), 2) if s["sim_goals"] else 0,
            "actual_avg_goals": round(mean(s["actual_goals"]), 2) if s["actual_goals"] else 0,
            "actual_btts_pct": round(sum(s["btts"]) / total * 100, 1) if s["btts"] else 0,
            "actual_over25_pct": round(sum(s["over25"]) / total * 100, 1) if s["over25"] else 0
        })
    return league_stats

# ---------- MAIN ----------
def main():
    # Load yesterday’s fixtures (already simulated)
    with open(FIXTURES_FILE, "r") as f:
        fixtures = json.load(f)

    data = load_json(OUTPUT_FILE, {})
    history = data.get("daily", []) if isinstance(data, dict) else data

    today_matches = []

    for m in fixtures:
        fixture_id = m.get("fixture_id")
        league = m["league"]["name"]
        home = m["home"]["name"]
        away = m["away"]["name"]

        sim = m.get("sim_stats", {}).get("xg", {})
        home_proj = to_float(sim.get("home"))
        away_proj = to_float(sim.get("away"))

        home_goals, away_goals = fetch_result(fixture_id)
        if home_goals is None or away_goals is None:
            continue

        # Accuracy metrics
        diff_home = abs(home_proj - home_goals)
        diff_away = abs(away_proj - away_goals)
        avg_diff = round((diff_home + diff_away) / 2, 2)
        accuracy_score = max(0, round(100 - (avg_diff * 25), 1))

        today_matches.append({
            "date": TODAY,
            "league": league,
            "match": f"{home} vs {away}",
            "fixture_id": fixture_id,
            "projected_score": f"{home_proj:.2f} - {away_proj:.2f}",
            "actual_score": f"{home_goals} - {away_goals}",
            "avg_diff": avg_diff,
            "accuracy_score": accuracy_score
        })

    if not today_matches:
        print("⚠️ No completed matches found today.")
        return

    history.append({
        "date": TODAY,
        "matches": today_matches
    })

    # --- Add league summary section ---
    league_summary = update_league_averages(history)

    combined_output = {
        "daily": history,
        "leagues": league_summary
    }

    save_json(OUTPUT_FILE, combined_output)

    print(f"✅ Added {len(today_matches)} matches for {TODAY}")
    print(f"✅ Updated {len(league_summary)} leagues → {OUTPUT_FILE}")

# ---------- RUN ----------
if __name__ == "__main__":
    main()