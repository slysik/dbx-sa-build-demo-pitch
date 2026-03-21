# Databricks SA Interview Project Repo Best Practices Skill

Use this file as the **default operating standard** when generating any Databricks project code. Treat these rules as mandatory unless the human explicitly overrides them.

---

## 1) Primary objective

Build Databricks projects that are:

- easy to review in Git
- modular and testable
- deployable across dev / staging / prod
- aligned to Databricks workspace files, Git folders, and Databricks Asset Bundles
- production-ready for data engineering, analytics, and AI workloads

---

## 2) Core operating model

Follow this model for every project:

- **Git repo = source of truth**
- **Databricks workspace = execution and interactive development surface**
- **Databricks Git folder = workspace view of the repo**
- **Databricks Asset Bundle = deployment unit for jobs, pipelines, dashboards, and related resources**
- **Unity Catalog volumes = location for data files, libraries, build artifacts, and large non-code assets**

Do **not** treat an unmanaged workspace folder as the permanent source of truth for production code.

---

## 3) Repo strategy

Default to **one repo per project / data product / bounded domain**.

Use a **single repo** for code + bundle configuration when:

- the project is small to medium
- Python, SQL, notebooks, and deployment config are tightly coupled
- one team owns the full lifecycle

Use **separate repos** only when clearly justified, such as:

- different teams own application code vs deployment config
- independent release cycles are required
- compiled artifacts must be versioned separately

If separate repos are used, all deployable artifacts must be referenced by **immutable versions** such as Git SHA, semantic version, or both.

---

## 4) Required repository layout

Use this structure unless there is a strong reason to change it:

```text
project-name/
  databricks.yml
  README.md
  .gitignore
  pyproject.toml
  .editorconfig
  .pre-commit-config.yaml

  conf/
    dev/
    stg/
    prod/

  resources/
    jobs/
    pipelines/
    dashboards/
    quality/
    permissions/

  src/
    project_name/
      __init__.py
      config/
      common/
      ingestion/
      bronze/
      silver/
      gold/
      quality/
      orchestration/
      ml/

  sql/
    bronze/
    silver/
    gold/
    serving/

  notebooks/
    demos/
    exploration/
    validation/
    runbooks/

  tests/
    unit/
    integration/

  fixtures/
    sample_data/

  docs/
    architecture.md
    operations.md
    decisions.md

  dist/
```

### Layout rules

- Keep **business logic in `src/`**.
- Keep **declarative SQL in `sql/`**.
- Keep **bundle resource definitions in `resources/`**.
- Keep notebooks thin and purposeful.
- Keep test data tiny.
- Treat `dist/` as generated output, not hand-authored source.

---

## 5) Mandatory code placement rules

### Put code in `src/` when it is:

- reusable across notebooks or jobs
- transformation logic
- utility code
- schema logic
- data quality logic
- shared configuration loading
- client wrappers and helper functions

### Put code in `sql/` when it is:

- a stable SQL transformation
- a view definition
- a semantic layer query
- a medallion-layer SQL step
- dashboard-supporting SQL logic

### Use notebooks only for:

- create synthetic data, generate dataset and write delta to bronze
- debugging
- human-readable runbooks

## 6) Notebook rules

When a notebook is necessary:

- keep it short
- make it readable top to bottom
- call imported functions from `src/` instead of implementing large inline logic
- parameterize inputs with widgets or job parameters only when needed
- include a short header cell with purpose, inputs, outputs, and owner
- avoid hidden side effects

Prefer standard Python imports over cross-notebook code copying.

Avoid using notebooks as a substitute for modules.

Avoid `%run` for reusable production logic when a Python module can be imported instead.

---

## 7) Python / PySpark standards

All generated Python and PySpark code must:

- be organized into small, focused functions
- separate I/O from transformation logic
- avoid hard-coded workspace paths, catalog names, and secrets
- accept config through arguments or environment-aware config objects
- use explicit function names and docstrings where useful
- use type hints where practical
- keep Spark transformations composable
- prefer DataFrame APIs or explicit SQL files over opaque dynamic string generation
- make table names, checkpoints, and target locations configurable

### Spark design rules

- keep transformations deterministic and idempotent
- do not collect large datasets to the driver unless explicitly required
- do not create giant monolithic functions
- do not mix data generation, transformation, and deployment logic in one file
- make write paths and write modes explicit
- enforce schema intentionally; do not rely on accidental inference in production paths

---

## 8) SQL standards

All SQL files must:

- have one clear purpose per file
- use readable formatting
- avoid duplicated business logic across bronze / silver / gold
- keep object naming consistent
- use comments only where they add real value
- separate DDL, transformation SQL, and validation SQL when practical

Use folder names and file names that clearly indicate medallion layer and intent.

Example:

```text
sql/
  bronze/load_orders.sql
  silver/clean_orders.sql
  gold/customer_ltv.sql
```

---

## 9) Databricks Asset Bundle rules

Every production-capable project should be bundle-first.

### Required bundle behaviors

- keep `databricks.yml` at repo root
- keep resources split into logical files under `resources/`
- define environment targets explicitly
- validate bundle config before deployment
- deploy the same project shape across environments
- avoid environment-specific code forks when configuration can solve it

### Environment expectations

At minimum, define:

- `dev`
- `stg` or `qa`
- `prod`

Use configuration and variables for differences across environments, not copied code trees.

---

## 10) Configuration and secrets

### Rules

