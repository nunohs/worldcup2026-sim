import numpy as np
from team_strength import get_team_ratings
from load_adjustments import load_manual_adjustments
from match_simulator import simulate_match

# Round of 32 matchups, using official match numbers (73-88)
# Results are filled in where already known (as of July 1, 2026 data pull)
ROUND_OF_32 = {
    73: {"team_a": "South Africa", "team_b": "Canada", "actual_winner": "Canada"},
    74: {"team_a": "Germany", "team_b": "Paraguay", "actual_winner": "Paraguay"},
    75: {"team_a": "Netherlands", "team_b": "Morocco", "actual_winner": None},
    76: {"team_a": "Brazil", "team_b": "Japan", "actual_winner": "Brazil"},
    77: {"team_a": "France", "team_b": "Sweden", "actual_winner": None},
    78: {"team_a": "Ivory Coast", "team_b": "Norway", "actual_winner": None},
    79: {"team_a": "Mexico", "team_b": "Ecuador", "actual_winner": None},
    80: {"team_a": "England", "team_b": "DR Congo", "actual_winner": None},
    81: {"team_a": "United States", "team_b": "Bosnia and Herzegovina", "actual_winner": None},
    82: {"team_a": "Belgium", "team_b": "Senegal", "actual_winner": None},
    83: {"team_a": "Portugal", "team_b": "Croatia", "actual_winner": None},
    84: {"team_a": "Spain", "team_b": "Austria", "actual_winner": None},
    85: {"team_a": "Switzerland", "team_b": "Algeria", "actual_winner": None},
    86: {"team_a": "Argentina", "team_b": "Cape Verde", "actual_winner": None},
    87: {"team_a": "Colombia", "team_b": "Ghana", "actual_winner": None},
    88: {"team_a": "Australia", "team_b": "Egypt", "actual_winner": None},
}

# Round of 16 pairing logic: which Round of 32 match winners meet
ROUND_OF_16_PAIRINGS = [
    (73, 75),
    (74, 77),
    (76, 78),
    (79, 80),
    (81, 82),
    (83, 84),
    (85, 87),
    (86, 88),
]


def play_knockout_match(team_a, team_b, ratings_df, adjustments_df, host_nations=None):
    """Simulate a single knockout match (with extra time / penalties if drawn)"""
    if host_nations is None:
        host_nations = {"United States", "Mexico", "Canada"}

    team_a_home = team_a in host_nations
    team_b_home = team_b in host_nations

    result = simulate_match(
        team_a, team_b, ratings_df, adjustments_df,
        team_a_is_home=team_a_home, team_b_is_home=team_b_home,
        knockout=True
    )
    return result["winner"]


def simulate_bracket_once(ratings_df, adjustments_df):
    """
    Simulate the entire knockout bracket once, starting from Round of 32.
    Uses real results where already known, simulates the rest.
    Returns the path: round_of_16_teams, quarterfinalists, semifinalists, finalists, champion
    """
    # ROUND OF 32 - get winner of each match
    r32_winners = {}
    for match_num, info in ROUND_OF_32.items():
        if info["actual_winner"] is not None:
            r32_winners[match_num] = info["actual_winner"]
        else:
            winner = play_knockout_match(info["team_a"], info["team_b"], ratings_df, adjustments_df)
            r32_winners[match_num] = winner

    # ROUND OF 16 - pair up winners using official pairing logic
    r16_matchups = []
    for (m1, m2) in ROUND_OF_16_PAIRINGS:
        r16_matchups.append((r32_winners[m1], r32_winners[m2]))

    r16_winners = []
    for team_a, team_b in r16_matchups:
        winner = play_knockout_match(team_a, team_b, ratings_df, adjustments_df)
        r16_winners.append(winner)

    # QUARTERFINALS - pair sequentially (1v2, 3v4, 5v6, 7v8)
    qf_matchups = [
        (r16_winners[0], r16_winners[1]),
        (r16_winners[2], r16_winners[3]),
        (r16_winners[4], r16_winners[5]),
        (r16_winners[6], r16_winners[7]),
    ]
    qf_winners = []
    for team_a, team_b in qf_matchups:
        winner = play_knockout_match(team_a, team_b, ratings_df, adjustments_df)
        qf_winners.append(winner)

    # SEMIFINALS
    sf_matchups = [
        (qf_winners[0], qf_winners[1]),
        (qf_winners[2], qf_winners[3]),
    ]
    sf_winners = []
    for team_a, team_b in sf_matchups:
        winner = play_knockout_match(team_a, team_b, ratings_df, adjustments_df)
        sf_winners.append(winner)

    # FINAL
    champion = play_knockout_match(sf_winners[0], sf_winners[1], ratings_df, adjustments_df)

    return {
        "r32_winners": list(r32_winners.values()),
        "r16_winners": r16_winners,
        "qf_winners": qf_winners,
        "sf_winners": sf_winners,
        "finalists": sf_winners,
        "champion": champion,
    }


def run_tournament_simulation(n_sims=10000):
    """Run the full bracket n times and aggregate results"""
    ratings_df = get_team_ratings()
    adjustments_df = load_manual_adjustments()

    all_teams = set()
    for info in ROUND_OF_32.values():
        all_teams.add(info["team_a"])
        all_teams.add(info["team_b"])

    reach_r16 = {t: 0 for t in all_teams}
    reach_qf = {t: 0 for t in all_teams}
    reach_sf = {t: 0 for t in all_teams}
    reach_final = {t: 0 for t in all_teams}
    win_title = {t: 0 for t in all_teams}

    print(f"\nRunning {n_sims} full knockout bracket simulations...")
    for i in range(n_sims):
        result = simulate_bracket_once(ratings_df, adjustments_df)

        for t in result["r16_winners"]:
            reach_r16[t] += 1
        for t in result["qf_winners"]:
            reach_qf[t] += 1
        for t in result["sf_winners"]:
            reach_sf[t] += 1
        for t in result["finalists"]:
            reach_final[t] += 1
        win_title[result["champion"]] += 1

        if (i + 1) % 2000 == 0:
            print(f"  {i + 1}/{n_sims} done")

    # Build final results table
    output = []
    for team in all_teams:
        output.append({
            "team": team,
            "Round_of_16_%": round(reach_r16[team] / n_sims * 100, 1),
            "Quarterfinal_%": round(reach_qf[team] / n_sims * 100, 1),
            "Semifinal_%": round(reach_sf[team] / n_sims * 100, 1),
            "Final_%": round(reach_final[team] / n_sims * 100, 1),
            "Champion_%": round(win_title[team] / n_sims * 100, 1),
        })

    output.sort(key=lambda x: x["Champion_%"], reverse=True)
    return output


if __name__ == "__main__":
    results = run_tournament_simulation(n_sims=10000)

    print("\n" + "="*90)
    print("2026 FIFA WORLD CUP - KNOCKOUT STAGE PREDICTIONS")
    print("="*90)
    print(f"{'Team':<25} {'R16%':>8} {'QF%':>8} {'SF%':>8} {'Final%':>8} {'Champion%':>10}")
    for r in results:
        if r["Round_of_16_%"] > 0:  # only show teams still alive
            print(f"{r['team']:<25} {r['Round_of_16_%']:>8} {r['Quarterfinal_%']:>8} {r['Semifinal_%']:>8} {r['Final_%']:>8} {r['Champion_%']:>10}")