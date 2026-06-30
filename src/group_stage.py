import numpy as np
from db_connect import get_engine
from team_strength import get_team_ratings
from load_adjustments import load_manual_adjustments
from match_simulator import simulate_match

def simulate_group_once(teams, ratings_df, adjustments_df):
    """
    Simulate one full group (6 matches), return final standings
    ordered by FIFA 2026 tiebreaker rules.
    """
    points = {t: 0 for t in teams}
    goals_for = {t: 0 for t in teams}
    goals_against = {t: 0 for t in teams}
    head_to_head = {t: {} for t in teams}  # head_to_head[A][B] = points A got vs B

    for i in range(len(teams)):
        for j in range(i+1, len(teams)):
            team_a, team_b = teams[i], teams[j]
            result = simulate_match(team_a, team_b, ratings_df, adjustments_df, knockout=False)

            ga, gb = result["goals_a"], result["goals_b"]
            goals_for[team_a] += ga
            goals_for[team_b] += gb
            goals_against[team_a] += gb
            goals_against[team_b] += ga

            if ga > gb:
                points[team_a] += 3
                head_to_head[team_a][team_b] = 3
                head_to_head[team_b][team_a] = 0
            elif gb > ga:
                points[team_b] += 3
                head_to_head[team_b][team_a] = 3
                head_to_head[team_a][team_b] = 0
            else:
                points[team_a] += 1
                points[team_b] += 1
                head_to_head[team_a][team_b] = 1
                head_to_head[team_b][team_a] = 1

    # Build standings with FIFA 2026 tiebreaker order:
    # 1. Points  2. Overall GD  3. Goals scored  4. (conduct/ranking - skipped, rare to reach)
    def sort_key(team):
        gd = goals_for[team] - goals_against[team]
        return (points[team], gd, goals_for[team])

    standings = sorted(teams, key=sort_key, reverse=True)

    return {
        "standings": standings,
        "points": points,
        "goals_for": goals_for,
        "goals_against": goals_against,
    }


def simulate_group_many(teams, ratings_df, adjustments_df, n_sims=1000):
    """Run group simulation n times, return finish probabilities"""
    finish_counts = {t: {1: 0, 2: 0, 3: 0, 4: 0} for t in teams}

    for _ in range(n_sims):
        result = simulate_group_once(teams, ratings_df, adjustments_df)
        for pos, team in enumerate(result["standings"], 1):
            finish_counts[team][pos] += 1

    output = []
    for team in teams:
        output.append({
            "team": team,
            "1st_%": round(finish_counts[team][1] / n_sims * 100, 1),
            "2nd_%": round(finish_counts[team][2] / n_sims * 100, 1),
            "3rd_%": round(finish_counts[team][3] / n_sims * 100, 1),
            "4th_%": round(finish_counts[team][4] / n_sims * 100, 1),
        })

    return sorted(output, key=lambda x: x["1st_%"], reverse=True)


if __name__ == "__main__":
    ratings_df = get_team_ratings()
    adjustments_df = load_manual_adjustments()

    # Quick test on Group A
    test_group = ["Mexico", "South Korea", "South Africa", "Czech Republic"]
    print("\nTesting Group A simulation (1000 runs)...")
    results = simulate_group_many(test_group, ratings_df, adjustments_df, n_sims=1000)

    print(f"\n{'Team':<20} {'1st%':>6} {'2nd%':>6} {'3rd%':>6} {'4th%':>6}")
    for r in results:
        print(f"{r['team']:<20} {r['1st_%']:>6} {r['2nd_%']:>6} {r['3rd_%']:>6} {r['4th_%']:>6}")