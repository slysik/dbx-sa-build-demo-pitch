# Databricks API Matrix Across Skills

## REST API Endpoints by Service

| API Service | Endpoint | Method | Skills That Use It |
|---|---|---|---|
| **Clusters** | `/api/2.0/clusters/list` | GET | databricks-python-sdk |
| | `/api/2.0/clusters/get` | GET | databricks-python-sdk, spark-native-bronze |
| | `/api/2.0/clusters/create` | POST | databricks-python-sdk |
| | `/api/2.0/clusters/start` | POST | databricks-python-sdk |
| | `/api/2.0/clusters/delete` | POST | databricks-python-sdk |
| **Jobs** | `/api/2.1/jobs/create` | POST | databricks-jobs, databricks-python-sdk, asset-bundles |
| | `/api/2.1/jobs/list` | GET | databricks-jobs, databricks-python-sdk, spark-native-bronze |
| | `/api/2.1/jobs/get` | GET | databricks-jobs, databricks-python-sdk |
| | `/api/2.1/jobs/delete` | DELETE | databricks-jobs, databricks-python-sdk, spark-native-bronze |
| | `/api/2.1/jobs/run-now` | POST | databricks-jobs, databricks-python-sdk |
| | `/api/2.1/jobs/runs/submit` | POST | spark-native-bronze |
| | `/api/2.1/jobs/runs/get` | GET | spark-native-bronze, databricks-python-sdk |
| | `/api/2.1/jobs/runs/get-output` | GET | databricks-python-sdk |
| **Pipelines (SDP/DLT)** | `/api/2.0/pipelines` | POST | spark-declarative-pipelines, spark-native-bronze |
| | `/api/2.0/pipelines/{id}` | GET | spark-declarative-pipelines, spark-native-bronze |
| | `/api/2.0/pipelines/{id}` | PUT | spark-native-bronze (sdp-and-dashboard-patterns) |
| | `/api/2.0/pipelines/{id}` | DELETE | spark-native-bronze, spark-declarative-pipelines |
| | `/api/2.0/pipelines` | GET | spark-native-bronze |
| | `/api/2.0/pipelines/{id}/updates` | POST | spark-declarative-pipelines |
| **SQL Statements** | `/api/2.0/sql/statements` | POST | databricks-aibi-dashboards, databricks-python-sdk, spark-native-bronze, databricks-dbsql |
| **SQL Warehouses** | `/api/2.0/sql/warehouses` | GET | databricks-python-sdk, databricks-aibi-dashboards |
| | `/api/2.0/sql/warehouses/{id}` | GET | databricks-python-sdk |
| | `/api/2.0/sql/warehouses` | POST | databricks-python-sdk |
| **Lakeview Dashboards** | `/api/2.0/lakeview/dashboards` | POST | databricks-aibi-dashboards, spark-native-bronze |
| | `/api/2.0/lakeview/dashboards/{id}` | PATCH | databricks-aibi-dashboards, spark-native-bronze |
| | `/api/2.0/lakeview/dashboards/{id}` | GET | databricks-aibi-dashboards |
| | `/api/2.0/lakeview/dashboards` | GET | databricks-aibi-dashboards, spark-native-bronze |
| | `/api/2.0/lakeview/dashboards/{id}` | DELETE | databricks-aibi-dashboards, spark-native-bronze |
| | `/api/2.0/lakeview/dashboards/{id}/published` | POST | databricks-aibi-dashboards, spark-native-bronze |
| | `/api/2.0/lakeview/dashboards/{id}/published` | DELETE | databricks-aibi-dashboards |
| **Unity Catalog — Catalogs** | `/api/2.1/unity-catalog/catalogs` | GET/POST | databricks-python-sdk, databricks-unity-catalog |
| **Unity Catalog — Schemas** | `/api/2.1/unity-catalog/schemas` | GET/POST | databricks-python-sdk, databricks-unity-catalog |
| **Unity Catalog — Tables** | `/api/2.1/unity-catalog/tables` | GET | databricks-python-sdk, databricks-unity-catalog |
| **Unity Catalog — Volumes** | `/api/2.1/unity-catalog/volumes` | GET/POST | databricks-python-sdk, databricks-unity-catalog |
| **Files (Volumes)** | `/api/2.0/fs/files/{path}` | GET/PUT/DELETE | databricks-python-sdk, databricks-unity-catalog |
| | `/api/2.0/fs/directories/{path}` | GET | databricks-python-sdk, databricks-unity-catalog |
| **Model Serving** | `/api/2.0/serving-endpoints` | POST | model-serving, databricks-python-sdk |
| | `/api/2.0/serving-endpoints` | GET | model-serving, databricks-python-sdk |
| | `/api/2.0/serving-endpoints/{name}` | GET | model-serving, databricks-python-sdk |
| | `/api/2.0/serving-endpoints/{name}/invocations` | POST | model-serving, databricks-python-sdk, databricks-agent-bricks |
| **Vector Search** | `/api/2.0/vector-search/endpoints` | POST | databricks-vector-search |
| | `/api/2.0/vector-search/endpoints` | GET | databricks-vector-search |
| | `/api/2.0/vector-search/endpoints/{name}` | GET | databricks-vector-search |
| | `/api/2.0/vector-search/endpoints/{name}` | DELETE | databricks-vector-search |
| | `/api/2.0/vector-search/indexes` | POST | databricks-vector-search |
| | `/api/2.0/vector-search/indexes/{name}` | GET/DELETE | databricks-vector-search |
| | `/api/2.0/vector-search/indexes/{name}/query` | POST | databricks-vector-search |
| | `/api/2.0/vector-search/indexes/{name}/delete-data` | POST | databricks-vector-search |
| **Genie Spaces** | `/api/2.0/genie/spaces` | POST | databricks-genie, databricks-agent-bricks |
| | `/api/2.0/genie/spaces/{id}` | GET/DELETE | databricks-genie, databricks-agent-bricks |
| | `/api/2.0/genie/spaces/{id}/conversations` | POST | databricks-genie |
| | `/api/2.0/genie/spaces/{id}/conversations/{cid}/messages` | POST | databricks-genie |
| **Agent Bricks (KA/MAS)** | `/api/2.0/agent-bricks/knowledge-assistants` | POST | databricks-agent-bricks |
| | `/api/2.0/agent-bricks/knowledge-assistants/{id}` | GET/DELETE | databricks-agent-bricks |
| | `/api/2.0/agent-bricks/supervisor-agents` | POST | databricks-agent-bricks |
| | `/api/2.0/agent-bricks/supervisor-agents/{id}` | GET/DELETE | databricks-agent-bricks |
| **Secrets** | `/api/2.0/secrets/scopes/create` | POST | databricks-python-sdk |
| | `/api/2.0/secrets/put` | PUT | databricks-python-sdk |
| | `/api/2.0/secrets/get` | GET | databricks-python-sdk |
| **Workspace** | `/api/2.0/workspace/import` | POST | spark-native-bronze, repo-best-practices |
| | `/api/2.0/workspace/list` | GET | spark-native-bronze |
| | `/api/2.0/workspace/delete` | POST | spark-native-bronze |
| **Lakebase Provisioned** | `w.database.create_database_instance()` | SDK | lakebase-provisioned |
| | `w.database.get_database_instance()` | SDK | lakebase-provisioned |
| **Lakebase Autoscale** | `w.postgres.create_project()` | SDK | databricks-lakebase-autoscale |
| | `w.postgres.get_endpoint()` | SDK | databricks-lakebase-autoscale |
| | `w.postgres.create_branch()` | SDK | databricks-lakebase-autoscale |
| | `w.postgres.update_endpoint()` | SDK | databricks-lakebase-autoscale |
| | `w.postgres.generate_db_credential()` | SDK | databricks-lakebase-autoscale |
| **Iceberg REST Catalog** | `/api/2.1/unity-catalog/iceberg/v1/` | Various | databricks-iceberg |
| **Zerobus Ingest** | gRPC endpoint (not REST) | Stream | zerobus-ingest |

