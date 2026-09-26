import requests
import time

TOKEN = "7f66108e-39a0-4858-88bf-22aaa5c2d42b"
BACKEND_SERVICE_ID = "51b40b30-936f-431b-9a4e-a8c47b44e43e"
ENV_ID = "645ae2ec-fdac-4f09-9ca9-5c6e78bd0c12"
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

q = """
query GetLatestDepl($serviceId: String!, $envId: String!) {
    deployments(first: 1, input: { serviceId: $serviceId, environmentId: $envId }) {
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

for i in range(12):
    res = requests.post(
        "https://backboard.railway.app/graphql/v2",
        headers=headers,
        json={"query": q, "variables": {"serviceId": BACKEND_SERVICE_ID, "envId": ENV_ID}}
    ).json()
    node = res["data"]["deployments"]["edges"][0]["node"]
    print(f"[{i+1}/12] Deployment {node['id']} status: {node['status']}")
    if node["status"] == "SUCCESS":
        break
    time.sleep(10)
