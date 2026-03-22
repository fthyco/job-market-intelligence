# Job Market Intelligence Platform — Project Structure

```
job_market_intelligence/
│
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Makefile
│
├── config/
│   ├── __init__.py
│   ├── settings.py                  # Central config (env vars, paths, constants)
│   └── logging_config.py
│
├── data/
│   ├── raw/                         # Raw Kaggle datasets + Upwork scraping output
│   │   ├── kaggle/
│   │   │   ├── linkedin_jobs.csv
│   │   │   ├── data_scientist_jobs.csv
│   │   │   ├── job_descriptions.csv
│   │   │   ├── ds_salaries.csv
│   │   │   └── tech_skills.csv
│   │   └── upwork/
│   │       └── upwork_jobs.csv
│   ├── processed/                   # Cleaned, validated data
│   ├── lake/                        # Delta Lake storage (raw + curated layers)
│   │   ├── raw/
│   │   └── curated/
│   └── warehouse/                   # Serving layer exports / backups
│
├── notebooks/
│   ├── 01_eda_kaggle_data.ipynb
│   ├── 02_eda_upwork_data.ipynb
│   ├── 03_skills_analysis.ipynb
│   ├── 04_salary_distributions.ipynb
│   ├── 05_generator_calibration.ipynb
│   └── 06_recommender_experiments.ipynb
│
├── src/
│   │
│   ├── ingestion/                   # Layer 1 — Knowledge Base Building
│   │   ├── __init__.py
│   │   ├── kaggle_loader.py         # Load + validate Kaggle datasets
│   │   ├── upwork_loader.py         # Load + validate Upwork scraping data
│   │   └── schema_validator.py      # Pydantic schemas for raw data
│   │
│   ├── knowledge/                   # Layer 1 Output — Market Knowledge Base
│   │   ├── __init__.py
│   │   ├── skills_extractor.py      # Extract + normalize skills from descriptions
│   │   ├── salary_analyzer.py       # Build salary distributions per role/skill
│   │   ├── job_templates.py         # Build job archetypes from clustering
│   │   ├── catalog_builder.py       # Build skills_catalog + tools_catalog
│   │   └── artifacts/               # Saved knowledge base artifacts
│   │       ├── skills_catalog.json
│   │       ├── tools_catalog.json
│   │       ├── salary_distributions.json
│   │       └── job_templates.json
│   │
│   ├── generator/                   # Layer 2 — Market Simulator
│   │   ├── __init__.py
│   │   ├── distributions.py         # Load + wrap statistical distributions
│   │   ├── job_generator.py         # Core generator logic (batch + streaming)
│   │   ├── batch_runner.py          # CLI entry for batch generation
│   │   ├── stream_runner.py         # Continuous event emission to Kafka
│   │   └── schemas.py               # JobPosting Pydantic model
│   │
│   ├── streaming/                   # Layer 2 Infrastructure — Kafka
│   │   ├── __init__.py
│   │   ├── producer.py              # Kafka producer wrapper
│   │   ├── consumer.py              # Kafka consumer wrapper
│   │   └── topics.py                # Topic names + config constants
│   │
│   ├── pipeline/                    # Layer 3 — Data Processing
│   │   ├── __init__.py
│   │   ├── validator.py             # Schema + quality checks on incoming events
│   │   ├── cleaner.py               # Normalization, dedup, null handling
│   │   ├── feature_extractor.py     # Feature engineering for ML
│   │   ├── lake_writer.py           # Write to Delta Lake (raw + curated)
│   │   └── warehouse_loader.py      # Load into PostgreSQL dim/fact tables
│   │
│   ├── warehouse/                   # Layer 3 Output — Data Warehouse
│   │   ├── __init__.py
│   │   ├── models.py                # SQLAlchemy ORM models
│   │   │                            #   dim_skills, dim_companies,
│   │   │                            #   dim_locations, fact_jobs
│   │   ├── migrations/
│   │   │   └── init_schema.sql
│   │   └── queries.py               # Reusable analytical queries
│   │
│   ├── ml/                          # Layer 4 — Models
│   │   ├── __init__.py
│   │   ├── embeddings/
│   │   │   ├── skill_embedder.py    # Train/load skill embeddings (Word2Vec/FastText)
│   │   │   └── job_embedder.py      # Embed job descriptions (sentence-transformers)
│   │   ├── recommender/
│   │   │   ├── trainer.py           # Training loop + MLflow logging
│   │   │   ├── model.py             # Recommender model class (pyfunc wrapper)
│   │   │   ├── vector_index.py      # FAISS index build + query
│   │   │   └── evaluator.py         # Precision@K, recall metrics
│   │   └── registry.py              # MLflow model registry helpers
│   │
│   ├── api/                         # Layer 5 — Serving
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app entry
│   │   ├── dependencies.py          # Shared deps (DB session, model loader)
│   │   ├── routers/
│   │   │   ├── recommendations.py   # POST /recommend — input skills → jobs
│   │   │   ├── skills.py            # GET /skills/trending
│   │   │   ├── market.py            # GET /market/trends
│   │   │   └── health.py            # GET /health
│   │   └── schemas.py               # Request/Response Pydantic models
│   │
│   └── dashboard/                   # Layer 5 — UI
│       ├── app.py                   # Streamlit or Dash entry point
│       ├── pages/
│       │   ├── job_recommendations.py
│       │   ├── skill_trends.py
│       │   └── market_overview.py
│       └── components/
│           ├── charts.py
│           └── filters.py
│
├── airflow/                         # Layer 6 — Orchestration
│   ├── dags/
│   │   ├── knowledge_base_dag.py    # One-time: build knowledge base from raw data
│   │   ├── batch_generation_dag.py  # Scheduled: generate batch jobs
│   │   ├── pipeline_dag.py          # Scheduled: validate → clean → load
│   │   └── model_retrain_dag.py     # Scheduled: retrain + promote model
│   └── plugins/
│       └── operators/
│           └── delta_lake_operator.py
│
├── infrastructure/                  # Layer 6 — Docker + Config
│   ├── docker/
│   │   ├── api.Dockerfile
│   │   ├── airflow.Dockerfile
│   │   └── dashboard.Dockerfile
│   ├── kafka/
│   │   └── server.properties
│   ├── mlflow/
│   │   └── mlflow.Dockerfile
│   └── postgres/
│       └── init.sql
│
└── tests/
    ├── unit/
    │   ├── test_generator.py
    │   ├── test_validator.py
    │   ├── test_skills_extractor.py
    │   └── test_recommender.py
    ├── integration/
    │   ├── test_kafka_pipeline.py
    │   ├── test_warehouse_loader.py
    │   └── test_api_endpoints.py
    └── conftest.py
```

