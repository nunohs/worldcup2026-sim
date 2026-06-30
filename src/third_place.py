import numpy as np
from team_strength import get_team_ratings
from load_adjustments import load_manual_adjustments
from group_stage import simulate_group_once

GROUPS = {
    'A': ['Mexico', 'South Korea', 'South Africa', 'Czech Republic'],
    'B': ['Canada', 'Switzerland', 'Bosnia and Herzegovina', 'Qatar'],
    'C': ['Brazil', 'Morocco', 'Scotland', 'Haiti'],
    'D': ['United States', 'Turkey', 'Australia', 'Paraguay'],
    'E': ['Germany', 'Ivory Coast', 'Ecuador', 'Curaçao'],
    'F': ['Netherlands', 'Japan', 'Sweden', 'Tunisia'],
    'G': ['Belgium', 'Egypt', 'Iran', 'New Zealand'],
    'H': ['Spain', 'Uruguay', 'Saudi Arabia', 'Cape Verde'],
    'I': ['France', 'Senegal', 'Norway', 'Iraq'],
    'J': ['Argentina', 'Austria', 'Algeria', 'Jordan'],
    'K': ['Portugal', 'Colombia', 'DR Congo', 'Uzbekistan'],
    'L': ['England', 'Croatia', 'Ghana', 'Panama'],
}

ACTUAL_BEST_THIRD = ['DR Congo', 'Sweden', 'Ecuador', 'Ghana',
                      'Bosnia and Herzegovina', 'Algeria', 'Paraguay', 'Senegal']


def simulate_full_group_stage_once(ratings_df, adjustments_df):
    """Simulate all 12 groups once, return all team results plus 3rd place rankings"""
    all_third_place = []
    qualified_top2 = []

    for group_name, teams in GROUPS.items():
        result = simulate_group_once(teams, ratings_df, adjustments_df)
        standings = result["standings"]

        # Top 2 auto-qualify
        qualified_top2.extend(standings[:2])

        # 3rd place team goes into the pool for comparison
        third_team = standings[2]
        all_third_place.append({
            "team": third_team,
            "group": group_name,
            "points": result["points"][third_team],
            "gd": result["goals_for"][third_team] - result["goals_against"][third_team],
            "gf": result["goals_for"][third_team]
        })

    # Rank all 12 third-place teams: points -> GD -> goals for
    all_third_place.sort(key=lambda x: (x["points"], x["gd"], x["gf"]), reverse=True)

    best_8_third = [t["team"] for t in all_third_place[:8]]
    eliminated_third = [t["team"] for t in all_third_place[8:]]

    return {
        "qualified_top2": qualified_top2,
        "best_8_third": best_8_third,
        "eliminated_third": eliminated_third,
        "all_third_place_ranked": all_third_place
    }


def validate_third_place(n_sims=2000):
    ratings_df = get_team_ratings()
    adjustments_df = load_manual_adjustments()

    third_place_advance_count = {}

    print(f"\nRunning {n_sims} full group stage simulations...")
    for i in range(n_sims):
        result = simulate_full_group_stage_once(ratings_df, adjustments_df)
        for team in result["best_8_third"]:
            third_place_advance_count[team] = third_place_advance_count.get(team, 0) + 1
        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{n_sims} done")

    # Convert to probabilities and sort
    all_teams = set()
    for teams in GROUPS.values():
        all_teams.update(teams)

    probs = []
    for team in all_teams:
        count = third_place_advance_count.get(team, 0)
        probs.append({"team": team, "advance_as_3rd_%": round(count / n_sims * 100, 1)})

    probs.sort(key=lambda x: x["advance_as_3rd_%"], reverse=True)

    print("\n" + "="*60)
    print("PROBABILITY OF ADVANCING AS A BEST THIRD-PLACE TEAM")
    print("="*60)
    print(f"{'Team':<25} {'Advance %':>10}")
    for p in probs[:16]:  # show top 16 (8 real spots + some margin)
        marker = " <-- ACTUALLY ADVANCED" if p["team"] in ACTUAL_BEST_THIRD else ""
        print(f"{p['team']:<25} {p['advance_as_3rd_%']:>10}{marker}")

    # Score against actual
    top8_predicted = set(p["team"] for p in probs[:8])
    actual_set = set(ACTUAL_BEST_THIRD)
    correct = len(top8_predicted & actual_set)

    print(f"\nCorrectly identified {correct}/8 actual best third-place teams")
    print(f"Predicted top 8: {sorted(top8_predicted)}")
    print(f"Actual top 8:    {sorted(actual_set)}")


if __name__ == "__main__":
    validate_third_place(n_sims=2000)