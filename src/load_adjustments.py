import pandas as pd
from db_connect import get_engine

def load_manual_adjustments():
    """Load manual adjustments from Excel and merge with base team ratings"""
    
    # Load the Excel file
    adjustments = pd.read_excel("../inputs/manual_adjustments.xlsx")
    
    print(f"Loaded adjustments for {len(adjustments)} teams")
    
    # Quick sanity check - flag any adjustments outside expected range
    for col in ['attack_adj', 'defence_adj', 'variance_boost', 'home_boost']:
        out_of_range = adjustments[(adjustments[col] < -0.30) | (adjustments[col] > 0.30)]
        if len(out_of_range) > 0:
            print(f"WARNING: {col} has values outside -0.30 to +0.30 range:")
            print(out_of_range[['team', col]])
    
    # Save to PostgreSQL so other scripts can pull it easily
    engine = get_engine()
    adjustments.to_sql("manual_adjustments", engine, if_exists="replace", index=False)
    print("Saved manual adjustments to database")
    
    return adjustments

def get_adjusted_rating(team_name, base_rating, adjustments_df):
    """
    Apply manual adjustments on top of a base rating.
    base_rating is a dict with 'attack_rating' and 'defence_rating'
    Returns adjusted attack_rating, defence_rating, variance_boost, home_boost
    """
    row = adjustments_df[adjustments_df["team"] == team_name]
    
    if len(row) == 0:
        # No adjustment found, return base with zeros
        return {
            "attack_rating": base_rating["attack_rating"],
            "defence_rating": base_rating["defence_rating"],
            "variance_boost": 0.0,
            "home_boost": 0.0
        }
    
    row = row.iloc[0]
    
    # Apply adjustments as additive percentage changes
    adjusted_attack = base_rating["attack_rating"] * (1 + row["attack_adj"])
    adjusted_defence = base_rating["defence_rating"] * (1 + row["defence_adj"])
    
    return {
        "attack_rating": adjusted_attack,
        "defence_rating": adjusted_defence,
        "variance_boost": row["variance_boost"],
        "home_boost": row["home_boost"]
    }

if __name__ == "__main__":
    load_manual_adjustments()