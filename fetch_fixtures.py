import requests
import json
from datetime import datetime, timedelta
import pytz
from match_simulator import simulate_match
from importlib import reload   # 🔹 added for reloading
import os
import shutil

API_KEY = "3c2b2ba5c3a0ccad7f273e8ca96bba5f"

# Load known team names from teams.json
with open("teams.json", "r") as f:
    known_teams = json.load(f)
known_names = {team["name"] for team in known_teams}

# --- Get tomorrow + day after tomorrow based on EST ---
est = pytz.timezone("US/Eastern")
now_est = datetime.now(est)
target_dates = {
    "tomorrow": (now_est + timedelta(days=1)).strftime("%Y-%m-%d"),
    "day_after": (now_est + timedelta(days=2)).strftime("%Y-%m-%d")
}

all_matches = {"tomorrow": [], "day_after": []}
h2h_data = {}

for label, target_date in target_dates.items():
    print(f"📅 Pulling fixtures for {target_date} ({label}, EST clock)")

    url = f"https://v3.football.api-sports.io/fixtures?date={target_date}"
    headers = {"x-apisports-key": API_KEY}
    response = requests.get(url, headers=headers)
    data = response.json()

    for fixture in data["response"]:
        home = fixture["teams"]["home"]
        away = fixture["teams"]["away"]
        fixture_id = fixture["fixture"]["id"]
        home_id = home["id"]
        away_id = away["id"]

        # Skip teams not in teams.json
        if home["name"] not in known_names or away["name"] not in known_names:
            continue

        # --- Get book odds (1X2) from Bet365 ---
        odds_url = f"https://v3.football.api-sports.io/odds?fixture={fixture_id}&bookmaker=8&bet=1"
        odds_response = requests.get(odds_url, headers=headers).json()
        try:
            odds_data = odds_response["response"][0]["bookmakers"][0]["bets"][0]["values"]
            book_odds = {
                "home_win": float(odds_data[0]["odd"]),
                "draw": float(odds_data[1]["odd"]),
                "away_win": float(odds_data[2]["odd"]),
                "btts": None,
                "over_2_5": None,
                "over_3_5": None,
                "under_2_5": None,
                "home_o1_5": None,
                "away_o1_5": None
            }
        except (IndexError, KeyError, ValueError):
            book_odds = {
                "home_win": None,
                "draw": None,
                "away_win": None,
                "btts": None,
                "over_2_5": None,
                "over_3_5": None,
                "under_2_5": None,
                "home_o1_5": None,
                "away_o1_5": None
            }

        # --- Get H2H stats (last 10 meetings, venue-specific) ---
        h2h_url = f"https://v3.football.api-sports.io/fixtures/headtohead?h2h={home_id}-{away_id}&last=10"
        h2h_response = requests.get(h2h_url, headers=headers).json()

        home_wins, away_wins, draws = 0, 0, 0
        home_goals, away_goals = [], []

        try:
            for match in h2h_response["response"]:
                if match["teams"]["home"]["id"] != home_id:
                    continue  

                h_goals = match["goals"]["home"]
                a_goals = match["goals"]["away"]

                if h_goals is None or a_goals is None:
                    continue

                if h_goals > a_goals:
                    home_wins += 1
                elif a_goals > h_goals:
                    away_wins += 1
                else:
                    draws += 1

                home_goals.append(h_goals)
                away_goals.append(a_goals)

            h2h_stats = {
                "home_wins": home_wins,
                "away_wins": away_wins,
                "draws": draws,
                "h2h_avg_home": round(sum(home_goals) / len(home_goals), 2) if home_goals else None,
                "h2h_avg_away": round(sum(away_goals) / len(away_goals), 2) if away_goals else None,
                "num_matches": len(home_goals)
            }

        except Exception as e:
            print(f"⚠️ H2H error for {home['name']} vs {away['name']}: {e}")
            h2h_stats = {}

        # --- Save fixture ---
        all_matches[label].append({
            "fixture_id": fixture_id,
            "league": {
                "id": fixture["league"]["id"],
                "name": fixture["league"]["name"]
            },
            "home": home,
            "away": away,
            "home_id": home_id,
            "away_id": away_id,
            "home_logo": home["logo"],
            "away_logo": away["logo"],
            "date": fixture["fixture"]["date"],
            "book_odds": book_odds,
            "sim_stats": {}
        })

        # --- Save H2H + odds ---
        key = f"home_{home_id}_{away_id}"
        h2h_data[key] = {
            "book_home_win": book_odds.get("home_win", 0),
            "book_draw": book_odds.get("draw", 0),
            "book_away_win": book_odds.get("away_win", 0),
            "home_wins": h2h_stats.get("home_wins", 0),
            "away_wins": h2h_stats.get("away_wins", 0),
            "draws": h2h_stats.get("draws", 0),
            "avg_home": h2h_stats.get("h2h_avg_home", 0.0),
            "avg_away": h2h_stats.get("h2h_avg_away", 0.0),
            "num_matches": h2h_stats.get("num_matches", 0)
        }

