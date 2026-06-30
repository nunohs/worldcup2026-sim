import numpy as np
from scipy.stats import poisson
from db_connect import get_engine
from team_strength import get_team_ratings, get_team_rating
from load_adjustments import load_manual_adjustments, get_adjusted_rating

BASE_RATE = 1.377  # league average goals per team per match

def get_final_team_rating(team_name, ratings_df, adjustments_df):
    """Get a team's final rating after applying manual adjustments"""
    base = get_team_rating(team_name, ratings_df)
    adjusted = get_adjusted_rating(team_name, base, adjustments_df)
    return adjusted

def simulate_match(team_a, team_b, ratings_df, adjustments_df,
                    team_a_is_home=False, team_b_is_home=False,
                    knockout=False):
    """
    Simulate a single match between team_a and team_b.
    Returns goals scored by each team.
    If knockout=True and the match is drawn, resolves via extra time + penalties.
    """
    rating_a = get_final_team_rating(team_a, ratings_df, adjustments_df)
    rating_b = get_final_team_rating(team_b, ratings_df, adjustments_df)

    # Expected goals — attack vs opponent's defence
    exp_goals_a = BASE_RATE * rating_a["attack_rating"] * rating_b["defence_rating"]
    exp_goals_b = BASE_RATE * rating_b["attack_rating"] * rating_a["defence_rating"]

    # Apply home advantage boost (additive to expected goals)
    if team_a_is_home:
        exp_goals_a *= (1 + rating_a["home_boost"])
    if team_b_is_home:
        exp_goals_b *= (1 + rating_b["home_boost"])

    # Apply variance boost — widens the Poisson spread by inflating expected goals slightly
    # then adding extra randomness via a scaling factor
    variance_a = 1 + rating_a["variance_boost"] * (np.random.random() - 0.5)
    variance_b = 1 + rating_b["variance_boost"] * (np.random.random() - 0.5)
    exp_goals_a *= variance_a
    exp_goals_b *= variance_b

    # Ensure expected goals never go negative or zero
    exp_goals_a = max(exp_goals_a, 0.1)
    exp_goals_b = max(exp_goals_b, 0.1)

    # Draw from Poisson distribution
    goals_a = poisson.rvs(exp_goals_a)
    goals_b = poisson.rvs(exp_goals_b)

    result = {
        "team_a": team_a,
        "team_b": team_b,
        "goals_a": int(goals_a),
        "goals_b": int(goals_b),
        "exp_goals_a": round(exp_goals_a, 2),
        "exp_goals_b": round(exp_goals_b, 2),
        "went_to_extra_time": False,
        "went_to_penalties": False,
        "winner": None
    }

    # Determine winner
    if goals_a > goals_b:
        result["winner"] = team_a
    elif goals_b > goals_a:
        result["winner"] = team_b
    else:
        # Draw
        if knockout:
            # Extra time — simulate at reduced intensity (1/3 of a match)
            et_exp_a = exp_goals_a / 3
            et_exp_b = exp_goals_b / 3
            et_goals_a = poisson.rvs(et_exp_a)
            et_goals_b = poisson.rvs(et_exp_b)
            result["went_to_extra_time"] = True
            result["goals_a"] += int(et_goals_a)
            result["goals_b"] += int(et_goals_b)

            if et_goals_a > et_goals_b:
                result["winner"] = team_a
            elif et_goals_b > et_goals_a:
                result["winner"] = team_b
            else:
                # Penalties — roughly 50/50, slight randomness
                result["went_to_penalties"] = True
                result["winner"] = team_a if np.random.random() < 0.5 else team_b
        else:
            result["winner"] = "draw"

    return result


def test_simulator():
    """Run a quick test to sanity check the simulator"""
    ratings_df = get_team_ratings()
    adjustments_df = load_manual_adjustments()

    print("\n" + "="*60)
    print("TESTING MATCH SIMULATOR")
    print("="*60)

    # Test a few matchups, run each 1000 times to check win rates
    test_matchups = [
        ("Argentina", "Jordan"),
        ("France", "Norway"),
        ("Brazil", "Morocco"),
    ]

    for team_a, team_b in test_matchups:
        wins_a, wins_b, draws = 0, 0, 0
        total_goals_a, total_goals_b = 0, 0
        n = 1000

        for _ in range(n):
            result = simulate_match(team_a, team_b, ratings_df, adjustments_df, knockout=False)
            total_goals_a += result["goals_a"]
            total_goals_b += result["goals_b"]
            if result["winner"] == team_a:
                wins_a += 1
            elif result["winner"] == team_b:
                wins_b += 1
            else:
                draws += 1

        print(f"\n{team_a} vs {team_b} ({n} simulations)")
        print(f"  {team_a} wins: {wins_a/n*100:.1f}%")
        print(f"  Draws: {draws/n*100:.1f}%")
        print(f"  {team_b} wins: {wins_b/n*100:.1f}%")
        print(f"  Avg goals: {team_a} {total_goals_a/n:.2f} - {total_goals_b/n:.2f} {team_b}")

if __name__ == "__main__":
    test_simulator()