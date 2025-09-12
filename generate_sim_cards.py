import json
from match_simulator import simulate_match

# Load fixtures
with open("fixtures.json") as f:
    fixtures = json.load(f)

# Load h2h and odds
with open("h2h_and_odds.json") as f:
    h2h_and_odds = json.load(f)

sim_cards = []

for fixture in fixtures:
    home_id = fixture["home_id"]
    away_id = fixture["away_id"]
    fixture_key = f"{home_id}_{away_id}"
    book = h2h_and_odds.get(fixture_key, {})

    sim = simulate_match(home_id, away_id)

    def pct_to_odds(p):
        return round(100 / p, 2) if p else 0

    sim_cards.append({
        "home": sim["home"],
        "away": sim["away"],
        "home_logo": sim["home_logo"],
        "away_logo": sim["away_logo"],
        "projected_score": f"{sim['home_score']} vs {sim['away_score']}",
        "win": {
            "sim": f"{sim['home_win_pct']}% ({pct_to_odds(sim['home_win_pct'])})",
            "book": book.get("book_home_win")
        },
        "draw": {
            "sim": f"{sim['draw_pct']}% ({pct_to_odds(sim['draw_pct'])})",
            "book": book.get("book_draw")
        },
        "away_win": {
            "sim": f"{sim['away_win_pct']}% ({pct_to_odds(sim['away_win_pct'])})",
            "book": book.get("book_away_win")
        },
        "home_o1_5": {
            "sim": f"{sim['home_o1_5_pct']}% ({pct_to_odds(sim['home_o1_5_pct'])})",
            "book": book.get("book_home_o1_5")
        },
        "away_o1_5": {
            "sim": f"{sim['away_o1_5_pct']}% ({pct_to_odds(sim['away_o1_5_pct'])})",
            "book": book.get("book_away_o1_5")
        },
        "over_2_5": {
            "sim": f"{sim['over_2_5_pct']}% ({pct_to_odds(sim['over_2_5_pct'])})",
            "book": book.get("book_over_2_5")
        },
        "btts": {
            "sim": f"{sim['btts_pct']}% ({pct_to_odds(sim['btts_pct'])})",
            "book": book.get("book_btts")
        }
    })

# Save to file
with open("sim_cards.json", "w") as f:
    json.dump(sim_cards, f, indent=2)

print(f"✅ {len(sim_cards)} sim card(s) saved to sim_cards.json")