# --- Save H2H immediately ---
with open("h2h_and_odds.json", "w") as f:
    json.dump(h2h_data, f, indent=2)

# --- Reload match_simulator ---
import match_simulator
reload(match_simulator)
simulate_match = match_simulator.simulate_match

# --- Run simulations ---
for label in all_matches:
    for match in all_matches[label]:
        home_id = match["home_id"]
        away_id = match["away_id"]
        fixture_id = match["fixture_id"]

        try:
            sim = simulate_match(home_id, away_id, fixture_id)
            match["sim_stats"] = {
                "xg": {
                    "home": f"{sim['home_score']:.2f}",
                    "away": f"{sim['away_score']:.2f}",
                    "total": f"{(sim['home_score'] + sim['away_score']):.2f}"
                },
                "corners": {
                    "home": f"{sim['home_corners']:.1f}",
                    "away": f"{sim['away_corners']:.1f}",
                    "total": f"{sim['total_corners']:.1f}"
                },
                "shots": {
                    "home": f"{sim['home_shots']:.1f}",
                    "away": f"{sim['away_shots']:.1f}",
                    "total": f"{sim['total_shots']:.1f}"
                },
                "percents": {
                    "home_win_pct": sim["home_win_pct"],
                    "draw_pct": sim["draw_pct"],
                    "away_win_pct": sim["away_win_pct"],
                    "over_2_5_pct": sim["over_2_5_pct"],
                    "over_3_5_pct": sim.get("over_3_5_pct", 0),   # ✅ new
                    "under_2_5_pct": sim.get("under_2_5_pct", 0), # ✅ new
                    "btts_pct": sim["btts_pct"],
                    "home_o1_5_pct": sim["home_o1_5_pct"],
                    "away_o1_5_pct": sim["away_o1_5_pct"]
                }
            }
        except Exception as e:
            print(f"⚠️ Simulation error for {match['home']['name']} vs {match['away']['name']}: {e}")
            match["sim_stats"] = {"xg": {}, "corners": {}, "shots": {}, "percents": {}}

# --- Save yesterday’s fixtures before overwriting ---
if os.path.exists("fixtures.json"):
    shutil.copy("fixtures.json", "fixtures_yesterday.json")

# --- Save tomorrow’s fixtures (main file) ---
with open("fixtures.json", "w") as f:
    json.dump(all_matches["tomorrow"], f, indent=2)

# --- Save day-after-tomorrow’s fixtures ---
with open("fixtures_tomorrow.json", "w") as f:
    json.dump(all_matches["day_after"], f, indent=2)

print(f"✅ Saved {len(all_matches['tomorrow'])} fixture(s) to fixtures.json (tomorrow).")
print(f"✅ Saved {len(all_matches['day_after'])} fixture(s) to fixtures_tomorrow.json (day after tomorrow).")
print("✅ Saved h2h_and_odds.json with goal averages.")