- never hard-code secrets, tokens, passwords, or private keys
- never hard-code production hosts or sensitive IDs unless clearly required
- read secrets from approved secret management mechanisms
- keep non-secret config in version control
- keep per-environment overrides isolated and minimal

### Configuration priorities

1. job or bundle variables
2. environment-specific config
3. safe defaults for local or dev use

---

## 11) Files, artifacts, and storage rules

### Store in Git / workspace files

- notebooks
- Python source files
- SQL files
- markdown docs
- project-level config files
- small test fixtures only

### Store outside Git, typically in Unity Catalog volumes or artifact storage

- large datasets
- parquet, json, csv, images, and documents used as real data assets
- wheels, jars, and other build artifacts
- generated exports
- large dashboard exports and binaries

Never commit large data dumps or build outputs into the main repo.

---

## 12) Testing requirements

Every project must include tests.

### Minimum expectations

- unit tests for reusable Python logic
- integration tests for critical data flows where practical
- validation queries or checks for major SQL transformations
- smoke tests for deployed jobs or pipelines

### Testing design rules

- design code so pure logic can be tested without a live cluster when possible
- keep fixtures tiny and deterministic
- avoid tests that depend on random ordering unless explicitly handled
- make test names descriptive

No project is complete if logic cannot be validated.

---

## 13) CI/CD rules

Assume this default promotion flow:

1. solution architect / developer works locally or in Databricks workspace through a Git branch
2. changes are committed to a feature branch
3. pull request triggers lint, tests, and bundle validation
4. merge to main triggers deployment to staging
5. staging checks pass
6. deployment promotes to production

### Required CI checks

- code formatting
- linting
- unit tests
- bundle validation
- optional integration tests
- artifact version stamping when relevant

All deployable artifacts must be traceable to a commit.

---

## 14) Branching and Git rules

### Standard branch model

- `main` = deployable trunk
- short-lived feature branches for work in progress
- pull requests required for merge

### Git rules

- keep commits small and reviewable
- do not commit generated secrets or credentials
- do not commit `.ipynb` or notebook outputs from other tools unless intentionally required
- write meaningful commit messages
- prefer atomic PRs that solve one problem well

Keep repo size under control. Do not create a bloated Databricks repo.

---

## 15) Dashboard and SQL analytics assets

If the project includes dashboards:

- version dashboard definitions in source control when supported
- keep supporting SQL in `sql/` rather than embedding large logic blobs only in the UI
- separate semantic logic from presentation choices
- name dashboard resources clearly by domain and audience

---

## 16) Naming conventions

Use consistent snake_case for file names, modules, and most table objects unless platform constraints require otherwise.

### Examples

- `src/project_name/bronze/load_orders.py`
- `resources/jobs/orders_ingestion_job.yml`
- `sql/gold/customer_ltv.sql`
- `notebooks/demos/orders_pipeline_demo.py`

Names must communicate:

- layer
- domain
- purpose
- object type

---

## 17) Documentation requirements

Every repo must include a `README.md` with:

- what the project does
- architecture summary
- how to run locally or in Databricks
- bundle targets and deployment notes
- test commands
- main folders explained

Add `docs/architecture.md` when the project is non-trivial.

Document assumptions and major design decisions.

---

## 18) Anti-patterns to avoid

Do not generate code that does any of the following unless explicitly requested:

- mixes exploration code with production code
- hard-codes catalogs, schemas, volumes, cluster IDs, secrets, or workspace usernames
- duplicates the same transformation in Python and SQL without reason
- stores large source data in the repo
- uses unmanaged workspace folders as the only copy of important code
- creates deeply nested, unclear directory trees
- creates one massive utilities file with unrelated helpers
- creates brittle relative paths without a clear project structure
- relies on manual click-ops instead of source-controlled resources when automation is appropriate
- uses notebook chaining for reusable business logic when modules or jobs are better

---

## 19) Default implementation preference order

When multiple implementation choices are possible, prefer this order:

1. source-controlled files in Git
2. reusable Python modules in `src/`
3. declarative SQL in `sql/`
4. bundle-managed resources in `resources/`
5. thin notebooks for exploration or orchestration
6. manual workspace-only assets only when unavoidable

---

## 20) Definition of done for generated projects

A generated Databricks project is only complete when it includes:

- a clean repo structure
- source-controlled code
- bundle configuration
- environment-aware config
- tests
- documentation
- no obvious secret leakage
- no major logic trapped only in notebooks
- clear separation of code, config, resources, and data assets

---

## 21) Instructions to the coding agent

When building a Databricks project, do the following automatically:

1. create the full repo skeleton first
2. place reusable logic in `src/`
3. place SQL transformations in `sql/`
4. keep notebooks thin and optional
5. create `databricks.yml` and resource files early
6. add tests with at least unit-test scaffolding
7. add a concise but useful `README.md`
8. use placeholders or configuration variables for environment-specific values
9. keep all paths, names, and deployment assumptions explicit
10. favor simplicity, modularity, and production readiness over cleverness

If uncertain, choose the option that is easier to version, test, review, and deploy.

---

## 22) Practical default for most data engineering projects

Unless told otherwise, generate projects with this opinionated default:

- Python + PySpark in `src/`
- SQL transformations in `sql/`
- Databricks Asset Bundles for deployment
- Git folder compatible layout
- Unity Catalog-aware naming
- medallion-oriented folders when relevant
- unit tests from the start
- thin notebooks only for demo, exploration, or operations

This is the preferred baseline.
