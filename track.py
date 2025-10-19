import json, requests
from collections import defaultdict
from datetime import datetime

# ---------- SETTINGS ----------
API_KEY = "3c2b2ba5c3a0ccad7f273e8ca96bba5f"
FIXTURES_FILE = "fixtures.json"
OUTPUT_FILE = "league_accuracy_readable.json"
PROCESSED_FILE = "processed_fixtures.json"
HEADERS = {"x-apisports-key": API_KEY}
API_URL = "https://v3.football.api-sports.io/fixtures"

# ---------- HELPERS ----------
def fetch_result(fixture_id):
    """Fetch final match result and ensure it's completed."""
    try:
        res = requests.get(f"{API_URL}?id={fixture_id}", headers=HEADERS).json()
        if not res.get("response"):
            return None, None
        game = res["response"][0]

        # Skip matches not completed (FT, AET only)
        status = game["fixture"]["status"]["short"]
        if status not in ("FT", "AET"):
            return None, None

        return game["goals"]["home"], game["goals"]["away"]
    except Exception as e:
        print(f"⚠️ Error fetching fixture {fixture_id}: {e}")
        return None, None


# ---------- MAIN ----------
def main():
    # Load today's fixtures
    with open(FIXTURES_FILE, "r") as f:
        fixtures = json.load(f)

    # Load or initialize combined accuracy file
    try:
        with open(OUTPUT_FILE, "r") as f:
            combined = json.load(f)
    except FileNotFoundError:
        combined = []

    # Load already processed fixtures to prevent duplicates
    try:
        with open(PROCESSED_FILE, "r") as f:
            processed = set(json.load(f))
    except FileNotFoundError:
        processed = set()

    # Convert list → dict for merging
    combined_dict = {l["league"]: l for l in combined}

    # Ensure all fields exist
    for lg, data in combined_dict.items():
        for key in [
            "games_tracked", "over25_correct", "btts_correct",
            "team_total_correct", "sim_goals_sum", "actual_goals_sum",
            "actual_btts", "actual_over25"
        ]:
            data.setdefault(key, 0)

    # Temporary storage for today's data
    daily_stats = defaultdict(lambda: {
        "games": 0,
        "over25_correct": 0,
        "btts_correct": 0,
        "team_total_correct": 0,
        "sim_goals_sum": 0,
        "actual_goals_sum": 0,
        "actual_btts": 0,
        "actual_over25": 0
    })

    # ---------- PROCESS MATCHES ----------
    for m in fixtures:
        fixture_id = m["fixture_id"]

        # Skip previously processed fixtures
        if fixture_id in processed:
            continue

        home_goals, away_goals = fetch_result(fixture_id)
        if home_goals is None or away_goals is None:
            continue

        league = m["league"]["name"]
        perc = m["sim_stats"]["percents"]

        total_goals = home_goals + away_goals
        both_scored = home_goals > 0 and away_goals > 0
        sim_total = float(m["sim_stats"]["xg"]["total"])

        d = daily_stats[league]
        d["games"] += 1
        d["sim_goals_sum"] += sim_total
        d["actual_goals_sum"] += total_goals
        d["actual_btts"] += int(both_scored)
        d["actual_over25"] += int(total_goals >= 3)

        # Accuracy conditions
        over25_pred = perc["over_2_5_pct"]
        btts_pred = perc["btts_pct"]
        home_pred = perc["home_o1_5_pct"]
        away_pred = perc["away_o1_5_pct"]

        over25_correct = (over25_pred >= 55 and total_goals >= 3) or (over25_pred <= 50 and total_goals <= 2)
        btts_correct = (btts_pred >= 55 and both_scored) or (btts_pred <= 50 and not both_scored)
        home_correct = (home_pred >= 55 and home_goals >= 2) or (home_pred <= 50 and home_goals <= 1)
        away_correct = (away_pred >= 55 and away_goals >= 2) or (away_pred <= 50 and away_goals <= 1)
        team_total_correct = (int(home_correct) + int(away_correct)) / 2

        d["over25_correct"] += int(over25_correct)
        d["btts_correct"] += int(btts_correct)
        d["team_total_correct"] += team_total_correct

        # Add fixture to processed set
        processed.add(fixture_id)

    # ---------- MERGE INTO COMBINED ----------
    for lg, s in daily_stats.items():
        if s["games"] == 0:
            continue

        if lg not in combined_dict:
            combined_dict[lg] = {
                "league": lg,
                "games_tracked": 0,
                "over25_correct": 0,
                "btts_correct": 0,
                "team_total_correct": 0,
                "sim_goals_sum": 0,
                "actual_goals_sum": 0,
                "actual_btts": 0,
                "actual_over25": 0
            }

        c = combined_dict[lg]
        c["games_tracked"] += s["games"]
        c["over25_correct"] += s["over25_correct"]
        c["btts_correct"] += s["btts_correct"]
        c["team_total_correct"] += s["team_total_correct"]
        c["sim_goals_sum"] += s["sim_goals_sum"]
        c["actual_goals_sum"] += s["actual_goals_sum"]
        c["actual_btts"] += s["actual_btts"]
        c["actual_over25"] += s["actual_over25"]

    # ---------- REBUILD SUMMARY ----------
    combined = []
    for lg, c in combined_dict.items():
        g = c["games_tracked"]
        if g == 0:
            continue

        over25_acc = (c["over25_correct"] / g) * 100
        btts_acc = (c["btts_correct"] / g) * 100
        team_total_acc = (c["team_total_correct"] / g) * 100
        dg_score = round((over25_acc + btts_acc + team_total_acc) / 3, 1)

        combined.append({
            "league": lg,
            "games_tracked": g,
            "over25_accuracy": round(over25_acc, 1),
            "btts_accuracy": round(btts_acc, 1),
            "team_total_accuracy": round(team_total_acc, 1),
            "dg_score": dg_score,
            "sim_avg_goals": round(c["sim_goals_sum"] / g, 2) if g > 0 else 0,
            "actual_avg_goals": round(c["actual_goals_sum"] / g, 2) if g > 0 else 0,
            "actual_btts_pct": round((c["actual_btts"] / g) * 100, 1),
            "actual_over25_pct": round((c["actual_over25"] / g) * 100, 1)
        })

    # ---------- SAVE UPDATED FILES ----------
    with open(OUTPUT_FILE, "w") as f:
        json.dump(combined, f, indent=2)

    with open(PROCESSED_FILE, "w") as f:
        json.dump(list(processed), f)

    # ---------- PRINT SUMMARY ----------
    print(f"\n✅ DataGaffer Accuracy Updated ({datetime.utcnow().strftime('%Y-%m-%d')}):\n")
    for s in combined:
        print(
            f"{s['league']}: {s['dg_score']}% | "
            f"O2.5={s['over25_accuracy']} | BTTS={s['btts_accuracy']} | "
            f"TeamTot={s['team_total_accuracy']} | "
            f"Games={s['games_tracked']}"
        )


if __name__ == "__main__":
    main()