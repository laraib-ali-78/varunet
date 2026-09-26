import requests
import psycopg2

TOKEN = "7f66108e-39a0-4858-88bf-22aaa5c2d42b"
PROJECT_ID = "bcf3f33c-0fed-406a-a289-1249f5292846"
ENV_ID = "645ae2ec-fdac-4f09-9ca9-5c6e78bd0c12"
BACKEND_SERVICE_ID = "51b40b30-936f-431b-9a4e-a8c47b44e43e"

headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# 1. Get latest deployment for backend service
query_depls = """
query GetDeployments($serviceId: String!, $envId: String!) {
    deployments(first: 5, input: { serviceId: $serviceId, environmentId: $envId }) {
        edges {
            node {
                id
                status
                createdAt
            }
        }
    }
}
"""
r = requests.post(
    "https://backboard.railway.app/graphql/v2",
    headers=headers,
    json={"query": query_depls, "variables": {"serviceId": BACKEND_SERVICE_ID, "envId": ENV_ID}}
).json()

latest_depl_id = r["data"]["deployments"]["edges"][0]["node"]["id"]
print(f"Latest deployment ID: {latest_depl_id}")
print(f"Status: {r['data']['deployments']['edges'][0]['node']['status']}")

# 2. Get logs for latest deployment
query_logs = f"""
query {{
    deploymentLogs(deploymentId: "{latest_depl_id}") {{
        message
        timestamp
    }}
}}
"""
r_logs = requests.post(
    "https://backboard.railway.app/graphql/v2",
    headers=headers,
    json={"query": query_logs}
).json()

logs = r_logs.get("data", {}).get("deploymentLogs", [])
print(f"Total logs fetched: {len(logs)}")
print("\n=== LAST 50 LINES OF BACKEND LOGS ===")
for l in logs[-50:]:
    safe = l["message"].encode("ascii", "replace").decode("ascii").strip()
    print(f"[{l['timestamp']}] {safe}")

# 3. Query PostgreSQL directly
print("\n=== DIRECT POSTGRESQL TABLE & ROW COUNTS ===")
try:
    conn = psycopg2.connect("postgresql://postgres:kgDS_TGVeQd50rw7EXOJFS7VfPJUAa7D@mainline.proxy.rlwy.net:45735/varunet", connect_timeout=10)
    cur = conn.cursor()
    cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
      AND table_type = 'BASE TABLE'
      AND table_name NOT IN ('spatial_ref_sys', 'geography_columns', 'geometry_columns')
    ORDER BY table_name;
    """)
    tables = [row[0] for row in cur.fetchall()]
    print(f"Total Tables: {len(tables)}")
    for t in tables:
        cur.execute(f'SELECT COUNT(*) FROM "{t}";')
        cnt = cur.fetchone()[0]
        print(f"  - {t}: {cnt} rows")
    conn.close()
except Exception as e:
    print(f"PostgreSQL connection error: {e}")

# 4. Check backend service variables
query_vars = """
query GetVariables($projectId: String!, $envId: String!, $serviceId: String!) {
    variables(projectId: $projectId, environmentId: $envId, serviceId: $serviceId)
}
"""
r_vars = requests.post(
    "https://backboard.railway.app/graphql/v2",
    headers=headers,
    json={"query": query_vars, "variables": {"projectId": PROJECT_ID, "envId": ENV_ID, "serviceId": BACKEND_SERVICE_ID}}
).json()
print("\n=== BACKEND ENVIRONMENT VARIABLES ===")
vars_dict = r_vars.get("data", {}).get("variables", {})
for k, v in vars_dict.items():
    if "PASSWORD" in k or "SECRET" in k or "KEY" in k:
        print(f"  {k} = [REDACTED]")
    else:
        print(f"  {k} = {v}")
