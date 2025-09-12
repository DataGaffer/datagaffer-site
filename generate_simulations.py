# generate_simulations.py

import json
from match_simulator import simulate_match

# Load today's fixtures
with open("fixtures.json") as f:
    fixtures = json.load(f)

# Run simulations
sim_results = []

for match in fixtures:
    home_id = match["home_id"]
    away_id = match["away_id"]
    result = simulate_match(home_id, away_id)
    sim_results.append(result)

# Save results
with open("sim_results.json", "w") as f:
    json.dump(sim_results, f, indent=2)

print(f"✅ Simulated {len(sim_results)} match(es) and saved to sim_results.json.")
