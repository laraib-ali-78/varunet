import requests

TOKEN = "7f66108e-39a0-4858-88bf-22aaa5c2d42b"
BACKEND_SERVICE_ID = "51b40b30-936f-431b-9a4e-a8c47b44e43e"
ENV_ID = "645ae2ec-fdac-4f09-9ca9-5c6e78bd0c12"
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

mutation = """
mutation DeployLatest($serviceId: String!, $envId: String!) {
    serviceInstanceDeploy(serviceId: $serviceId, environmentId: $envId, latestCommit: true)
}
"""

res = requests.post(
    "https://backboard.railway.app/graphql/v2",
    headers=headers,
    json={"query": mutation, "variables": {"serviceId": BACKEND_SERVICE_ID, "envId": ENV_ID}}
).json()
print("serviceInstanceDeploy result:", res)
