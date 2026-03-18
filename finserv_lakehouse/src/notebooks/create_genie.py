import os
from databricks.sdk import WorkspaceClient

# Provide credentials for the free edition workspace
os.environ["DATABRICKS_HOST"] = "https://dbc-61514402-8451.cloud.databricks.com"
os.environ["DATABRICKS_CLIENT_ID"] = "5d54409d-304c-42aa-8a21-8070a8879443"
os.environ["DATABRICKS_CLIENT_SECRET"] = "REDACTED_DATABRICKS_OAUTH_SECRET"

w = WorkspaceClient()

print("Creating Genie space...")
try:
    from databricks.sdk.service.genie import CreateSpaceMessage
except ImportError:
    print("Genie API missing in SDK version. Try another way.")

