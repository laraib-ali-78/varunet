import requests

TOKEN = "7f66108e-39a0-4858-88bf-22aaa5c2d42b"
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# First get latest deployment ID
q_depl = """
query GetLatestDepl($serviceId: String!, $envId: String!) {
    deployments(first: 3, input: { serviceId: $serviceId, environmentId: $envId }) {
        edges { node { id status meta createdAt } }
    }
}
"""
res = requests.post(
    "https://backboard.railway.app/graphql/v2",
    headers=headers,
    json={"query": q_depl, "variables": {"serviceId": "51b40b30-936f-431b-9a4e-a8c47b44e43e", "envId": "645ae2ec-fdac-4f09-9ca9-5c6e78bd0c12"}}
).json()
for e in res["data"]["deployments"]["edges"]:
    print(e["node"])
depl_id = res["data"]["deployments"]["edges"][0]["node"]["id"]
print("Latest deployment:", depl_id)


q_logs = """
query GetLogs($deploymentId: String!) {
    deploymentLogs(deploymentId: $deploymentId, limit: 500) {
        message
        timestamp
    }
}
"""
l_res = requests.post(
    "https://backboard.railway.app/graphql/v2",
    headers=headers,
    json={"query": q_logs, "variables": {"deploymentId": depl_id}}
).json()

logs = l_res.get("data", {}).get("deploymentLogs", [])
print(f"Total log lines: {len(logs)}")
for l in logs:
    msg = l.get("message", "")
    if "api/blend" in msg or "500" in msg or "Error" in msg or "error" in msg or "Traceback" in msg or "Exception" in msg:
        print(f"{l.get('timestamp')}: {msg}")

