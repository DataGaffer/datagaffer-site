import requests
import json
from datetime import datetime, timedelta
import pytz
import os
import shutil
from importlib import reload

API_KEY = "3c2b2ba5c3a0ccad7f273e8ca96bba5f"

# ---- load allowed national team IDs (your national_teams.json has id + stats only)
with open("team_stats/national_teams.json", "r") as f:
    national_teams = json.load(f)
ALLOWED_IDS = {t["id"] for t in national_teams}

# --- Get tomorrow + day after tomorrow based on EST ---
est = pytz.timezone("US/Eastern")
now_est = datetime.now(est)
target_dates = {
    "tomorrow": (now_est + timedelta(days=1)).strftime("%Y-%m-%d"),
    "day_after": (now_est + timedelta(days=2)).strftime("%Y-%m-%d")
}

all_matches = {"tomorrow": [], "day_after": []}
h2h_data = {}

def implied_pct(dec):
    try:
        d = float(dec)
        return 100.0 / d if d > 1.0 else None
    except:
        return None

for label, target_date in target_dates.items():
    print(f"📅 Pulling NT fixtures for {target_date} ({label}, EST clock)")

    url = f"https://v3.football.api-sports.io/fixtures?date={target_date}"
    headers = {"x-apisports-key": API_KEY}
    data = requests.get(url, headers=headers).json()

    for fx in data.get("response", []):
        fixture_id = fx["fixture"]["id"]
        league = fx["league"]["name"]

        home = fx["teams"]["home"]
        away = fx["teams"]["away"]
        home_id, away_id = home["id"], away["id"]

        # only keep national-team matches we have stats for
        if home_id not in ALLOWED_IDS or away_id not in ALLOWED_IDS:
            continue

        # --- Bet365 1X2
        odds_url = f"https://v3.football.api-sports.io/odds?fixture={fixture_id}&bookmaker=8&bet=1"
        odds_response = requests.get(odds_url, headers=headers).json()
        try:
            vals = odds_response["response"][0]["bookmakers"][0]["bets"][0]["values"]
            book_odds = {
                "home_win": float(vals[0]["odd"]),
                "draw": float(vals[1]["odd"]),
                "away_win": float(vals[2]["odd"]),
                "btts": None,
                "over_2_5": None,
                "home_o1_5": None,
                "away_o1_5": None
            }
        except Exception:
            book_odds = {"home_win": None, "draw": None, "away_win": None,
                         "btts": None, "over_2_5": None, "home_o1_5": None, "away_o1_5": None}

        # --- H2H: last 10, venue-agnostic BUT aligned to today's sides
        h2h_url = f"https://v3.football.api-sports.io/fixtures/headtohead?h2h={home_id}-{away_id}&last=10"
        h2h_response = requests.get(h2h_url, headers=headers).json()

        home_goals_aligned, away_goals_aligned = [], []
        home_wins = away_wins = draws = 0

        try:
            for m in h2h_response.get("response", []):
                mh = m["teams"]["home"]["id"]
                ma = m["teams"]["away"]["id"]
                gh = m["goals"]["home"]
                ga = m["goals"]["away"]
                if gh is None or ga is None:
                    continue

                # map each historical match to "today's home" vs "today's away"
                if mh == home_id and ma == away_id:
                    hg, ag = gh, ga
                elif mh == away_id and ma == home_id:
                    hg, ag = ga, gh
                else:
                    # should not happen, but be safe
                    continue

                home_goals_aligned.append(hg)
                away_goals_aligned.append(ag)
                if   hg > ag: home_wins += 1
                elif ag > hg: away_wins += 1
                else:         draws += 1

            h2h_stats = {
                "home_wins": home_wins,
                "away_wins": away_wins,
                "draws": draws,
                "h2h_avg_home": round(sum(home_goals_aligned) / len(home_goals_aligned), 2) if home_goals_aligned else None,
                "h2h_avg_away": round(sum(away_goals_aligned) / len(away_goals_aligned), 2) if away_goals_aligned else None,
                "num_matches": len(home_goals_aligned)
            }
        except Exception as e:
            print(f"⚠️ H2H error for {home['name']} vs {away['name']}: {e}")
            h2h_stats = {"home_wins":0,"away_wins":0,"draws":0,"h2h_avg_home":None,"h2h_avg_away":None,"num_matches":0}

        # --- Save fixture (same structure you already use)
        all_matches[label].append({
            "fixture_id": fixture_id,
            "league": { "id": fx["league"]["id"], "name": league },
            "home": home,
            "away": away,
            "home_id": home_id,
            "away_id": away_id,
            "home_logo": home["logo"],
            "away_logo": away["logo"],
            "date": fx["fixture"]["date"],
            "book_odds": book_odds,
            "sim_stats": {}
        })

        # --- Save H2H + odds (same key + fields)
        key = f"home_{home_id}_{away_id}"
        h2h_data[key] = {
            "book_home_win": book_odds.get("home_win", 0),
            "book_draw": book_odds.get("draw", 0),
            "book_away_win": book_odds.get("away_win", 0),
            "avg_home": h2h_stats.get("h2h_avg_home", 0.0),
            "avg_away": h2h_stats.get("h2h_avg_away", 0.0),
            "num_matches": h2h_stats.get("num_matches", 0)
        }

# --- Persist H2H first
with open("h2h_and_odds.json", "w") as f:
    json.dump(h2h_data, f, indent=2)

import simulate_nations_match
reload(simulate_nations_match)
simulate_nations_match = simulate_nations_match.simulate_nations_match

for label in all_matches:
    for match in all_matches[label]:
        try:
            sim = simulate_nations_match(match["home_id"], match["away_id"], match["fixture_id"])
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
                    "btts_pct": sim["btts_pct"],
                    "home_o1_5_pct": sim["home_o1_5_pct"],
                    "away_o1_5_pct": sim["away_o1_5_pct"]
                }
            }
        except Exception as e:
            print(f"⚠️ Simulation error for {match['home']['name']} vs {match['away']['name']}: {e}")
            match["sim_stats"] = {"xg": {}, "corners": {}, "shots": {}, "percents": {}}

# --- Save yesterday’s fixtures before overwriting
if os.path.exists("fixtures.json"):
    shutil.copy("fixtures.json", "fixtures_yesterday.json")

# --- Save tomorrow + day-after (same filenames as your club fetch)
with open("fixtures.json", "w") as f:
    json.dump(all_matches["tomorrow"], f, indent=2)

with open("fixtures_tomorrow.json", "w") as f:
    json.dump(all_matches["day_after"], f, indent=2)

print(f"✅ Saved {len(all_matches['tomorrow'])} fixture(s) to fixtures.json (tomorrow).")
print(f"✅ Saved {len(all_matches['day_after'])} fixture(s) to fixtures_tomorrow.json (day after tomorrow).")
print("✅ Saved h2h_and_odds.json with venue-agnostic, correctly aligned averages.")