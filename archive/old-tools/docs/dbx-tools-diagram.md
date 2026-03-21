# dbx-tools.ts Overview

```mermaid
graph TD
    subgraph Extension
        root["dbx-tools.ts<br/>Custom Databricks tools"]
    end

    subgraph Profiles
        profiles["Active profile state\nPRIMARY: slysik\nFALLBACK: slysik-sp\nFailover on auth error"]
    end

    subgraph Helpers
        isAuth["isAuthError(output)"]
        dbxExec["dbxExec(args)\n• pi.exec → databricks CLI\n• Retry with service principal"]
        dbxApi["dbxApi(method, path, body)\n• REST calls via CLI\n• JSON parse + failover"]
        runSql["runSql(sql, warehouse)\n• POST /sql/statements\n• Returns rows + schema"]
    end

    subgraph Tools
        auth["dbx_auth_check\nCheck PAT, switch profiles"]
        cluster["dbx_cluster_status\nGET /clusters/get"]
        runNotebook["dbx_run_notebook\nPOST /jobs/runs + poll"]
        pipeline["dbx_poll_pipeline\nDLT/Lakeflow updates"]
        validate["dbx_validate_tables\nCOUNT(*) Bronze/Silver/Gold"]
        sql["dbx_sql\nSingle SQL via warehouse"]
        dashboard["dbx_deploy_dashboard\nLakeview create/update + publish"]
        cleanup["dbx_cleanup\nDelete pipelines/jobs/dashboards/tables"]
    end

    subgraph External
        cli["Databricks CLI\n(databricks -p <profile>)"]
        api["Databricks REST API\n/jobs, /pipelines, /lakeview"]
        warehouse["Serverless SQL Warehouse\nID b89b264d78f9d52e"]
    end

    root --> profiles
    root --> isAuth
    root --> dbxExec
    root --> dbxApi
    root --> runSql

    dbxExec --> cli
    dbxApi --> cli
    dbxApi --> api
    runSql --> warehouse

    auth --> dbxExec
    cluster --> dbxApi
    runNotebook --> dbxApi
    pipeline --> dbxApi
    validate --> runSql
    sql --> runSql
    dashboard --> dbxApi
    cleanup --> dbxApi
    cleanup --> runSql
```

## How to Read This Diagram
- **Extension**: Registers all tools when pi loads the `dbx-tools.ts` extension.
- **Profiles**: Maintains a sticky active profile, failing over from the PAT profile (`slysik`) to the service principal (`slysik-sp`) whenever authentication errors appear.
- **Helpers**: Shared utility functions used by every tool to issue Databricks CLI/REST calls with automatic retry and JSON parsing.
- **Tools**: The eight exported pi tools, each mapped to the helper(s) and APIs they rely on.
- **External**: Databricks systems the extension talks to: CLI auth, REST APIs, and the default SQL warehouse.

Use this as a quick reference when extending or debugging the extension—start at the helper layer to trace how each tool dispatches work to the Databricks platform.