---

## Skills × API Service Heatmap

| Skill | Clusters | Jobs | Pipelines | SQL Stmt | Warehouses | Dashboards | UC (Cat/Sch/Tbl) | Volumes/Files | Serving | Vector Search | Genie | Agent Bricks | Secrets | Workspace | Lakebase | Iceberg | Zerobus |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **spark-native-bronze** | ● | ● | ● | ● | | ● | | | | | | | | ● | | | |
| **spark-declarative-pipelines** | | | ● | | | | | | | | | | | | | | |
| **databricks-aibi-dashboards** | | | | ● | ● | ● | | | | | | | | | | | |
| **databricks-jobs** | | ● | | | | | | | | | | | | | | | |
| **databricks-python-sdk** | ● | ● | ● | ● | ● | | ● | ● | ● | ● | | | ● | | | | |
| **model-serving** | | | | | | | | | ● | | | | | | | | |
| **databricks-vector-search** | | | | | | | | | | ● | | | | | | | |
| **databricks-genie** | | | | | | | | | | | ● | | | | | | |
| **databricks-agent-bricks** | | | | | | | | | ● | | ● | ● | | | | | |
| **databricks-unity-catalog** | | | | | | | ● | ● | | | | | | | | | |
| **databricks-dbsql** | | | | ● | | | | | | | | | | | | | |
| **databricks-iceberg** | | | | | | | ● | | | | | | | | | ● | |
| **databricks-metric-views** | | | | ● | | | ● | | | | | | | | | | |
| **lakebase-provisioned** | | | | | | | | | | | | | | | ● | | |
| **databricks-lakebase-autoscale** | | | | | | | | | | | | | | | ● | | |
| **asset-bundles** | | ● | ● | | | ● | | | | | | | | ● | | | |
| **databricks-app-python** | | | | ● | ● | | | | ● | | | | | | ● | | |
| **databricks-config** | ● | | | | | | | | | | | | | | | | |
| **databricks-spark-structured-streaming** | ● | | | | | | | | | | | | | | | | |
| **zerobus-ingest** | | | | | | | ● | | | | | | | | | | ● |
| **repo-best-practices** | | | | | | | | | | | | | | ● | | | |
| **databricks-sa** | | | | | | | | | | | | | | | | | |
| **synthetic-data-generation** | | | | | | | | ● | | | | | | | | | |
| **databricks-parsing** | | | | ● | | | | ● | | | | | | | | | |
| **databricks-docs** | | | | | | | | | | | | | | | | | |
| **MLflow skills** *(5 skills)* | | | | | | | | | ● | | | | | | | | |

