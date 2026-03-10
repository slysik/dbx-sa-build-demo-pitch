# SQL Scripting, Stored Procedures, Recursive CTEs, Transactions

## Table of Contents

- [Compound Statements (BEGIN...END)](#compound-statements)
- [Variables: DECLARE and SET](#variables)
- [Control Flow: IF, WHILE, FOR, LOOP, REPEAT](#control-flow)
- [LEAVE and ITERATE](#leave-and-iterate)
- [Exception Handling](#exception-handling)
- [Stored Procedures](#stored-procedures)
- [EXECUTE IMMEDIATE (Dynamic SQL)](#execute-immediate)
- [Recursive CTEs](#recursive-ctes)
- [Multi-Statement Transactions](#multi-statement-transactions)
- [Gotchas and Tips](#gotchas)

---

## Compound Statements

Every SQL script starts with `BEGIN...END`. Can be nested.

```sql
BEGIN
  -- declarations first, then statements
  DECLARE x INT DEFAULT 0;
  SELECT x;
END
```

**Anonymous block** (notebook/DBSQL editor):
```sql
BEGIN
  -- statements here
END
```

---

## Variables

### DECLARE

```sql
DECLARE var_name data_type [DEFAULT expr];
DECLARE v_count INT;                          -- NULL initially
DECLARE v_status STRING DEFAULT 'pending';
DECLARE v_threshold DECIMAL(10,2) DEFAULT 100.00;
```

All `DECLARE` statements must appear **before** any executable statements in the compound block.

### SET

```sql
SET v_count = 42;
SET v_count = (SELECT COUNT(*) FROM my_table);
SET VAR v_count = 42;  -- SET VAR form also valid
```

### SELECT INTO

```sql
SELECT COUNT(*), MAX(amount) INTO v_count, v_max FROM orders;
```

---

## Control Flow

### IF / ELSEIF / ELSE

```sql
IF v_count > 1000 THEN
  SET v_tier = 'high';
ELSEIF v_count > 100 THEN
  SET v_tier = 'medium';
ELSE
  SET v_tier = 'low';
END IF;
```

### CASE (statement form)

```sql
CASE v_region
  WHEN 'US' THEN SET v_tax = 0.08;
  WHEN 'EU' THEN SET v_tax = 0.20;
  ELSE SET v_tax = 0.0;
END CASE;
```

### WHILE

```sql
WHILE v_counter < 10 DO
  INSERT INTO log_table VALUES (v_counter, current_timestamp());
  SET v_counter = v_counter + 1;
END WHILE;
```

### FOR (cursor loop)

```sql
FOR row AS SELECT id, name FROM source_table DO
  INSERT INTO target_table VALUES (row.id, upper(row.name));
END FOR;
```

**Gotcha:** The loop variable (`row`) is implicitly declared. Access columns as `row.column_name`.

### LOOP (infinite until LEAVE)

```sql
lbl: LOOP
  SET v_i = v_i + 1;
  IF v_i > 5 THEN LEAVE lbl; END IF;
  INSERT INTO t VALUES (v_i);
END LOOP lbl;
```

### REPEAT (do-while equivalent)

```sql
REPEAT
  SET v_i = v_i + 1;
  INSERT INTO t VALUES (v_i);
UNTIL v_i >= 10
END REPEAT;
```

---

## LEAVE and ITERATE

| Statement | Effect | Equivalent |
|-----------|--------|------------|
| `LEAVE label` | Exit the labeled loop/block | `break` |
| `ITERATE label` | Skip to next iteration | `continue` |

```sql
process_loop: WHILE v_i < 100 DO
  SET v_i = v_i + 1;
  IF mod(v_i, 2) = 0 THEN ITERATE process_loop; END IF;  -- skip even
  IF v_i > 50 THEN LEAVE process_loop; END IF;            -- exit
  INSERT INTO odd_table VALUES (v_i);
END WHILE process_loop;
```

---

## Exception Handling

### DECLARE HANDLER

```sql
-- EXIT handler: executes body then exits the compound block
DECLARE EXIT HANDLER FOR SQLEXCEPTION
BEGIN
  INSERT INTO error_log VALUES (current_timestamp(), 'ETL failed');
END;

-- CONTINUE handler: executes body then resumes at next statement
DECLARE CONTINUE HANDLER FOR NOT FOUND
BEGIN
  SET v_done = TRUE;
END;
```

**Handler conditions:**

| Condition | Triggers On |
|-----------|------------|
| `SQLEXCEPTION` | Any SQL error |
| `SQLWARNING` | Any SQL warning |
| `NOT FOUND` | No rows returned (cursor/SELECT INTO) |
| `SQLSTATE 'xxxxx'` | Specific SQLSTATE code |
| `condition_name` | User-defined condition |

### SIGNAL (raise error)

```sql
SIGNAL SQLSTATE '45000'
  SET MESSAGE_TEXT = concat('Invalid input: ', v_param);
```

### RESIGNAL (re-raise in handler)

```sql
DECLARE EXIT HANDLER FOR SQLEXCEPTION
BEGIN
  INSERT INTO error_log VALUES (current_timestamp(), 'caught error');
  RESIGNAL;  -- re-raise the original error
END;
```

### GET DIAGNOSTICS

```sql
DECLARE v_msg STRING;
DECLARE v_state STRING;
DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
BEGIN
  GET DIAGNOSTICS CONDITION 1
    v_msg = MESSAGE_TEXT,
    v_state = RETURNED_SQLSTATE;
  INSERT INTO error_log VALUES (v_state, v_msg, current_timestamp());
END;
```

---

## Stored Procedures

### CREATE PROCEDURE

```sql
CREATE OR REPLACE PROCEDURE catalog.schema.proc_name(
  IN p_source STRING,           -- input only (default)
  IN p_batch_size INT,
  OUT p_rows_affected BIGINT,   -- output only
  INOUT p_status STRING         -- input + output
)
LANGUAGE SQL
SQL SECURITY INVOKER            -- runs as caller (recommended)
COMMENT 'Upsert from staging to target'
BEGIN
  -- procedure body (same as compound statement)
  MERGE INTO catalog.schema.target AS t
  USING (SELECT * FROM identifier(p_source)) AS s
  ON t.id = s.id
  WHEN MATCHED THEN UPDATE SET *
  WHEN NOT MATCHED THEN INSERT *;

  SET p_rows_affected = (SELECT COUNT(*) FROM identifier(p_source));
  SET p_status = 'completed';
END;
```

### Calling Procedures

```sql
-- Positional args, ? for OUT params
CALL catalog.schema.proc_name('catalog.schema.staging', 1000, ?, ?);

-- Named args
CALL catalog.schema.proc_name(
  p_source => 'catalog.schema.staging',
  p_batch_size => 1000,
  p_rows_affected => ?,
  p_status => ?
);
```

### SQL SECURITY

| Mode | Behavior | Use Case |
|------|----------|----------|
| `INVOKER` | Runs with caller's permissions | Default, recommended for most cases |
| `DEFINER` | Runs with creator's permissions | Controlled data access patterns |

### identifier() for Dynamic Table Names

```sql
-- Safely reference tables from parameters
SELECT * FROM identifier(p_table_name);
INSERT INTO identifier(p_target) SELECT * FROM identifier(p_source);
```

---

## EXECUTE IMMEDIATE

Dynamic SQL construction and execution.

```sql
-- Simple
EXECUTE IMMEDIATE 'SELECT COUNT(*) FROM ' || v_table_name;

-- With parameters (USING clause)
EXECUTE IMMEDIATE
  'INSERT INTO log_table VALUES (?, ?, current_timestamp())'
  USING v_job_id, v_status;

-- INTO clause for results
DECLARE v_result BIGINT;
EXECUTE IMMEDIATE
  'SELECT COUNT(*) FROM identifier(?)'
  INTO v_result
  USING v_table_name;
```

**Gotcha:** `EXECUTE IMMEDIATE` cannot use `identifier()` — pass the full table name as a string or use parameterized `?` placeholders.

---

## Recursive CTEs

**Availability:** DBR 17.0+ / DBSQL

```sql
WITH RECURSIVE hierarchy AS (
  -- Anchor member (base case)
  SELECT id, parent_id, name, 0 AS depth, ARRAY(name) AS path
  FROM catalog.schema.categories
  WHERE parent_id IS NULL

  UNION ALL

  -- Recursive member
  SELECT c.id, c.parent_id, c.name, h.depth + 1, array_append(h.path, c.name)
  FROM catalog.schema.categories c
  JOIN hierarchy h ON c.parent_id = h.id
  WHERE h.depth < 20  -- ALWAYS add a depth guard
)
SELECT * FROM hierarchy ORDER BY depth, name;
```

**Rules and gotchas:**

| Rule | Detail |
|------|--------|
| Must use `UNION ALL` | `UNION` (dedup) not supported in recursive member |
| Anchor first | Anchor member must be the first SELECT |
| No aggregation | Recursive member cannot use GROUP BY, DISTINCT, aggregate functions |
| No window functions | Not allowed in recursive member |
| Depth guard required | Always add `WHERE depth < N` to prevent infinite recursion |
| Default limit | 10,000 iterations max (configurable via `spark.sql.cte.recursion.limit`) |
| Self-reference once | Recursive member can reference the CTE name exactly once |

### Common Patterns

**Bill of Materials (BOM) explosion:**
```sql
WITH RECURSIVE bom AS (
  SELECT part_id, part_name, 1 AS quantity, 0 AS level
  FROM parts WHERE part_id = 'FINAL_ASSEMBLY'
  UNION ALL
  SELECT c.component_id, c.component_name, b.quantity * c.quantity, b.level + 1
  FROM bom b JOIN components c ON b.part_id = c.parent_id
  WHERE b.level < 15
)
SELECT part_id, part_name, SUM(quantity) AS total_needed
FROM bom GROUP BY part_id, part_name;
```

**Date spine generation:**
```sql
WITH RECURSIVE dates AS (
  SELECT DATE'2024-01-01' AS dt
  UNION ALL
  SELECT dateadd(DAY, 1, dt) FROM dates WHERE dt < DATE'2024-12-31'
)
SELECT * FROM dates;
```

---

## Multi-Statement Transactions

**Status:** Preview (serverless SQL warehouses)

### BEGIN ATOMIC

```sql
BEGIN ATOMIC
  DELETE FROM catalog.schema.orders WHERE status = 'cancelled';
  INSERT INTO catalog.schema.archive
    SELECT * FROM catalog.schema.orders WHERE status = 'cancelled';
  UPDATE catalog.schema.order_summary
    SET last_cleanup = current_timestamp();
END;
```

All statements succeed or all roll back. No partial commits.

**Limitations:**

| Limitation | Detail |
|-----------|--------|
| Serverless only | Not available on classic/pro warehouses |
| Preview feature | May change; enable via workspace admin |
| No DDL inside | Only DML (INSERT/UPDATE/DELETE/MERGE) supported |
| Same catalog | All tables must be in the same Unity Catalog catalog |
| No streaming | Cannot use with streaming tables |
| Timeout | Long-running transactions may be aborted |

---

## Gotchas

- **Temp views don't persist across `execute_sql` calls** -- each MCP `execute_sql` is a separate session. Use CTEs or inline subqueries instead when running via MCP/serverless.
- **Variable names** can shadow column names -- prefix with `v_` to avoid ambiguity.
- **DECLARE must come first** in a compound block, before any executable statements.
- **FOR loop variable** is read-only -- you cannot SET columns of the loop variable.
- **Nested BEGIN...END** blocks create new variable scopes. Inner blocks can see outer variables but not vice versa.
- **CALL with OUT params** requires `?` placeholder in DBSQL editor; in notebooks you can capture results directly.
- **identifier()** only works with fully qualified names (`catalog.schema.table`).
