# dbx-sa-build-demo-pitch
## AI-Native Customer Intelligence Platform — End-to-End Databricks Demo

> **Scenario**: A retail company wants to harness AI to understand customer sentiment, predict churn, and generate personalised recommendations — all built end-to-end on Databricks using the Lakehouse architecture and the Databricks AI/ML stack.

---

## 🚀 What This Demo Shows

| Stage | What You'll See |
|---|---|
| **Data Ingestion** | Landing raw customer & review data into Delta Lake (Bronze → Silver → Gold) |
| **AI Analysis** | LLM-powered sentiment classification using Databricks Foundation Model APIs |
| **ML Training** | Churn-prediction model trained with AutoML, tracked in MLflow |
| **Model Serving** | One-click deployment to a Databricks Model Serving endpoint |
| **Personalisation** | Real-time recommendation scoring via the serving endpoint |

---

## 📂 Repository Structure

```
.
├── README.md
├── config/
│   └── demo_config.yml          # Centralised configuration (catalog, schema, endpoints…)
├── notebooks/
│   ├── 01_setup.py              # Workspace bootstrapping – catalogs, schemas, sample data
│   ├── 02_data_ingestion.py     # Bronze/Silver/Gold Delta Lake pipeline
│   ├── 03_ai_analysis.py        # LLM sentiment analysis via Foundation Model APIs
│   ├── 04_ml_training.py        # AutoML churn model + MLflow experiment tracking
│   └── 05_model_serving.py      # Register, deploy and query a Model Serving endpoint
├── src/
│   └── utils.py                 # Shared helper functions
└── tests/
    └── test_utils.py            # Unit tests for utility functions
```

---

## ⚡ Quick Start

### Prerequisites

- Databricks workspace (DBR 14.3 LTS or above recommended)
- Unity Catalog enabled
- Access to Databricks Foundation Model APIs (DBRX / Llama-3 or similar)
- A cluster with at least 8 GB memory

### 1 — Clone / import into Databricks

```bash
# From a Databricks terminal or via Repos
git clone https://github.com/slysik/dbx-sa-build-demo-pitch.git
```

Or use **Workspace → Repos → Add Repo** and paste the URL above.

### 2 — Review configuration

Edit `config/demo_config.yml` to match your workspace:

```yaml
catalog: main               # Unity Catalog name
schema: customer_intel      # Schema / database name
volume: raw_data            # UC Volume for file uploads
model_name: churn_predictor # Registered model name
serving_endpoint: churn_ep  # Model Serving endpoint name
llm_endpoint: databricks-dbrx-instruct  # Foundation Model endpoint
```

### 3 — Run the notebooks in order

```
01_setup.py           →  bootstrap workspace objects
02_data_ingestion.py  →  build the Delta Lakehouse pipeline
03_ai_analysis.py     →  run LLM sentiment enrichment
04_ml_training.py     →  train & log the churn model
05_model_serving.py   →  deploy and query the endpoint
```

---

## 🏗 Architecture

```
                   ┌─────────────────────────────────────────────────────┐
                   │                  Databricks Lakehouse                │
                   │                                                       │
  Raw CSVs ──────► │  Bronze (Delta)  ──►  Silver (Delta)  ──►  Gold     │
                   │                                                       │
                   │  Foundation Model APIs                                │
                   │       │  LLM Sentiment                                │
                   │       ▼                                               │
                   │  Gold (enriched) ──►  MLflow AutoML  ──►  Model      │
                   │                             │           Registry     │
                   │                             ▼                        │
                   │                    Model Serving Endpoint            │
                   │                             │                        │
                   │                             ▼                        │
                   │                    Real-time Inference               │
                   └─────────────────────────────────────────────────────┘
```

---

## 🧩 Key Databricks Features Demonstrated

- **Unity Catalog** — governed data and model assets
- **Delta Lake** — ACID transactions, time-travel, schema evolution
- **Databricks Foundation Model APIs** — zero-infrastructure LLM inference
- **MLflow** — experiment tracking, model registry, deployment
- **Databricks AutoML** — automated feature engineering and model selection
- **Model Serving** — serverless real-time inference endpoints
- **Databricks Notebooks** — reproducible, parameterised workflows

---

## 🧪 Running Tests

```bash
pip install pytest
pytest tests/
```

---

## �� License

Apache 2.0 — see [LICENSE](LICENSE) for details.
