"""
Recompute Skill Scores from Database Data and Run Three-Way Evaluation
"""

import os
import sys
import psycopg2
import pandas as pd
import numpy as np

# Add repository root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.skill_scoring_engine import compute_skill_scores, upsert_skill_scores
from ml.training.evaluate import run_evaluation

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:kgDS_TGVeQd50rw7EXOJFS7VfPJUAa7D@mainline.proxy.rlwy.net:45735/varunet"
)

def recompute_and_evaluate():
    print(f"Connecting to database to fetch forecasts and observations...")
    conn = psycopg2.connect(DATABASE_URL)
    
    # 1. Fetch observations
    obs_query = "SELECT region_id, valid_time, variable, value FROM observations;"
    obs_df = pd.read_sql(obs_query, conn)
    print(f"Fetched {len(obs_df)} observation records from PostgreSQL.")

    # 2. Fetch forecasts
    fcst_query = "SELECT forecast_id, source_id, region_id, valid_time, lead_time_hrs, variable, value FROM forecasts;"
    fcst_df = pd.read_sql(fcst_query, conn)
    print(f"Fetched {len(fcst_df)} forecast records from PostgreSQL.")

    # 3. Compute skill scores
    print("\nComputing deterministic skill scores stratified across (source, region, regime, season, lead_time, variable)...")
    scores_df = compute_skill_scores(fcst_df, obs_df, min_sample_size=10)
    print(f"Computed {len(scores_df)} valid skill score strata.")

    # 4. Upsert into skill_scores table
    print("\nUpserting into PostgreSQL skill_scores table...")
    upserted = upsert_skill_scores(conn, scores_df)
    conn.commit()
    print(f"Successfully committed {upserted} skill score rows to PostgreSQL!")

    # 5. Verify row count directly
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM skill_scores;")
    count = cur.fetchone()[0]
    print(f"\nVerification query: skill_scores table now contains {count} rows.")
    conn.close()

    # 6. Re-run ml/training/evaluate.py's three-way comparison
    print("\nRunning three-way held-out validation comparison against authoritative dataset...")
    comparison_df = run_evaluation()
    print("\nThree-Way Comparison Summary Table:")
    print(comparison_df.to_string(index=False))

if __name__ == "__main__":
    recompute_and_evaluate()
