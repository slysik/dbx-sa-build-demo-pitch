# Volumes

Comprehensive reference for Unity Catalog Volumes: types, paths, SQL operations, MCP tools, permissions, and best practices.

## Overview

Volumes are Unity Catalog objects that provide governed access to non-tabular data (files) stored in cloud object storage. They live inside schemas and follow the three-level namespace: `catalog.schema.volume`.

| Volume Type | Storage | Use Case |
|-------------|---------|----------|
| **Managed** | UC-managed location | Default choice; UC handles storage lifecycle |
| **External** | Customer-managed location | Existing cloud storage; UC provides governance overlay |

---

## Volume Paths

All volume access uses the `/Volumes/` prefix:

```
/Volumes/{catalog}/{schema}/{volume}/{path_to_file}
```

**Examples:**
```
/Volumes/analytics/bronze/raw_files/2024/01/orders.csv
/Volumes/dbx_weg/bronze/checkpoints/streaming/offsets/
/Volumes/ml_prod/models/artifacts/model_v2.mlmodel
```

---

## SQL Operations

### Create Volume

```sql
-- Managed volume (UC manages storage)
CREATE VOLUME analytics.bronze.raw_files
COMMENT 'Raw CSV/JSON files for bronze ingestion';

-- External volume (point to existing cloud storage)
CREATE EXTERNAL VOLUME analytics.bronze.landing_zone
LOCATION 'abfss://landing@storageaccount.dfs.core.windows.net/incoming'
COMMENT 'External landing zone for vendor data drops';
```

### Alter Volume

```sql
-- Rename volume
ALTER VOLUME analytics.bronze.raw_files
RENAME TO analytics.bronze.raw_data_files;

-- Update owner
ALTER VOLUME analytics.bronze.raw_files
SET OWNER TO `data_engineering`;

-- Update comment
COMMENT ON VOLUME analytics.bronze.raw_files IS 'Updated description';
```

### Drop Volume

```sql
-- Drop managed volume (deletes underlying storage)
DROP VOLUME analytics.bronze.raw_files;

-- Drop external volume (removes UC metadata only, storage untouched)
DROP VOLUME analytics.bronze.landing_zone;

-- Safe drop
DROP VOLUME IF EXISTS analytics.bronze.raw_files;
```

### Query Volume Metadata

```sql
-- List volumes in a schema
SHOW VOLUMES IN analytics.bronze;

-- Describe volume details
DESCRIBE VOLUME analytics.bronze.raw_files;

-- Find volumes via information_schema
SELECT volume_name, volume_type, storage_location, comment
FROM system.information_schema.volumes
WHERE volume_catalog = 'analytics'
  AND volume_schema = 'bronze';
```

---

## MCP Tool Patterns

### list_volume_files

List files and directories in a volume path.

```python
# List root of a volume
list_volume_files(volume_path="/Volumes/analytics/bronze/raw_files/")

# List a subdirectory
list_volume_files(volume_path="/Volumes/analytics/bronze/raw_files/2024/01/")
```

### upload_to_volume

Upload a local file to a volume. **5 GB limit per upload.**

```python
upload_to_volume(
    local_path="/tmp/orders_2024.csv",
    volume_path="/Volumes/analytics/bronze/raw_files/orders_2024.csv"
)
```

### download_from_volume

Download a file from a volume to local filesystem.

```python
download_from_volume(
    volume_path="/Volumes/analytics/bronze/raw_files/orders_2024.csv",
    local_path="/tmp/downloaded_orders.csv"
)
```

### create_volume_directory

Create a directory inside a volume.

```python
create_volume_directory(volume_path="/Volumes/analytics/bronze/raw_files/2024/02")
```

### delete_volume_file / delete_volume_directory

```python
# Delete a single file
delete_volume_file(volume_path="/Volumes/analytics/bronze/raw_files/old_data.csv")

# Delete a directory (must be empty)
delete_volume_directory(volume_path="/Volumes/analytics/bronze/raw_files/archive/")
```

### get_volume_file_info

Get metadata about a file (size, modification time).

```python
get_volume_file_info(volume_path="/Volumes/analytics/bronze/raw_files/orders_2024.csv")
```

---

## Permissions

| Privilege | Allows |
|-----------|--------|
| `READ VOLUME` | Read/download files from the volume |
| `WRITE VOLUME` | Upload/delete files in the volume |
| `CREATE VOLUME` | Create new volumes in the schema |

```sql
-- Grant read access
GRANT READ VOLUME ON VOLUME analytics.bronze.raw_files TO `data_analysts`;

-- Grant write access
GRANT WRITE VOLUME ON VOLUME analytics.bronze.raw_files TO `data_engineering`;

-- Grant ability to create volumes in a schema
GRANT CREATE VOLUME ON SCHEMA analytics.bronze TO `platform_team`;

-- Revoke access
REVOKE WRITE VOLUME ON VOLUME analytics.bronze.raw_files FROM `data_analysts`;

-- Show grants
SHOW GRANTS ON VOLUME analytics.bronze.raw_files;
```

---

## Best Practices

1. **Prefer managed volumes** for most use cases -- UC handles storage lifecycle, cleanup, and governance automatically.
2. **Use external volumes** only when you need to govern existing cloud storage or share storage across workspaces.
3. **Organize with directory structure** -- use date partitions or logical groupings (`/year/month/day/`, `/source_system/entity/`).
4. **Set granular permissions** -- `READ VOLUME` for consumers, `WRITE VOLUME` only for producers.
5. **Use volumes for non-tabular data** -- config files, ML model artifacts, images, CSVs for ingestion. For tabular data, use managed tables.
6. **Name volumes descriptively** -- `raw_files`, `model_artifacts`, `checkpoints`, not `vol1`.

---

## Gotchas

| Issue | Details |
|-------|---------|
| **5 GB upload limit** | API upload capped at 5 GB per file. For larger files, use cloud-native tools (azcopy, gsutil, aws s3 cp) and an external volume. |
| **No direct streaming writes** | Cannot use Structured Streaming to write directly to a volume path. Write to a Delta table, then export if needed. |
| **External volume drops don't delete data** | `DROP VOLUME` on an external volume only removes the UC metadata. The underlying cloud storage is untouched. |
| **Managed volume drops DO delete data** | `DROP VOLUME` on a managed volume deletes the underlying files. Use caution. |
| **Path must start with /Volumes/** | All volume file access requires the `/Volumes/` prefix. Paths like `dbfs:/Volumes/...` will fail. |
| **Directory delete requires empty dir** | `delete_volume_directory` fails if the directory contains files. Delete files first. |
