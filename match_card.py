import json, requests, time
from datetime import datetime

API_KEY = "3c2b2ba5c3a0ccad7f273e8ca96bba5f"
FIXTURES_FILE = "fixtures.json"
OUTPUT_FILE = "h2h_form_combined.json"

headers = {"x-apisports-key": API_KEY}


def get_form_stats(team_id):
    """Fetch last 5 matches and compute detailed form metrics."""
    url = f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=5&status=FT"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json().get("response", [])
        if not data:
            return {}

        stats = {
            "form": "",
            "points": 0,
            "win": 0,
            "draw": 0,
            "loss": 0,
            "scored": [],
            "conceded": [],
            "btts": 0,
            "clean_sheets": 0,
            "failed_to_score": 0,
        }

        for m in data:
            home_id = m["teams"]["home"]["id"]
            away_id = m["teams"]["away"]["id"]
            home_goals = m["goals"]["home"] or 0
            away_goals = m["goals"]["away"] or 0

            if team_id == home_id:
                scored, conceded = home_goals, away_goals
            else:
                scored, conceded = away_goals, home_goals

            stats["scored"].append(scored)
            stats["conceded"].append(conceded)

            # Form string and outcomes
            if scored > conceded:
                stats["form"] += "W"
                stats["points"] += 3
                stats["win"] += 1
            elif scored == conceded:
                stats["form"] += "D"
                stats["points"] += 1
                stats["draw"] += 1
            else:
                stats["form"] += "L"
                stats["loss"] += 1

            if scored > 0 and conceded > 0:
                stats["btts"] += 1
            if conceded == 0:
                stats["clean_sheets"] += 1
            if scored == 0:
                stats["failed_to_score"] += 1

        n = len(data)
        avg_goals = round(sum(stats["scored"]) / n, 2)
        avg_conceded = round(sum(stats["conceded"]) / n, 2)

        # Over-goal thresholds
        over_1_5 = sum((s + c) > 1 for s, c in zip(stats["scored"], stats["conceded"]))
        over_2_5 = sum((s + c) > 2 for s, c in zip(stats["scored"], stats["conceded"]))
        over_3_5 = sum((s + c) > 3 for s, c in zip(stats["scored"], stats["conceded"]))

        return {
            "form": stats["form"],
            "points": stats["points"],
            "win_pct": round(stats["win"] / n * 100, 1),
            "draw_pct": round(stats["draw"] / n * 100, 1),
            "loss_pct": round(stats["loss"] / n * 100, 1),
            "avg_goals": avg_goals,
            "avg_conceded": avg_conceded,
            "over_1_5_pct": round(over_1_5 / n * 100, 1),
            "over_2_5_pct": round(over_2_5 / n * 100, 1),
            "over_3_5_pct": round(over_3_5 / n * 100, 1),
            "btts_pct": round(stats["btts"] / n * 100, 1),
            "clean_sheets_pct": round(stats["clean_sheets"] / n * 100, 1),
            "failed_to_score_pct": round(stats["failed_to_score"] / n * 100, 1),
        }

    except Exception as e:
        print(f"⚠️ Error fetching form for team {team_id}: {e}")
        return {}


def get_h2h_stats(home_id, away_id):
    """Fetch last 10 H2H meetings with extended metrics."""
    url = f"https://v3.football.api-sports.io/fixtures/headtohead?h2h={home_id}-{away_id}&last=10"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json().get("response", [])
        if not data:
            return {}

        total = len(data)
        home_wins = away_wins = draws = 0
        home_goals = away_goals = 0
        over_1_5 = over_2_5 = over_3_5 = btts = 0

        for m in data:
            hg = m["goals"]["home"] or 0
            ag = m["goals"]["away"] or 0
            home_goals += hg
            away_goals += ag

            total_goals = hg + ag
            if total_goals > 1:
                over_1_5 += 1
            if total_goals > 2:
                over_2_5 += 1
            if total_goals > 3:
                over_3_5 += 1
            if hg > 0 and ag > 0:
                btts += 1

            if hg > ag:
                home_wins += 1
            elif hg < ag:
                away_wins += 1
            else:
                draws += 1

        return {
            "matches": total,
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "avg_home_goals": round(home_goals / total, 2),
            "avg_away_goals": round(away_goals / total, 2),
            "over_1_5_pct": round(over_1_5 / total * 100, 1),
            "over_2_5_pct": round(over_2_5 / total * 100, 1),
            "over_3_5_pct": round(over_3_5 / total * 100, 1),
            "btts_pct": round(btts / total * 100, 1),
        }

    except Exception as e:
        print(f"⚠️ Error fetching H2H for {home_id}-{away_id}: {e}")
        return {}


def main():
    with open(FIXTURES_FILE, "r") as f:
        fixtures = json.load(f)

    results = []
    for fx in fixtures:
        home = fx["home"]
        away = fx["away"]
        home_id, away_id = home["id"], away["id"]

        print(f"🔄 {home['name']} vs {away['name']}")

        home_form = get_form_stats(home_id)
        time.sleep(0.5)
        away_form = get_form_stats(away_id)
        time.sleep(0.5)
        h2h = get_h2h_stats(home_id, away_id)
        time.sleep(0.5)

        # Flatten for HTML
        results.append({
            "home_name": home["name"],
            "away_name": away["name"],
            "home_logo": home["logo"],
            "away_logo": away["logo"],
            "home_form_goals": home_form.get("avg_goals", 0),
            "away_form_goals": away_form.get("avg_goals", 0),
            "home_form_last5": home_form.get("form", ""),
            "away_form_last5": away_form.get("form", ""),
            "home_form_win": home_form.get("win_pct", 0),
            "away_form_win": away_form.get("win_pct", 0),
            "home_form_o15": home_form.get("over_1_5_pct", 0),
            "away_form_o15": away_form.get("over_1_5_pct", 0),
            "home_form_o35": home_form.get("over_3_5_pct", 0),
            "away_form_o35": away_form.get("over_3_5_pct", 0),
            "home_form_btts": home_form.get("btts_pct", 0),
            "away_form_btts": away_form.get("btts_pct", 0),
            "home_form_clean": home_form.get("clean_sheets_pct", 0),
            "away_form_clean": away_form.get("clean_sheets_pct", 0),
            "h2h": h2h,
        })

    output = {
        "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "matches": results,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Saved {len(results)} matchups to {OUTPUT_FILE}")
    print(f"🕓 Last Updated: {output['last_updated']}")


if __name__ == "__main__":
    main()
