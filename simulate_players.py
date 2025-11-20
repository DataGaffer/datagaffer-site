import os
import json
import numpy as np
import pytz
from datetime import datetime, timedelta

# ----------- Load data -----------
with open("fixtures.json", "r") as f:
    fixtures = json.load(f)

# --- Get tomorrow’s date based on EST ---
est = pytz.timezone("US/Eastern")
now_est = datetime.now(est)
target_date = (now_est + timedelta(days=1)).strftime("%Y-%m-%d")

with open("teams.json", "r") as f:
    all_teams = json.load(f)

team_id_to_name = {team["id"]: team["name"] for team in all_teams}

PLAYER_STATS_FOLDER = "players"           # current season
PLAYER_STATS_LAST_SEASON = "players_2024" # last season
SIM_OUTPUT_FOLDER = "player_simulations"
os.makedirs(SIM_OUTPUT_FOLDER, exist_ok=True)

SIMULATIONS = 10000

# thresholds
MIN_APPS_CURRENT = 2
MIN_AVG_MINUTES_CURRENT = 45.0

# ---------- Helpers ----------
def per90(count, minutes, appearances):
    """Return per-90 using minutes when available; fallback to appearances."""
    if minutes and minutes > 0:
        denom = minutes / 90.0
    else:
        denom = appearances or 0
    if denom <= 0:
        return 0.0
    return float(count) / float(denom)

def blend_stats(curr, prev):
    """Blend two seasons with fixed weighting: 50% current, 50% last season."""
    if not prev:
        return curr
    blended = {}
    for key in ["appearances", "minutes", "goals", "assists", "shots", "shots_on_target"]:
        blended[key] = int(round(
            (curr.get(key, 0) or 0) * 0.7 +
            (prev.get(key, 0) or 0) * 0.3
        ))
    return {**curr, **blended}

# ---------- Player simulation ----------
def simulate_player(player, team_id, g_scale, a_scale, sh_scale, sot_scale, players):
    mins = float(player.get("minutes", 0) or 0)
    apps = float(player.get("appearances", 0) or 0)

    g_raw   = per90(player.get("goals", 0),            mins, apps)
    a_raw   = per90(player.get("assists", 0),          mins, apps)
    sh_raw  = per90(player.get("shots", 0),            mins, apps)
    sot_raw = per90(player.get("shots_on_target", 0),  mins, apps)

    # Apply scales
    g_per90   = g_raw   * g_scale
    a_per90   = a_raw   * a_scale
    sh_per90  = sh_raw  * sh_scale
    sot_per90 = sot_raw * sot_scale

    # --- Bench/regular/boost adjustment ---
    avg_minutes = mins / apps if apps > 0 else 0
    if avg_minutes < 55:
        play_factor = avg_minutes / 55.0
        g_per90   *= play_factor
        a_per90   *= play_factor
        sh_per90  *= play_factor
        sot_per90 *= play_factor
    elif avg_minutes >= 65:
        g_per90   *= 1.10
        a_per90   *= 1.10
        sot_per90 *= 1.10

    # --- Star-player boost (fixture-adjusted) ---
    def ga_per90(p):
        return (
            per90(p.get("goals", 0), p.get("minutes", 0), p.get("appearances", 0)) * g_scale +
            per90(p.get("assists", 0), p.get("minutes", 0), p.get("appearances", 0)) * a_scale
        )

    top_contributors = sorted(players, key=ga_per90, reverse=True)[:3]
    top_ids = {p.get("id") or p.get("player_id") for p in top_contributors}

    if player.get("id") in top_ids or player.get("player_id") in top_ids:
        g_per90   *= 1.15
        a_per90   *= 1.15
        sh_per90  *= 1.10
        sot_per90 *= 1.10

    # Mild positional nudge (attackers only)
    pos = (player.get("position", "") or "").lower()
    if pos == "attacker":
        g_per90 *= 1.10
        a_per90 *= 1.10

    # Monte Carlo draws
    g_draws   = np.random.poisson(lam=g_per90,   size=SIMULATIONS) if g_per90   > 0 else np.zeros(SIMULATIONS, dtype=int)
    a_draws   = np.random.poisson(lam=a_per90,   size=SIMULATIONS) if a_per90   > 0 else np.zeros(SIMULATIONS, dtype=int)
    sh_draws  = np.random.poisson(lam=sh_per90,  size=SIMULATIONS) if sh_per90  > 0 else np.zeros(SIMULATIONS, dtype=int)
    sot_draws = np.random.poisson(lam=sot_per90, size=SIMULATIONS) if sot_per90 > 0 else np.zeros(SIMULATIONS, dtype=int)

    goals_per90   = float(g_draws.mean())
    assists_per90 = float(a_draws.mean())
    shots_per90   = float(sh_draws.mean())
    sot_per90_out = float(sot_draws.mean())

    # Probabilities
    p1g  = 1.0 - np.exp(-g_per90)
    p1a  = 1.0 - np.exp(-a_per90)
    psoa = 1.0 - np.exp(-(g_per90 + a_per90))

    player_id = player.get("id") or player.get("player_id")

    return {
        "team_id": team_id,
        "player_id": player_id,
        "name": player["name"],
        "position": player.get("position", ""),
        "appearances": int(apps),
        "goals": int(player.get("goals", 0) or 0),
        "assists": int(player.get("assists", 0) or 0),
        "shots": int(player.get("shots", 0) or 0),
        "shots_on_target": int(player.get("shots_on_target", 0) or 0),
        "goals_per90_simulated":   round(goals_per90,   2),
        "assists_per90_simulated": round(assists_per90, 2),
        "shots_per90":             round(shots_per90,   2),
        "sot_per90":               round(sot_per90_out, 2),
        "+1_goal_pct":   round(p1g  * 100.0, 1),
        "+1_assist_pct": round(p1a  * 100.0, 1),
        "soa_pct":       round(psoa * 100.0, 1),
    }

