import os
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from scipy.ndimage import gaussian_filter

# ================= CONFIG =================
FIXTURES_FILE = "fixtures.json"
OUTPUT_DIR = "heatmaps/projected"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ================ HELPERS =================
def norm_name(name):
    return "".join(ch for ch in (name or "") if ch.isalnum() or ch in ("_", "-")).lower()

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# ================ FIELD DRAW ==============
def draw_pitch(ax):
    ax.set_facecolor("#2b753b")  # lush green pitch
    lw = 2.0
    # Outer boundaries
    ax.add_patch(Rectangle((0, 0), 105, 68, edgecolor="white", facecolor="none", lw=lw))
    # Halfway line
    ax.plot([52.5, 52.5], [0, 68], color="white", lw=lw)
    # Center circle + spot
    ax.add_patch(Circle((52.5, 34), 9.15, edgecolor="white", facecolor="none", lw=lw))
    ax.add_patch(Circle((52.5, 34), 0.3, color="white"))
    # Penalty areas + goals
    for x in [0, 105]:
        side = -1 if x == 105 else 1
        ax.add_patch(Rectangle((x - 16.5 * side, 13.84), 16.5 * side, 40.32, edgecolor="white", facecolor="none", lw=lw))
        ax.add_patch(Rectangle((x - 5.5 * side, 24.84), 5.5 * side, 18.32, edgecolor="white", facecolor="none", lw=lw))
        ax.add_patch(Rectangle((x, 30), side * 2, 8, edgecolor="white", facecolor="none", lw=lw))
        ax.add_patch(Circle((x - 11 * side, 34), 0.3, color="white"))
    ax.set_xlim(0, 105)
    ax.set_ylim(0, 68)
    ax.axis("off")

# ================ TEAM HEAT ==============
def generate_team_heat(team_type, xg):
    """Generate realistic clustered heat pattern"""
    field = np.zeros((68, 105))

    # Number of “activity zones”
    n_clusters = np.random.randint(6, 10)
    for _ in range(n_clusters):
        cx = np.random.uniform(0, 105)
        cy = np.random.uniform(10, 58)
        intensity = np.random.uniform(0.6, 1.2)
        field += intensity * np.exp(-(((np.arange(105) - cx) ** 2)[None, :] +
                                      ((np.arange(68)[:, None] - cy) ** 2)) / (2 * np.random.uniform(30, 80)))

    field = gaussian_filter(field, sigma=3)
    field /= field.max() if field.max() > 0 else 1

    # Directional weighting (horizontal bias)
    x_weight = np.linspace(1.4, 0.6, 105) if team_type == "home" else np.linspace(0.6, 1.4, 105)
    field *= x_weight

    # xG scaling
    scale = np.clip(float(xg) / 2.5, 0.5, 1.6)
    field *= scale

    return field

# ================ COMBINE MAPS ==============
def combine_heatmaps(home_map, away_map):
    """Blend home (green-yellow) and away (red-orange)"""
    home_rgb = np.zeros((*home_map.shape, 3))
    away_rgb = np.zeros((*away_map.shape, 3))

    home_rgb[..., 1] = home_map  # green
    home_rgb[..., 0] = home_map * 0.6  # yellow mix

    away_rgb[..., 0] = away_map  # red
    away_rgb[..., 1] = away_map * 0.4  # orange tint

    combined = np.clip(home_rgb + away_rgb, 0, 1)
    return combined

# ================ MAIN GEN =================
def generate_match_heatmaps():
    fixtures = load_json(FIXTURES_FILE)
    if not fixtures:
        print("❌ No fixtures found.")
        return

    for match in fixtures:
        home = match["home"]["name"]
        away = match["away"]["name"]
        try:
            home_xg = float(match["sim_stats"]["xg"]["home"])
            away_xg = float(match["sim_stats"]["xg"]["away"])
        except:
            print(f"⚠️ Missing sim stats for {home} vs {away}")
            continue

        # Generate and merge
        home_map = generate_team_heat("home", home_xg)
        away_map = generate_team_heat("away", away_xg)
        combined = combine_heatmaps(home_map, away_map)

        fig, ax = plt.subplots(figsize=(8, 5))
        draw_pitch(ax)
        ax.imshow(combined, extent=[0, 105, 0, 68], origin="lower", alpha=0.8)
        plt.tight_layout(pad=0)
        output_path = os.path.join(OUTPUT_DIR, f"{norm_name(home)}_vs_{norm_name(away)}.png")
        plt.savefig(output_path, bbox_inches="tight", pad_inches=0)
        plt.close(fig)

        print(f"✅ Created realistic match heatmap for {home} vs {away}")

# ================== RUN ====================
if __name__ == "__main__":
    generate_match_heatmaps()