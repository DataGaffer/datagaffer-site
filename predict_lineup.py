import json
import os

def predict_best_lineup(team_file):
    with open(team_file, "r") as f:
        players = json.load(f)

    # Calculate a "per-90" rating for each player
    for p in players:
        mins = p["minutes"] or 1
        per90 = 90 / mins
        # weighted performance score (goals+assists more valuable than shots)
        p["rating"] = (
            (p["goals"] * 6 + p["assists"] * 3 + p["shots_on_target"] * 1.5 + p["shots"] * 0.5)
            * per90
        )

    # Split by position
    gk = [p for p in players if p["position"] == "Goalkeeper"]
    defenders = [p for p in players if p["position"] == "Defender"]
    mids = [p for p in players if p["position"] == "Midfielder"]
    forwards = [p for p in players if p["position"] == "Attacker"]

    # Sort by rating (descending)
    gk.sort(key=lambda x: x["rating"], reverse=True)
    defenders.sort(key=lambda x: x["rating"], reverse=True)
    mids.sort(key=lambda x: x["rating"], reverse=True)
    forwards.sort(key=lambda x: x["rating"], reverse=True)

    # Pick the best XI (4-3-3)
    lineup = {
        "GK": gk[:1],
        "Defenders": defenders[:4],
        "Midfielders": mids[:3],
        "Attackers": forwards[:3],
    }

    return lineup


def print_lineup(lineup):
    print("\n🏟️ Predicted Best Lineup (4-3-3)\n")
    for pos, group in lineup.items():
        print(f"🧩 {pos}:")
        for p in group:
            print(
                f"  - {p['name']} ({p['position']}) | {p['minutes']} min | "
                f"{p['goals']}G {p['assists']}A | Rating: {p['rating']:.2f}"
            )
        print("")


if __name__ == "__main__":
    # Example run: Chelsea.json in your players folder
    team_path = os.path.join("players", "Chelsea.json")
    lineup = predict_best_lineup(team_path)
    print_lineup(lineup)