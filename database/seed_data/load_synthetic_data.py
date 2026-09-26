"""
Seed Database with Synthetic Historical Dataset
Reuses the authoritative generate_synthetic_historical_dataset() from ml/training/train_weighting_model.py.
Populates:
1. forecast_sources (3 sources)
2. regions (3 regions with PostGIS WKT polygon)
3. regimes (2 weather regimes)
4. users (forecaster, admin, citizen)
5. observations (1095 daily observations)
6. forecasts (9855 multi-model forecasts across 3 lead times)
"""

import sys
import os
from datetime import datetime, timezone
import psycopg2
from psycopg2.extras import execute_batch

# Add repository root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from ml.training.train_weighting_model import generate_synthetic_historical_dataset
from backend.app.auth.jwt_handler import hash_password

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:kgDS_TGVeQd50rw7EXOJFS7VfPJUAa7D@mainline.proxy.rlwy.net:45735/varunet"
)

def seed_database():
    print(f"Connecting to database: {DATABASE_URL.split('@')[-1]}...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # 1. Populate forecast_sources
        print("\n1. Seeding forecast_sources...")
        sources = [
            (1, "Source 1 (NWP-proxy)", "NWP"),
            (2, "Source 2 (AI/ML-proxy)", "AI/ML"),
            (3, "Source 3 (Ensemble-proxy)", "Ensemble"),
        ]
        cur.execute("""
            INSERT INTO forecast_sources (source_id, name, type)
            VALUES (%s, %s, %s)
            ON CONFLICT (source_id) DO UPDATE 
            SET name = EXCLUDED.name, type = EXCLUDED.type;
        """, sources[0])
        for s in sources[1:]:
            cur.execute("""
                INSERT INTO forecast_sources (source_id, name, type)
                VALUES (%s, %s, %s)
                ON CONFLICT (source_id) DO UPDATE 
                SET name = EXCLUDED.name, type = EXCLUDED.type;
            """, s)
        cur.execute("SELECT setval('forecast_sources_source_id_seq', (SELECT MAX(source_id) FROM forecast_sources));")
        print("   -> forecast_sources seeded.")

        # 2. Populate regimes
        print("\n2. Seeding regimes...")
        regimes = [
            (1, "Normal Synoptic"),
            (2, "Monsoon Active / Intense"),
        ]
        for r in regimes:
            cur.execute("""
                INSERT INTO regimes (regime_id, name)
                VALUES (%s, %s)
                ON CONFLICT (regime_id) DO UPDATE SET name = EXCLUDED.name;
            """, r)
        cur.execute("SELECT setval('regimes_regime_id_seq', (SELECT MAX(regime_id) FROM regimes));")
        print("   -> regimes seeded.")

        # 3. Populate regions with valid PostGIS EPSG:4326 geometries
        print("\n3. Seeding regions...")
        regions = [
            (
                1,
                "Region 1 - Coastal Basin (Kerala & Konkan)",
                "POLYGON((76.9 8.3, 76.2 10.0, 75.0 12.5, 73.7 15.5, 72.8 18.9, 73.5 19.2, 74.5 16.0, 75.8 13.0, 76.9 10.5, 77.5 8.5, 76.9 8.3))"
            ),
            (
                2,
                "Region 2 - Central Plateau (Deccan Belt)",
                "POLYGON((74.8 15.0, 73.5 19.0, 76.0 21.5, 80.5 21.8, 82.0 19.5, 81.0 16.5, 78.5 14.0, 74.8 15.0))"
            ),
            (
                3,
                "Region 3 - Northwest Plains (Gangetic & Indus Valley)",
                "POLYGON((72.0 24.5, 70.5 28.0, 74.0 32.0, 77.5 32.5, 81.0 28.5, 82.5 25.0, 78.0 24.0, 72.0 24.5))"
            ),
        ]
        for rid, rname, wkt in regions:
            cur.execute("""
                INSERT INTO regions (region_id, name, geometry)
                VALUES (%s, %s, ST_GeomFromText(%s, 4326))
                ON CONFLICT (region_id) DO UPDATE 
                SET name = EXCLUDED.name, geometry = EXCLUDED.geometry;
            """, (rid, rname, wkt))
        cur.execute("SELECT setval('regions_region_id_seq', (SELECT MAX(region_id) FROM regions));")
        print("   -> regions seeded.")

        # 4. Populate users
        print("\n4. Seeding default users...")
        users = [
            ("forecaster@varunet.in", hash_password("Forecaster@123"), "forecaster"),
            ("admin@varunet.in", hash_password("Admin@123"), "admin"),
            ("citizen@varunet.in", hash_password("Citizen@123"), "citizen"),
        ]
        for email, p_hash, role in users:
            cur.execute("""
                INSERT INTO users (email, password_hash, role)
                VALUES (%s, %s, %s)
                ON CONFLICT (email) DO UPDATE 
                SET password_hash = EXCLUDED.password_hash, role = EXCLUDED.role;
            """, (email, p_hash, role))
        print("   -> users seeded.")

        # 5. Generate synthetic historical dataset (authoritative function)
        print("\n5. Generating synthetic historical dataset using generate_synthetic_historical_dataset()...")
        df = generate_synthetic_historical_dataset(n_days=365, start_date="2024-01-01", seed=42)
        print(f"   -> Generated {len(df)} forecast records across 365 days and 3 regions.")

        # 6. Extract and insert observations (one per region_id, valid_time, variable)
        print("\n6. Inserting observations...")
        obs_df = df[["region_id", "valid_time", "variable", "observation"]].drop_duplicates(
            subset=["region_id", "valid_time", "variable"]
        )
        obs_data = [
            (
                int(row["region_id"]),
                row["valid_time"].replace(tzinfo=timezone.utc),
                str(row["variable"]),
                float(row["observation"])
            )
            for _, row in obs_df.iterrows()
        ]
        execute_batch(cur, """
            INSERT INTO observations (region_id, valid_time, variable, value)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (region_id, valid_time, variable) DO UPDATE SET value = EXCLUDED.value;
        """, obs_data, page_size=1000)
        print(f"   -> Inserted {len(obs_data)} unique observation records.")

        # 7. Extract and insert forecasts for all 3 sources
        print("\n7. Inserting forecasts for NWP, AI/ML, and Ensemble sources...")
        forecast_rows = []
        source_map = {
            1: "fcst_nwp",
            2: "fcst_aiml",
            3: "fcst_ensemble"
        }
        for _, row in df.iterrows():
            valid_dt = row["valid_time"].replace(tzinfo=timezone.utc)
            r_id = int(row["region_id"])
            lt = int(row["lead_time_hrs"])
            var = str(row["variable"])
            for s_id, col in source_map.items():
                forecast_rows.append((
                    s_id,
                    r_id,
                    valid_dt,
                    lt,
                    var,
                    float(row[col])
                ))
        
        # Clean existing forecasts to avoid unbounded duplicate inflation
        cur.execute("TRUNCATE TABLE forecasts RESTART IDENTITY CASCADE;")
        execute_batch(cur, """
            INSERT INTO forecasts (source_id, region_id, valid_time, lead_time_hrs, variable, value)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, forecast_rows, page_size=2000)
        print(f"   -> Inserted {len(forecast_rows)} forecast records.")

        conn.commit()
        print("\nAll database seeding committed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"Error during seeding: {e}")
        raise e
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    seed_database()
