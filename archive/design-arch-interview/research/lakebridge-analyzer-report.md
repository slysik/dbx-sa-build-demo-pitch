# Databricks Lakebridge Analyzer: What It Outputs

## Research Task
Determine what Databricks Lakebridge Analyzer actually outputs -- its reports, metrics, complexity categories, supported source systems, and how it differs from the Lakebridge Converter.

## Summary

Lakebridge Analyzer is the **assessment/profiling component** of Databricks' free, open-source Lakebridge migration toolkit (formerly BladeBridge, acquired 2024, relaunched as Lakebridge June 2025). It scans **exported** SQL code and ETL metadata (it does NOT connect directly to source databases) and produces a multi-tab **Excel report (.xlsx)** -- optionally with a companion JSON file -- that inventories all migration objects, classifies them by complexity (Low / Medium / Complex / Very Complex), and maps interdependencies. These metrics feed into a **Conversion Calculator** to estimate engineering hours and licensing costs.

## Detailed Findings

### 1. What Is Lakebridge Analyzer?

Lakebridge Analyzer is one of two tools in the **Assessment phase** of the Lakebridge migration workflow (the other being the Profiler)<sup>[1](#Sources)</sup>. It is a static code/metadata scanner -- you export SQL files, ETL repository XMLs, or orchestration definitions from your legacy system and point the Analyzer at them<sup>[2](#Sources)</sup>. It does **not** connect to live databases; that is the Profiler's role<sup>[3](#Sources)</sup>.

The Analyzer was originally part of the **BladeBridge** product, which Databricks acquired in early 2024<sup>[4](#Sources)</sup>. It was combined with the open-source **Remorph** SQL transpiler and relaunched as **Lakebridge** in June 2025<sup>[5](#Sources)</sup>.

### 2. Lakebridge Component Breakdown

| Component | Phase | Purpose |
|-----------|-------|---------|
| **Profiler** | Assessment | Connects to source DB to examine workloads, size, feature usage; estimates TCO savings |
| **Analyzer** | Assessment | Scans exported code/metadata; generates complexity report and object inventory |
| **BladeBridge Transpiler** | Conversion | Mature rule-based SQL transpiler; handles 20+ dialects + some ETL |
| **Morpheus Transpiler** | Conversion | Next-gen transpiler with experimental dbt support |
| **Switch Transpiler** | Conversion | LLM-powered converter producing Databricks notebooks |
| **Reconciler** | Reconciliation | Validates source-to-target data accuracy post-migration |

Source: Lakebridge Overview documentation<sup>[1](#Sources)</sup>

### 3. Specific Outputs / Report Format

The Analyzer generates two output types<sup>[2](#Sources)</sup>:

- **Excel Report (.xlsx)** -- always produced; multi-tab workbook with formatted analysis
- **JSON Report (.json)** -- optional, triggered via `--generate-json true`; same filename as xlsx, for programmatic consumption

### 4. Excel Report Tabs (Documented for Snowflake Source)

The following 13 tabs have been documented for a Snowflake-to-Databricks analysis<sup>[6](#Sources)</sup><sup>[7](#Sources)</sup>:

| Tab Name | Contents |
|----------|----------|
| **Summary** | High-level counts: total scripts, tables, views, lines of code, stored procedures, functions; overall complexity indication |
| **SQL Programs** | Inventory of all SQL programs/scripts discovered |
| **SQL Script Categories** | Classification of SQL statements by type (DDL, DML, etc.) |
| **UNKNOWN SQL category** | SQL statements the parser could not categorize |
| **SQL SubJobInfo** | Sub-job and sub-task details within larger workflows |
| **SQL Special Patterns** | Detection of loops, cursors, dynamic SQL, and other patterns requiring special handling |
| **Functions** | Complete inventory of all functions found |
| **Functions By Script** | Function usage broken down per script file |
| **Scripts Function XREF** | Cross-reference matrix: which scripts call which functions |
| **Referenced Objects** | All database objects (tables, views, etc.) referenced across the codebase |
| **Program-Object XREF** | Cross-reference: which programs touch which database objects |
| **Raw Program PARAM list** | Parameter lists for stored procedures and programs |
| **SQL data types** | Inventory of all data types used across the codebase |

### 5. Three Core Assessment Dimensions

The Analyzer delivers three categories of insight<sup>[2](#Sources)</sup>:

1. **Job Complexity Assessment** -- Quantified complexity scores (Low / Medium / Complex / Very Complex) for each job/script, used to estimate migration effort and cost<sup>[8](#Sources)</sup>
2. **Comprehensive Job Inventory** -- Full catalog of mappings, programs, transformations, functions, dynamic variables, and database objects<sup>[2](#Sources)</sup>
3. **Cross-System Interdependency Mapping** -- Dependency graphs showing relationships between jobs, systems, and components for migration sequencing<sup>[2](#Sources)</sup>

### 6. Complexity Categories

Workloads are classified into four tiers<sup>[8](#Sources)</sup><sup>[5](#Sources)</sup>:

| Category | Meaning |
|----------|---------|
| **Low** | Simple, straightforward migration; minimal manual intervention |
| **Medium** | Moderate complexity; some patterns needing attention |
| **Complex** | Significant manual effort; special patterns (cursors, dynamic SQL, etc.) |
| **Very Complex** | Highest effort; deep interdependencies, unsupported patterns, heavy refactoring |

Note: The specific scoring algorithms and thresholds that determine these categories are not publicly documented<sup>[3](#Sources)</sup>.

### 7. Conversion Calculator Integration

The Analyzer's complexity metrics feed directly into a **Conversion Calculator** that estimates<sup>[2](#Sources)</sup><sup>[8](#Sources)</sup>:
- Software licensing costs
- Engineering hours required for migration
- Overall project budget and timeline

This enables teams to scope projects accurately, prioritize by business impact, and plan phased migrations<sup>[5](#Sources)</sup>.

### 8. Supported Source Technologies (38 Platforms)

The Analyzer supports the following source technologies<sup>[2](#Sources)</sup><sup>[1](#Sources)</sup>:

**SQL Databases:**
Athena, BigQuery, Greenplum, Hive, IBM DB2, MS SQL Server, MySQL, Netezza, Oracle, PostgreSQL, Presto, Redshift, SAP HANA (CalcViews), Snowflake, Synapse, Teradata, Vertica

**ETL / ELT Tools:**
ABInitio, Alteryx, DataStage, Oracle Data Integrator (ODI), PentahoDI, PIG, PySpark, SAS, SQOOP, SPSS, SSIS, SSRS, Talend

**Orchestration:**
ADF (Azure Data Factory), Oozie

**Other:**
Cloudera (Impala)

### 9. Input Format Requirements

Different source technologies require different export formats<sup>[3](#Sources)</sup>:

| Source Type | Required Input Format |
|-------------|----------------------|
| SQL databases | Exported .sql files (one artifact per file recommended) |
| Informatica PowerCenter | XML workflow exports via `pmrep` commands |
| DataStage | XML project exports |
| SSIS | DTSX package files |
| Talend | Unzipped .item and .properties files |
| Informatica Cloud (IICS/IDMC) | Single zip files preserving directory structure |

### 10. CLI Usage

```bash
databricks labs lakebridge analyze \
  --source-directory /path/to/exported/artifacts \
  --report-file /path/to/output/migration_assessment.xlsx \
  --source-tech snowflake \
  --generate-json true
```

Key parameters<sup>[2](#Sources)</sup>:

| Parameter | Required | Purpose |
|-----------|----------|---------|
| `--source-directory` | Yes* | Path to exported source artifacts |
| `--report-file` | Yes* | Output Excel file path |
| `--source-tech` | Yes* | Source technology identifier |
| `--generate-json` | No | Also produce JSON output |
| `--debug` | No | Enable debug logging |

*If omitted, interactive prompts are triggered.

### 11. Key Limitations

- **No live database connection** -- requires manual export of SQL/metadata from source systems<sup>[9](#Sources)</sup>
- **Structural analysis only** -- no column-level lineage or value-level impact analysis<sup>[9](#Sources)</sup>
- **Scoring algorithm opaque** -- the thresholds for Low/Medium/Complex/Very Complex are not publicly documented<sup>[3](#Sources)</sup>
- **"Lightly documented"** -- some capabilities are described as based on legacy BladeBridge functionality with limited public docs<sup>[9](#Sources)</sup>

### 12. Performance Benchmark

In a documented customer example, the Analyzer processed **3,500+ SQL files in under 9 minutes 30 seconds**<sup>[7](#Sources)</sup>.

## Concerns/Notes

- The Conversion Calculator that consumes Analyzer output appears to be a separate (possibly internal Databricks) tool; its exact interface and availability are not well documented publicly.
- The 13 Excel tabs documented above were specifically observed for a Snowflake source analysis. Tab names and contents may vary for other source technologies (e.g., Informatica/DataStage analyses would likely include ETL-specific tabs for mappings, workflows, and transformations).
- The Profiler (live DB connection) and Analyzer (static code scan) are complementary tools meant to be used together during assessment, but the Analyzer can be run independently.
- Lakebridge is free and open source under the Databricks Labs umbrella (GitHub: databrickslabs/lakebridge, latest release v0.12.2 as of Feb 26, 2026).

## Sources
1. Lakebridge Overview Documentation - https://databrickslabs.github.io/lakebridge/docs/overview/
2. Lakebridge Analyzer Guide - https://databrickslabs.github.io/lakebridge/docs/assessment/analyzer/
3. DeepWiki: Lakebridge Analyzer Technical Deep Dive - https://deepwiki.com/databrickslabs/lakebridge/3.2-analyzer
4. Databricks Blog: Welcoming BladeBridge - https://www.databricks.com/blog/welcoming-bladebridge-databricks-accelerating-data-warehouse-migrations-lakehouse
5. Databricks Blog: Introducing Lakebridge - https://www.databricks.com/blog/introducing-lakebridge-free-open-data-migration-databricks-sql
6. Lakebridge: Snowflake to Databricks Migration in Action (Senthilkumarr) - https://medium.com/@senthilkumarr.ma/lakebridge-snowflake-to-databricks-migration-in-action-e7da6807c66d
7. Intellus Group: Databricks Lakebridge Guide - https://www.intellus.group/databricks-lakebridge-what-is-it-and-how-to-use-it-to-migrate-your-legacy-data-warehouse/
8. Databricks Solutions: Lakebridge Migration Page - https://www.databricks.com/solutions/migration/lakebridge
9. Datafold: Lakebridge vs Datafold Comparison - https://www.datafold.com/blog/lakebridge-alternatives
10. GitHub: databrickslabs/lakebridge - https://github.com/databrickslabs/lakebridge
11. Cubis: Databricks Lakebridge Guide - https://cubis.be/databricks-lakebridge-what-is-it-and-how-to-use-it-to-migrate-your-legacy-data-warehouse/
12. Abylon: Lakebridge from Databricks - https://abylon.io/blog/lakebridge-from-databricks-simpler-and-faster-data-warehouse-migration/
