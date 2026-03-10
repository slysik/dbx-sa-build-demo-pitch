# dbx_tools_v1_src

Databricks / PySpark helper toolkit runnable from a Mac terminal with `just`.

## Usage
Run from this directory:

```bash
just --list
just dbx_profile interview_demo.silver_access_events
just dbx_skew interview_demo.silver_access_events building_id,user_id 20
just dbx_plan interview_demo.silver_access_events
just dbx_delta interview_demo.silver_access_events
just dbx_nulls interview_demo.silver_access_events
just dbx_keys interview_demo.silver_access_events building_id,user_id 20
just dbx_compare interview_demo.bronze_access_events interview_demo.silver_access_events event_id
```
