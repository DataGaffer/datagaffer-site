import json, requests
from datetime import datetime

# ---------- SETTINGS ----------
API_KEY = "3c2b2ba5c3a0ccad7f273e8ca96bba5f"
FIXTURES_FILE = "fixtures.json"
OUTPUT_FILE = "accuracy.json"
HEADERS = {"x-apisports-key": API_KEY}
API_URL = "https://v3.football.api-sports.io/fixtures"
TODAY = datetime.utcnow().strftime("%Y-%m-%d")


# ---------- FUNCTIONS ----------
def implied_pct(odds):
    return round(100 / odds, 1) if odds and odds > 1 else None

def find_top_picks(fixtures):
    picks = []
    MARKET_MAP = [
        ("home_win_pct", "home_win", lambda m: f"{m['home']['name']} Win"),
        ("away_win_pct", "away_win", lambda m: f"{m['away']['name']} Win"),
        ("over_2_5_pct", "over_2_5", lambda m: "Over 2.5 Goals"),
        ("under_2_5_pct", "under_2_5", lambda m: "Under 2.5 Goals"),
        ("btts_pct", "btts", lambda m: "BTTS Yes"),
        ("home_o1_5_pct", "home_o1_5", lambda m: f"{m['home']['name']} o1.5 Goals"),
        ("away_o1_5_pct", "away_o1_5", lambda m: f"{m['away']['name']} o1.5 Goals"),
    ]

    for match in fixtures:
        sim = match.get("sim_stats", {}).get("percents", {})
        book = match.get("book_odds", {})
        for sim_key, book_key, label_func in MARKET_MAP:
            p = sim.get(sim_key)
            o = book.get(book_key)

            # ✅ Only consider valid decimal odds within realistic range
            if isinstance(p, (int, float)) and isinstance(o, (int, float)) and 1.6 <= o <= 2.3:
                imp = implied_pct(o)
                edge = round(p - imp, 1)

                # ✅ same threshold logic as your plays.html
                if edge > 0 and p >= 55:
                    picks.append({
                        "fixture_id": match.get("fixture_id"),
                        "match": f"{match['home']['name']} vs {match['away']['name']}",
                        "pick": label_func(match),
                        "dg_odds": round(100 / p, 2),
                        "book_odds": round(o, 2),
                        "edge": edge,
                        "league": match.get("league", {}).get("name", "")
                    })

    # ✅ Sort by highest edge first
    picks.sort(key=lambda x: x["edge"], reverse=True)

    # ✅ One pick per match (unique)
    seen = set()
    unique = []
    for p in picks:
        if p["fixture_id"] not in seen:
            unique.append(p)
            seen.add(p["fixture_id"])
        if len(unique) >= 5:  # ✅ top 5 same as plays.html
            break
    return unique


def fetch_result(fixture_id):
    res = requests.get(f"{API_URL}?id={fixture_id}", headers=HEADERS).json()
    if not res.get("response"):
        return None
    game = res["response"][0]
    return game["goals"]["home"], game["goals"]["away"]


def determine_result(pick, home_goals, away_goals, home_name, away_name):
    # 🛑 Skip unfinished matches
    if home_goals is None or away_goals is None:
        return "Pending"

    total = home_goals + away_goals
    pick_lower = pick.lower()

    # --- Goal Totals ---
    if "over 3.5" in pick_lower:
        return "Win" if total > 3 else "Loss"
    if "over 2.5" in pick_lower:
        return "Win" if total > 2 else "Loss"
    if "under 2.5" in pick_lower:
        return "Win" if total < 3 else "Loss"

    # --- Both Teams To Score ---
    if "btts yes" in pick_lower:
        return "Win" if home_goals > 0 and away_goals > 0 else "Loss"

    # --- Team Totals ---
    if "o1.5" in pick_lower:
        if home_name.lower() in pick_lower:
            return "Win" if home_goals >= 2 else "Loss"
        if away_name.lower() in pick_lower:
            return "Win" if away_goals >= 2 else "Loss"

    # --- Win Markets ---
    if "win" in pick_lower:
        if home_name.lower() in pick_lower:
            return "Win" if home_goals > away_goals else "Loss"
        if away_name.lower() in pick_lower:
            return "Win" if away_goals > home_goals else "Loss"

    return "Unknown"


# ---------- MAIN ----------
def main():
    with open(FIXTURES_FILE, "r") as f:
        fixtures = json.load(f)

    top_picks = find_top_picks(fixtures)
    results = []

    for p in top_picks:
        fixture_id = p["fixture_id"]
        res = fetch_result(fixture_id)
        if not res:
            p["result"] = "Pending"
        else:
            home_goals, away_goals = res
            p["result"] = determine_result(p["pick"], home_goals, away_goals,
                                           p["match"].split(" vs ")[0], p["match"].split(" vs ")[1])
        results.append(p)

    try:
        with open(OUTPUT_FILE, "r") as f:
            history = json.load(f)
    except FileNotFoundError:
        history = []

    history.append({
        "date": TODAY,
        "picks": results
    })

    with open(OUTPUT_FILE, "w") as f:
        json.dump(history, f, indent=2)

    print(f"✅ Logged results for {TODAY}:")
    for p in results:
        print(f" - {p['pick']} → {p['result']} (Edge +{p['edge']}%)")


if __name__ == "__main__":
    main()