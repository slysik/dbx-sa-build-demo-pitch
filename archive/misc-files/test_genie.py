import os
from databricks.sdk import WorkspaceClient

w = WorkspaceClient(profile="dbc-61514402-8451")
print(dir(w.genie))
