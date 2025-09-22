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
PLAYER_STATS_FOLDER = "player_stats"
SIM_OUTPUT_FOLDER = "player_simulations"
os.makedirs(SIM_OUTPUT_FOLDER, exist_ok=True)
SIMULATIONS = 5000
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
def clamp(x, lo, hi):
   return max(lo, min(hi, x))
# ---------- Player simulation ----------
def simulate_player(player, team_id, team_xg_today, team_avg_goals_per_match):
   # Baselines from player stats (use minutes if present)
   mins = float(player.get("minutes", 0) or 0)
   apps = float(player.get("appearances", 0) or 0)
   g_per90_raw   = per90(player.get("goals", 0),            mins, apps)
   a_per90_raw   = per90(player.get("assists", 0),          mins, apps)
   sh_per90_raw  = per90(player.get("shots", 0),            mins, apps)
   sot_per90_raw = per90(player.get("shots_on_target", 0),  mins, apps)
   # Scale from matchup: today’s xG vs typical team goals/match
   # (This gently nudges rates; prevents blow-ups when roster file coverage varies.)
   if team_avg_goals_per_match > 0:
       scale = team_xg_today / team_avg_goals_per_match
   else:
       scale = 1.0
   scale = clamp(scale, 0.6, 1.4)  # keep influence realistic
   g_per90   = g_per90_raw   * scale
   a_per90   = a_per90_raw   * scale
   sh_per90  = sh_per90_raw  * scale
   sot_per90 = sot_per90_raw * scale
   # Mild positional nudges
   pos = (player.get("position", "") or "").lower()
   if pos == "attacker":
       g_per90   *= 1.10
       a_per90   *= 1.05
       sh_per90  *= 1.05
       sot_per90 *= 1.05
   elif pos == "midfielder":
       g_per90   *= 1.05
       a_per90   *= 1.10
   # Cap outliers to reasonable ceilings
   g_per90   = clamp(g_per90,   0.0, 1.20)  # very elite ~1.0–1.2
   a_per90   = clamp(a_per90,   0.0, 1.00)
   sh_per90  = clamp(sh_per90,  0.0, 7.00)
   sot_per90 = clamp(sot_per90, 0.0, 3.50)
   # Monte Carlo draws for means (optional but keeps the “simulated” spirit)
   g_draws   = np.random.poisson(lam=g_per90,   size=SIMULATIONS) if g_per90   > 0 else np.zeros(SIMULATIONS, dtype=int)
   a_draws   = np.random.poisson(lam=a_per90,   size=SIMULATIONS) if a_per90   > 0 else np.zeros(SIMULATIONS, dtype=int)
   sh_draws  = np.random.poisson(lam=sh_per90,  size=SIMULATIONS) if sh_per90  > 0 else np.zeros(SIMULATIONS, dtype=int)
   sot_draws = np.random.poisson(lam=sot_per90, size=SIMULATIONS) if sot_per90 > 0 else np.zeros(SIMULATIONS, dtype=int)
   goals_per90   = float(g_draws.mean())
   assists_per90 = float(a_draws.mean())
   shots_per90   = float(sh_draws.mean())
   sot_per90_out = float(sot_draws.mean())
   # Probabilities (analytical Poisson tail for stability)
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
       stats_path = os.path.join(PLAYER_STATS_FOLDER, f"{team_id}.json")
       if not os.path.exists(stats_path):
           print(f"⚠️ No player stats found for {team_name}")
           continue
       with open(stats_path, "r") as f:
           players = json.load(f)
       # Team totals & matches (use max appearances as proxy for matches played)
       total_goals = sum(p.get("goals", 0) or 0 for p in players)
       team_matches = max((p.get("appearances", 0) or 0) for p in players) or 1  # avoid /0
       team_avg_goals_per_match = total_goals / team_matches
       # Today's simulated team xG
       team_xg_today = float(fixture.get("sim_stats", {}).get("xg", {}).get(side, 1.4) or 1.4)
       simulated_players = []
       for player in players:
           sim = simulate_player(player, team_id, team_xg_today, team_avg_goals_per_match)
           # keep players who project anything non-trivial
           if (sim["goals_per90_simulated"] > 0) or (sim["assists_per90_simulated"] > 0) or (sim["shots_per90"] > 0):
               simulated_players.append(sim)
       if simulated_players:
           out_file = os.path.join(SIM_OUTPUT_FOLDER, f"{team_name.replace(' ', '_')}.json")
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