`●` = skill references or uses this API service

---

## Summary: Most-Used APIs

| Rank | API Service | # Skills Using It |
|---:|---|:---:|
| 1 | **SQL Statements** (`/api/2.0/sql/statements`) | 7 |
| 2 | **Jobs** (`/api/2.1/jobs/*`) | 5 |
| 3 | **Unity Catalog** (catalogs/schemas/tables) | 5 |
| 4 | **Model Serving** (`/api/2.0/serving-endpoints`) | 5 |
| 5 | **Pipelines/SDP** (`/api/2.0/pipelines`) | 4 |
| 6 | **Lakeview Dashboards** (`/api/2.0/lakeview/dashboards`) | 4 |
| 7 | **Clusters** (`/api/2.0/clusters`) | 4 |
| 8 | **Volumes/Files** (`/api/2.0/fs/*`) | 4 |
| 9 | **SQL Warehouses** (`/api/2.0/sql/warehouses`) | 3 |
| 10 | **Workspace** (`/api/2.0/workspace`) | 3 |
| 11 | **Vector Search** (`/api/2.0/vector-search`) | 2 |
| 12 | **Genie Spaces** (`/api/2.0/genie/spaces`) | 2 |
| 13 | **Secrets** (`/api/2.0/secrets`) | 2 |
| 14 | **Agent Bricks** (KA/MAS) | 1 |
| 15 | **Lakebase** (Provisioned + Autoscale) | 2 |
| 16 | **Iceberg REST Catalog** | 1 |
| 17 | **Zerobus Ingest** (gRPC) | 1 |

---

## dbx-tools Extension Coverage

The `dbx-tools` pi extension wraps these APIs into single-call tools:

| dbx-tool | APIs Wrapped |
|---|---|
| `dbx_auth_check` | Auth token validation (profile-based) |
| `dbx_cluster_status` | `GET /api/2.0/clusters/get` |
| `dbx_run_notebook` | `POST /api/2.1/jobs/runs/submit` + `GET /api/2.1/jobs/runs/get` (poll) |
| `dbx_poll_pipeline` | `GET /api/2.0/pipelines` (list) + `POST /api/2.0/pipelines/{id}/updates` + poll |
| `dbx_validate_tables` | `POST /api/2.0/sql/statements` (multiple COUNT queries) |
| `dbx_sql` | `POST /api/2.0/sql/statements` |
| `dbx_deploy_dashboard` | `GET /api/2.0/lakeview/dashboards` + `POST`/`PATCH` + `POST .../published` |
| `dbx_cleanup` | Pipelines DELETE + SQL DROP TABLE + Jobs DELETE + Dashboards DELETE |
