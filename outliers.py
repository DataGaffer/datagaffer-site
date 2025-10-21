# find_outliers.py
import json
import numpy as np
from collections import Counter
from match_simulator import simulate_match  # uses your existing logic

# -------- settings you can tweak ----------
SIMS_PER_FIXTURE = 5000
MIN_TOTAL_GOALS_FOR_OUTLIER = 8         # extreme goal-fests
MIN_SINGLE_TEAM_GOALS = 6               # hatful by one team
MIN_MARGIN = 5                          # 5+ goal win
TOP_N = 12                              # how many outliers to keep overall
OUTFILE = "outliers.json"
# -----------------------------------------

def prob_fmt(p):
    # return "0.02%" instead of 0.0002
    return f"{p*100:.3f}%"

def analyze_fixture(fx):
    """
    fx is a fixture dict from fixtures.json
    We call simulate_match to get the expected goals (means) then do 5k draws.
    """
    home_id = fx["home_id"]
    away_id = fx["away_id"]
    fixture_id = fx.get("fixture_id")

    # Use your simulator to get the expected means (includes H2H & coefficients)
    sim_summary = simulate_match(home_id, away_id, fixture_id=fixture_id)
    # Treat the returned means as Poisson lambdas
    lam_h = max(sim_summary["home_score"], 0.0001)
    lam_a = max(sim_summary["away_score"], 0.0001)

    # Independent Poisson draws for goals
    rng = np.random.default_rng(fixture_id or 0)
    home_goals = rng.poisson(lam=lam_h, size=SIMS_PER_FIXTURE)
    away_goals = rng.poisson(lam=lam_a, size=SIMS_PER_FIXTURE)

    # --- Clamp extremes for realism ---
    home_goals = np.clip(home_goals, 0, 9)
    away_goals = np.clip(away_goals, 0, 9)

    totals = home_goals + away_goals
    margins = (home_goals - away_goals)

    # “Extreme” flags / probabilities
    p_total_big = np.mean(totals >= MIN_TOTAL_GOALS_FOR_OUTLIER)
    p_home_big  = np.mean(home_goals >= MIN_SINGLE_TEAM_GOALS)
    p_away_big  = np.mean(away_goals >= MIN_SINGLE_TEAM_GOALS)
    p_margin_h  = np.mean(margins >= MIN_MARGIN)
    p_margin_a  = np.mean(margins <= -MIN_MARGIN)

    # Find the single craziest observed result
    candidates = []
    for h, a in zip(home_goals, away_goals):
        candidates.append(((abs(h - a), h + a, max(h, a)), (h, a)))

    best_tuple = max(candidates, key=lambda x: x[0])[1]
    best_h, best_a = best_tuple
    best_total = best_h + best_a
    best_margin = abs(best_h - best_a)

    # How rare was that exact scoreline?
    score_counts = Counter(zip(home_goals, away_goals))
    best_count = score_counts[(best_h, best_a)]
    best_prob = best_count / SIMS_PER_FIXTURE

    # Rare wild scorelines
    rare = []
    for (h, a), c in score_counts.items():
        p = c / SIMS_PER_FIXTURE
        if p <= 0.005 and (
            h + a >= MIN_TOTAL_GOALS_FOR_OUTLIER
            or max(h, a) >= MIN_SINGLE_TEAM_GOALS
            or abs(h - a) >= MIN_MARGIN
        ):
            rare.append({
                "scoreline": f"{h}-{a}",
                "prob": p,
                "total_goals": int(h + a),
                "margin": int(abs(h - a)),
                "single_team_max": int(max(h, a)),
                "count": int(c)
            })
    rare.sort(key=lambda r: (r["prob"], -r["total_goals"], -r["margin"]))
    rare_top5 = rare[:5]

    # Outlier score
    rarity_components = [p for p in [p_total_big, p_home_big, p_away_big, p_margin_h, p_margin_a] if p > 0]
    min_rare = min(rarity_components) if rarity_components else 1.0
    outlier_score = (1.0 - min_rare) + best_total * 0.01 + best_margin * 0.02

    return {
        "fixture_id": int(fixture_id or 0),
        "league": fx["league"]["name"],
        "home": {"id": int(fx["home_id"]), "name": fx["home"]["name"]},
        "away": {"id": int(fx["away_id"]), "name": fx["away"]["name"]},
        "date": fx.get("date"),

        "craziest_scoreline_observed": {
            "scoreline": f"{best_h}-{best_a}",
            "total_goals": int(best_total),
            "margin": int(best_margin),
            "probability": float(best_prob),
            "probability_pretty": prob_fmt(best_prob),
            "count": int(best_count),
            "sample_size": SIMS_PER_FIXTURE
        },

        "extreme_probs": {
            f"total_goals>={MIN_TOTAL_GOALS_FOR_OUTLIER}": prob_fmt(p_total_big),
            f"home_goals>={MIN_SINGLE_TEAM_GOALS}":       prob_fmt(p_home_big),
            f"away_goals>={MIN_SINGLE_TEAM_GOALS}":       prob_fmt(p_away_big),
            f"home_margin>={MIN_MARGIN}":                 prob_fmt(p_margin_h),
            f"away_margin>={MIN_MARGIN}":                 prob_fmt(p_margin_a),
        },

        "rare_wild_scorelines": rare_top5,
        "outlier_score": round(float(outlier_score), 6),
    }

def main():
    with open("fixtures.json") as f:
        fixtures = json.load(f)

    results = []
    for fx in fixtures:
        try:
            results.append(analyze_fixture(fx))
        except Exception as e:
            print(f"⚠️ Skipping fixture {fx.get('fixture_id')} due to error: {e}")

    results.sort(key=lambda r: r["outlier_score"], reverse=True)
    top = results[:TOP_N]

    # ✅ Fix NumPy types before dumping
    def default_converter(o):
        if isinstance(o, (np.integer, np.int64, np.int32)):
            return int(o)
        if isinstance(o, (np.floating, np.float32, np.float64)):
            return float(o)
        return str(o)

    with open(OUTFILE, "w") as f:
        json.dump({
            "generated_from": "find_outliers.py",
            "sims_per_fixture": SIMS_PER_FIXTURE,
            "thresholds": {
                "min_total_goals": MIN_TOTAL_GOALS_FOR_OUTLIER,
                "min_single_team_goals": MIN_SINGLE_TEAM_GOALS,
                "min_margin": MIN_MARGIN
            },
            "outliers": top
        }, f, indent=2, default=default_converter)

    print(f"✅ Wrote {len(top)} outliers to {OUTFILE}")

if __name__ == "__main__":
    main()