# ---------- Run per fixture ----------
for fixture in fixtures:
    fixture_date = (fixture.get("date") or "").split("T")[0]
    if fixture_date != target_date:
        continue

    for side in ["home", "away"]:
        team_id = fixture.get(f"{side}_id")
        team_name = fixture.get(side, {}).get("name", f"{side}_team")

        # build safe filename
        safe_name = (
            team_name.replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace(":", "_")
            .replace("*", "_")
            .replace("?", "_")
            .replace('"', "_")
            .replace("<", "_")
            .replace(">", "_")
            .replace("|", "_")
        )

        stats_path = os.path.join(PLAYER_STATS_FOLDER, f"{safe_name}.json")
        if not os.path.exists(stats_path):
            print(f"⚠️ No player stats found for {team_name}")
            continue

        with open(stats_path, "r") as f:
            players = json.load(f)

        last_season_path = os.path.join(PLAYER_STATS_LAST_SEASON, f"{safe_name}.json")
        last_season_players = []
        if os.path.exists(last_season_path):
            with open(last_season_path, "r") as f:
                last_season_players = json.load(f)
        prev_by_id = {p["id"]: p for p in last_season_players}

        # --- Filter (current season only) + blend ---
        blended_players = []
        for p in players:
            curr_apps = p.get("appearances", 0) or 0
            curr_mins = p.get("minutes", 0) or 0
            avg_curr  = (curr_mins / curr_apps) if curr_apps > 0 else 0

            if curr_apps < MIN_APPS_CURRENT:
                continue
            if avg_curr < MIN_AVG_MINUTES_CURRENT:
                continue

            prev = prev_by_id.get(p["id"])
            blended = blend_stats(p, prev) if prev else dict(p)
            blended_players.append(blended)

        if not blended_players:
            print(f"❌ No valid players for {team_name}")
            continue

        # fixture inputs
        team_xg_today = float(fixture.get("sim_stats", {}).get("xg", {}).get(side, 1.4) or 1.4)
        team_shots_today = float(fixture.get("sim_stats", {}).get("shots", {}).get(side, 10.0) or 10.0)
        team_sot_today = team_shots_today * 0.40

        # --- Option 2: average-based normalization ---
        def safe_mean(values):
            valid = [v for v in values if v > 0]
            return np.mean(valid) if valid else 0.1

        goal_rates   = [per90(p.get("goals",0), p.get("minutes",0), p.get("appearances",0)) for p in blended_players]
        assist_rates = [per90(p.get("assists",0), p.get("minutes",0), p.get("appearances",0)) for p in blended_players]
        shot_rates   = [per90(p.get("shots",0), p.get("minutes",0), p.get("appearances",0)) for p in blended_players]
        sot_rates    = [per90(p.get("shots_on_target",0), p.get("minutes",0), p.get("appearances",0)) for p in blended_players]

        avg_goals   = safe_mean(goal_rates)
        avg_assists = safe_mean(assist_rates)
        avg_shots   = safe_mean(shot_rates)
        avg_sot     = safe_mean(sot_rates)

        player_count = max(1, len(blended_players))

        g_scale   = (team_xg_today / (avg_goals   * player_count)) if avg_goals   > 0 else 1.0
        a_scale   = (team_xg_today / (avg_assists * player_count)) if avg_assists > 0 else 1.0
        sh_scale  = (team_shots_today / (avg_shots * player_count)) if avg_shots  > 0 else 1.0
        sot_scale = (team_sot_today / (avg_sot    * player_count)) if avg_sot     > 0 else 1.0

        simulated_players = []
        for player in blended_players:
            zero_count = sum([
                1 if player.get("goals", 0) == 0 else 0,
                1 if player.get("assists", 0) == 0 else 0,
                1 if player.get("shots", 0) == 0 else 0,
                1 if player.get("shots_on_target", 0) == 0 else 0
            ])
            if zero_count >= 2:
                continue

            sim = simulate_player(player, team_id, g_scale, a_scale, sh_scale, sot_scale, blended_players)
            if (sim["goals_per90_simulated"] > 0) or (sim["assists_per90_simulated"] > 0) or (sim["shots_per90"] > 0):
                simulated_players.append(sim)

        if simulated_players:
            out_file = os.path.join(SIM_OUTPUT_FOLDER, f"{safe_name}.json")
            with open(out_file, "w") as f:
                json.dump(simulated_players, f, indent=2)
            print(f"✅ Simulated {len(simulated_players)} players for {team_name}")
        else:
            print(f"❌ No valid players found for {team_name}")

# Build an index of outputs for the frontend
sim_files = [f for f in os.listdir(SIM_OUTPUT_FOLDER) if f.endswith(".json")]
with open(os.path.join(SIM_OUTPUT_FOLDER, "index.json"), "w") as f:
    json.dump(sim_files, f, indent=2)

print(f"📁 Created index.json with {len(sim_files)} files")