---

## Data Flow Map

```
data/raw/
    └── [Kaggle + Upwork CSVs]
         │
         ▼
src/ingestion/         → load + validate raw data
         │
         ▼
src/knowledge/         → build skills_catalog, salary_distributions, job_templates
         │
         ▼
src/generator/         → batch_runner.py  →  data/processed/
                       → stream_runner.py →  Kafka topic: job_events
                                                    │
                                                    ▼
                                         src/pipeline/validator.py
                                                    │
                                                    ▼
                                         src/pipeline/cleaner.py
                                                    │
                                         ┌──────────┴──────────┐
                                         ▼                     ▼
                               lake_writer.py         warehouse_loader.py
                               data/lake/             PostgreSQL
                               (Delta format)         dim_skills
                                                       dim_companies
                                                       dim_locations
                                                       fact_jobs
                                                            │
                                                            ▼
                                                   src/ml/recommender/
                                                   trainer.py → MLflow
                                                            │
                                                            ▼
                                                   src/api/main.py (FastAPI)
                                                            │
                                                            ▼
                                                   src/dashboard/app.py
```

---

## Docker Compose Services

| Service        | Port  | Purpose                        |
|----------------|-------|--------------------------------|
| kafka          | 9092  | Event streaming                |
| zookeeper      | 2181  | Kafka coordination             |
| postgres       | 5432  | Warehouse + MLflow backend     |
| minio          | 9000  | Artifact store (Delta + MLflow)|
| mlflow         | 5000  | Experiment tracking + registry |
| airflow        | 8080  | Pipeline orchestration         |
| api            | 8000  | FastAPI serving                |
| dashboard      | 8501  | Streamlit UI                   |

---

## Execution Order (First Run)

```
1. docker-compose up
2. make init-db               # run postgres/init.sql
3. make build-knowledge-base  # src/knowledge/ pipeline on raw data
4. make generate-batch        # produce historical job records
5. make run-pipeline-batch    # validate → clean → load warehouse
6. make train-model           # train recommender, log to MLflow
7. make promote-model         # push best run to Production in registry
8. make start-streaming       # stream_runner → Kafka → pipeline live
```
