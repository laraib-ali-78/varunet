"""
Verification for FIX 4:
1. Verify honest 404 when no forecast data exists.
2. Verify real computation and database storage when data exists.
"""

import os
import sys
import psycopg2
from datetime import datetime, timezone
from fastapi import HTTPException

# Add repository root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.query_service import fetch_or_compute_blend

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:kgDS_TGVeQd50rw7EXOJFS7VfPJUAa7D@mainline.proxy.rlwy.net:45735/varunet"
)

def run_checks():
    conn = psycopg2.connect(DATABASE_URL)
    
    print("=== CHECK 1: Call with non-existent forecast date (2035-01-01) ===")
    try:
        res = fetch_or_compute_blend(
            db_session=conn,
            region_id=1,
            valid_time=datetime(2035, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            lead_time_hrs=24,
            variable="rainfall"
        )
        print("FAIL: Expected 404 exception, but got result:", res)
    except HTTPException as e:
        print(f"PASS: Correctly raised HTTPException {e.status_code}: {e.detail}")

    print("\n=== CHECK 2: Call with genuine seeded forecast (2024-06-15) ===")
    cur = conn.cursor()
    cur.execute("""
        SELECT source_id, value 
        FROM forecasts 
        WHERE region_id = 1 
          AND valid_time = '2024-06-15 00:00:00+00' 
          AND lead_time_hrs = 24 
          AND variable = 'rainfall'
        ORDER BY source_id;
    """)
    real_sources = cur.fetchall()
    print("Real source forecast rows in PostgreSQL:")
    for s_id, val in real_sources:
        print(f"  - Source {s_id}: {val:.4f}")

    target_dt = datetime(2024, 6, 15, 0, 0, 0, tzinfo=timezone.utc)
    res = fetch_or_compute_blend(
        db_session=conn,
        region_id=1,
        valid_time=target_dt,
        lead_time_hrs=24,
        variable="rainfall"
    )

    print("\nComputed Blend Result:")
    print(f"  blend_id: {res['blend_id']} (Is NOT NULL: {res['blend_id'] is not None})")
    print(f"  blended_value: {res['blended_value']:.4f}")
    print(f"  weights_json: {res['weights_json']}")
    print(f"  confidence_score: {res['confidence_score']:.4f}")
    print(f"  explanation_text: {res['explanation_text']}")

    # Verify row actually exists in database
    cur.execute("SELECT blend_id, blended_value, weights_json, confidence_score FROM blended_forecasts WHERE blend_id = %s;", (res['blend_id'],))
    db_row = cur.fetchone()
    print(f"\nVerification from PostgreSQL blended_forecasts table:")
    print(f"  Found row: blend_id={db_row[0]}, blended_value={db_row[1]}, confidence={db_row[3]}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    run_checks()
