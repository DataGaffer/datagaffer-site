import os
import json

# Paths
PLAYER_SIM_DIR = "player_simulations"
OUTPUT_FILE = os.path.join(PLAYER_SIM_DIR, "index.json")

def merge_player_files():
    all_players = []

    # Loop through all team json files
    for filename in os.listdir(PLAYER_SIM_DIR):
        if filename.endswith(".json") and filename != "index.json":
            filepath = os.path.join(PLAYER_SIM_DIR, filename)

            with open(filepath, "r") as f:
                players = json.load(f)

                # Try to grab team name from filename (e.g. Arsenal.json -> Arsenal)
                team_name = filename.replace(".json", "")
                for p in players:
                    # Add team info for frontend
                    p["team"] = team_name

                    # Optional: attach team logo path if you store them locally
                    # (e.g. logos/arsenal.png). Otherwise, you can skip this.
                    p["team_logo"] = f"logos/{team_name.lower().replace(' ', '_')}.png"

                    all_players.append(p)

    # Save merged file
    with open(OUTPUT_FILE, "w") as out:
        json.dump(all_players, out, indent=2)

    print(f"✅ Merged {len(all_players)} players into {OUTPUT_FILE}")

if __name__ == "__main__":
    merge_player_files()
