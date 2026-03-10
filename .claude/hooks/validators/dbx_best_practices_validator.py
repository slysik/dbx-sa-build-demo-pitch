#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Databricks Best Practices Validator for Claude Code PostToolUse Hook

Warning-mode hook that scans .py/.sql files for dbx-best-practices.md violations.
Each warning includes the suggested fix so Claude self-corrects in one iteration.

Outputs JSON for Claude Code PostToolUse hook:
- {"decision": "block", "reason": "..."} to block (NOT USED — warning mode only)
- Warnings via output_additional_context() pattern
- {} to allow completion
"""
import json
import logging
import re
import sys
from pathlib import Path

# Logging setup
SCRIPT_DIR = Path(__file__).parent
LOG_FILE = SCRIPT_DIR / "dbx_best_practices_validator.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(LOG_FILE, mode='a')]
)
logger = logging.getLogger(__name__)

# ── Money column patterns ────────────────────────────────────────────────────
MONEY_COLS = r'(?:amount|price|revenue|cost|balance|fee|total|salary|income|payment)'
FLOAT_MONEY_SQL = re.compile(
    rf'(?:FLOAT|DOUBLE)\b.*\b{MONEY_COLS}\b|'
    rf'\b{MONEY_COLS}\b.*\b(?:FLOAT|DOUBLE)\b',
    re.IGNORECASE
)
FLOAT_MONEY_PY = re.compile(
    rf'DoubleType\s*\(.*{MONEY_COLS}|'
    rf'FloatType\s*\(.*{MONEY_COLS}|'
    rf'{MONEY_COLS}.*DoubleType|'
    rf'{MONEY_COLS}.*FloatType',
    re.IGNORECASE
)

# ── Rule patterns ────────────────────────────────────────────────────────────
MERGE_PATTERN = re.compile(r'\bMERGE\s+INTO\b', re.IGNORECASE)
ROW_NUMBER_PATTERN = re.compile(r'\bROW_NUMBER\s*\(', re.IGNORECASE)

CREATE_TABLE_PATTERN = re.compile(r'\bCREATE\s+(?:OR\s+REPLACE\s+)?TABLE\b', re.IGNORECASE)
CHECK_CONSTRAINT_PATTERN = re.compile(r'\b(?:ADD\s+CONSTRAINT|CHECK\s*\()', re.IGNORECASE)
CLUSTER_BY_PATTERN = re.compile(r'\bCLUSTER\s+BY\b', re.IGNORECASE)

OVERWRITE_PATTERN = re.compile(r'mode\s*\(\s*["\']overwrite["\']\s*\)', re.IGNORECASE)

INSERT_OR_MERGE = re.compile(r'\b(?:MERGE\s+INTO|INSERT\s+INTO)\b', re.IGNORECASE)
VALIDATION_PATTERN = re.compile(r'\b(?:count\s*\(\s*\*\s*\)|HAVING)\b', re.IGNORECASE)

# Rule 8: SET * in MERGE (pulls extra columns like rn)
MERGE_SET_STAR = re.compile(r'\bUPDATE\s+SET\s+\*', re.IGNORECASE)

# Rule 9: Unqualified table names (missing catalog.schema prefix)
# Matches CREATE TABLE / INSERT INTO / MERGE INTO / FROM / JOIN with a simple identifier (no dots)
UNQUALIFIED_TABLE = re.compile(
    r'\b(?:CREATE\s+(?:OR\s+REPLACE\s+)?TABLE|INSERT\s+INTO|MERGE\s+INTO|FROM|JOIN)\s+'
    r'(?:IF\s+NOT\s+EXISTS\s+)?'
    r'([a-zA-Z_]\w*)\b'
    r'(?!\s*\.)',  # NOT followed by a dot
    re.IGNORECASE
)
# Tables that are OK unqualified (temp views, CTEs, aliases)
TEMP_VIEW_KEYWORDS = {'temp', 'temporary', 'v_', 'cte_', 'src', 'tgt', 'lateral'}

SQL_BLOCK_COMMENT = re.compile(r'--')


def check_decimal_for_money(content: str, is_sql: bool) -> str | None:
    """Rule 1: DECIMAL for money columns."""
    pattern = FLOAT_MONEY_SQL if is_sql else FLOAT_MONEY_PY
    if pattern.search(content):
        return (
            "[Rule 1] FLOAT/DOUBLE used for monetary column. "
            "Fix: Use DECIMAL(18,2) — e.g. CAST(amount AS DECIMAL(18,2)). "
            "FLOAT introduces rounding errors ($19.99 → $19.98999...)."
        )
    return None


def check_row_number_before_merge(content: str) -> str | None:
    """Rule 2: ROW_NUMBER before MERGE."""
    if MERGE_PATTERN.search(content) and not ROW_NUMBER_PATTERN.search(content):
        return (
            "[Rule 2] MERGE INTO without ROW_NUMBER dedup. "
            "Fix: Add staging view:\n"
            "  CREATE OR REPLACE TEMP VIEW v_latest AS\n"
            "  SELECT *, ROW_NUMBER() OVER (PARTITION BY <key> ORDER BY <ts> DESC) AS rn\n"
            "  FROM <source> WHERE rn = 1;\n"
            "Then MERGE from v_latest instead of raw source."
        )
    return None


def check_constraints(content: str) -> str | None:
    """Rule 3: CHECK constraints after CREATE TABLE."""
    if CREATE_TABLE_PATTERN.search(content) and not CHECK_CONSTRAINT_PATTERN.search(content):
        return (
            "[Rule 3] CREATE TABLE without CHECK constraints. "
            "Fix: Add after DDL:\n"
            "  ALTER TABLE <t> ADD CONSTRAINT chk_<col> CHECK (<col> IS NULL OR <col> >= 0);\n"
            "Constraints enforce data quality at the storage layer."
        )
    return None


def check_liquid_clustering(content: str) -> str | None:
    """Rule 4: Liquid Clustering after CREATE TABLE."""
    if CREATE_TABLE_PATTERN.search(content) and not CLUSTER_BY_PATTERN.search(content):
        return (
            "[Rule 4] CREATE TABLE without CLUSTER BY. "
            "Fix: Add after DDL:\n"
            "  ALTER TABLE <t> CLUSTER BY (<key>, <date>);\n"
            "  OPTIMIZE <t>;\n"
            "  ANALYZE TABLE <t> COMPUTE STATISTICS FOR ALL COLUMNS;\n"
            "Liquid Clustering replaces partitioning + Z-ORDER."
        )
    return None


def check_gold_overwrite(content: str) -> str | None:
    """Rule 5: No full overwrite for Gold tables."""
    if OVERWRITE_PATTERN.search(content):
        return (
            "[Rule 5] mode('overwrite') detected — use window rebuild instead. "
            "Fix: Replace with:\n"
            "  DELETE FROM <gold> WHERE date >= date_sub(current_date(), 14);\n"
            "  INSERT INTO <gold> SELECT ... WHERE date >= date_sub(current_date(), 14);\n"
            "Overwrite rewrites 100% of data for a 1% change."
        )
    return None


def check_validation_harness(content: str) -> str | None:
    """Rule 6: Validation harness when doing MERGE/INSERT."""
    if INSERT_OR_MERGE.search(content) and not VALIDATION_PATTERN.search(content):
        return (
            "[Rule 6] MERGE/INSERT without validation harness. "
            "Fix: Add final cells with:\n"
            "  - Row counts across layers: SELECT count(*) FROM each table\n"
            "  - Uniqueness check: GROUP BY pk HAVING count(*) > 1\n"
            "  - Rule violation counts (negative amounts, bad enums)\n"
            "  - Pruning-friendly query (filters match CLUSTER BY keys)"
        )
    return None


def check_narration_comments(content: str, is_sql: bool) -> str | None:
    """Rule 7: SQL blocks >5 lines should have comments."""
    if not is_sql:
        # For .py files, check SQL blocks inside triple-quoted strings or MAGIC %sql
        sql_sections = re.findall(
            r'(?:# MAGIC %sql\n)((?:# MAGIC .*\n){6,})',
            content
        )
        for section in sql_sections:
            lines = section.strip().split('\n')
            has_comment = any('--' in line for line in lines)
            if not has_comment:
                return (
                    "[Rule 7] SQL block >5 lines without narration comments. "
                    "Fix: Add -- comments explaining WHAT and WHY. "
                    "The interviewer grades 'Think Out Loud' — comments ARE your narration script."
                )
        return None

    # For .sql files, check consecutive non-comment, non-blank lines
    lines = content.split('\n')
    consecutive_code = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            consecutive_code = 0
            continue
        if stripped.startswith('--'):
            consecutive_code = 0
            continue
        consecutive_code += 1
        if consecutive_code > 5:
            return (
                "[Rule 7] SQL block >5 lines without narration comments. "
                "Fix: Add -- comments explaining WHAT and WHY. "
                "The interviewer grades 'Think Out Loud' — comments ARE your narration script."
            )
    return None


def check_merge_set_star(content: str) -> str | None:
    """Rule 8: No SET * in MERGE — pulls extra columns like rn."""
    if MERGE_PATTERN.search(content) and MERGE_SET_STAR.search(content):
        return (
            "[Rule 8] MERGE with UPDATE SET * — this pulls extra columns (e.g. rn from ROW_NUMBER). "
            "Fix: Use explicit column list:\n"
            "  WHEN MATCHED THEN UPDATE SET\n"
            "    t.col1 = s.col1, t.col2 = s.col2, ...\n"
            "  WHEN NOT MATCHED THEN INSERT (col1, col2, ...)\n"
            "    VALUES (s.col1, s.col2, ...)"
        )
    return None


def check_unqualified_tables(content: str) -> str | None:
    """Rule 9: Fully qualify table names as catalog.schema.table."""
    matches = UNQUALIFIED_TABLE.findall(content)
    # Filter out known OK names (temp views, aliases, keywords)
    suspect = []
    sql_keywords = {
        'select', 'from', 'where', 'table', 'view', 'as', 'on', 'set',
        'into', 'values', 'group', 'order', 'having', 'limit', 'union',
        'exists', 'not', 'and', 'or', 'in', 'is', 'null', 'case', 'when',
        'then', 'else', 'end', 'between', 'like', 'all', 'any', 'true',
        'false', 'current_timestamp', 'current_date', 'dual',
    }
    for name in matches:
        lower = name.lower()
        if lower in sql_keywords:
            continue
        if any(lower.startswith(prefix) for prefix in TEMP_VIEW_KEYWORDS):
            continue
        if len(lower) <= 2:  # aliases like t, s
            continue
        suspect.append(name)
    if suspect:
        examples = ', '.join(suspect[:3])
        return (
            f"[Rule 9] Unqualified table name(s): {examples}. "
            "Fix: Use fully qualified names: catalog.schema.table. "
            "Serverless SQL has no default catalog — unqualified names will fail."
        )
    return None


def check_pipeline_completeness(content: str) -> str | None:
    """Rule 10: Pipeline that mentions bronze+silver+gold should have validation harness."""
    content_lower = content.lower()
    has_bronze = 'bronze' in content_lower
    has_silver = 'silver' in content_lower
    has_gold = 'gold' in content_lower
    has_harness = 'validation harness' in content_lower or 'VALIDATION HARNESS' in content

    if has_bronze and has_silver and has_gold and not has_harness:
        return (
            "[Rule 10] Pipeline mentions bronze/silver/gold but missing VALIDATION HARNESS section. "
            "Fix: Add final cells with:\n"
            "  -- VALIDATION HARNESS\n"
            "  -- A) Row counts: SELECT count(*) FROM each layer\n"
            "  -- B) Uniqueness: GROUP BY pk HAVING count(*)>1\n"
            "  -- C) Rule violations: negative amounts, bad enums\n"
            "  -- D) Pruning query: filters match CLUSTER BY keys"
        )
    return None


def validate(file_path: str, content: str) -> list[str]:
    """Run all rules against file content. Returns list of warnings."""
    is_sql = file_path.endswith('.sql')
    warnings = []

    checks = [
        check_decimal_for_money(content, is_sql),
        check_row_number_before_merge(content),
        check_constraints(content),
        check_liquid_clustering(content),
        check_gold_overwrite(content),
        check_validation_harness(content),
        check_narration_comments(content, is_sql),
        check_merge_set_star(content),
        check_unqualified_tables(content),
        check_pipeline_completeness(content),
    ]

    for result in checks:
        if result:
            warnings.append(result)

    return warnings


def main():
    logger.info("=" * 50)
    logger.info("DBX BEST PRACTICES VALIDATOR TRIGGERED")

    # Read hook input from stdin
    try:
        stdin_data = sys.stdin.read()
        if stdin_data.strip():
            hook_input = json.loads(stdin_data)
            logger.info(f"hook_input keys: {list(hook_input.keys())}")
        else:
            hook_input = {}
    except json.JSONDecodeError:
        hook_input = {}

    # Extract file_path from PostToolUse input
    file_path = hook_input.get("tool_input", {}).get("file_path", "")
    logger.info(f"file_path: {file_path}")

    # Only run for .py and .sql files
    if not (file_path.endswith(".py") or file_path.endswith(".sql")):
        logger.info("Skipping non-Python/SQL file")
        print(json.dumps({}))
        return

    # Read file content
    try:
        content = Path(file_path).read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError) as e:
        logger.info(f"Cannot read file: {e}")
        print(json.dumps({}))
        return

    # Run all checks
    warnings = validate(file_path, content)

    if not warnings:
        logger.info("RESULT: PASS — no best-practice violations")
        print(json.dumps({}))
        return

    # Warning mode: output as additional context (never block)
    warning_text = (
        f"⚠ dbx-best-practices violations in {Path(file_path).name}:\n\n"
        + "\n\n".join(warnings)
        + "\n\nFix these before proceeding. See dbx-best-practices.md for full templates."
    )

    logger.info(f"RESULT: {len(warnings)} warning(s)")
    for w in warnings:
        logger.info(f"  {w[:80]}...")

    # Output as additional_context (warning, not block)
    print(json.dumps({
        "decision": "warn",
        "reason": warning_text
    }))


if __name__ == "__main__":
    main()
