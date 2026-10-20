# Orbit Analysis — B2B SaaS Product & Growth Analytics

An end-to-end product analytics and growth intelligence platform modeling **1.45M+ product events** across **100,000 accounts** for a B2B SaaS company. Features a **FastAPI** multi-tenant backend, **React + TypeScript + Vite** dashboard, **DuckDB** SQL pipeline, and **Python** statistical analysis. Originally built from the [SaaS Growth Analytics](https://github.com/supreetha9/saas-growth-analytics) foundation.

> **Portfolio & Demonstration Notice:** All data in this repository is generated synthetically using NumPy and Faker for analytics modeling and portfolio demonstration. It does not represent real customer accounts, proprietary commercial metrics, or measured production systems.

---

## Business Problem & Objectives

A high-velocity B2B SaaS company experiences strong top-of-funnel signup volume but seeks visibility into onboarding friction, customer engagement, and conversion drop-offs. Leadership needs empirical answers to core growth questions:

1. **Funnel Friction:** At which stage of the self-serve onboarding flow do accounts abandon the product, and how do acquisition channels compare?
2. **Feature & Engagement Impact:** Which in-product milestones predict paid subscription conversion versus early churn?
3. **Experimentation (A/B Testing):** Did the Onboarding V2 experience produce a statistically significant increase in 7-day activation?
4. **Cohort Retention:** How does user stickiness decay over a 12-week horizon, and where does retention plateau?
5. **Churn Risk Identification:** Which active accounts exhibit engagement patterns consistent with impending cancellation?

---

## Key Analytical Findings

| Dimension | Finding | Verified Dataset Metric |
| :--- | :--- | :--- |
| **Primary Bottleneck** | Highest drop-off occurs between sending team invites and creating the first project. | **33.2% drop-off** (46.89% → 31.31% step conversion) |
| **Overall Conversion** | Signup-to-paid conversion across the full observation period. | **15.67%** (15,669 of 100,000 signups reach paid) |
| **Top Acquisition Channel** | Referral yields the highest signup-to-paid conversion efficiency. | **18.15%** (vs. Paid Search at 14.39% and 15.67% benchmark) |
| **Onboarding V2 A/B Test** | Statistically significant lift in 7-day workspace activation. | **+3.26 pp absolute lift** (95% CI: [+1.98 pp, +4.54 pp], Z = 4.98, p < 0.001) |
| **Relative Lift** | Percentage improvement over control baseline (67.27% → 70.53%). | **+4.85% relative lift** |
| **Sample Ratio Mismatch** | Chi-square diagnostic test for split integrity (10,095 Control / 9,905 Treatment). | **p = 0.179 (SRM Passed, $\chi^2 = 1.805$)** |
| **Retention Plateau** | Weekly retention stabilizes after initial onboarding decay. | **~36% mature cohort retention plateau at Week 12** |

---

## Tech Stack & Architecture

| Layer | Component | Description |
| :--- | :--- | :--- |
| **API Backend** | FastAPI, Pydantic, Uvicorn | Multi-tenant REST API with JWT authentication, tenant isolation, and versioned endpoints (`/api/v1/`). |
| **Frontend Dashboard** | React 18, TypeScript, Vite | SPA with funnel visualization, cohort retention, experimentation, and churn intelligence views. |
| **Data Generation** | Python 3.13, NumPy, Faker, pyarrow | Generates 100k users, 1.45M events, 100k subscriptions, and 20k experiment assignments. |
| **Storage & Formats** | Apache Parquet (Snappy) | High-performance columnar storage partitioned across raw and processed analytical marts. |
| **SQL Transformations** | DuckDB (Embedded OLAP) | SQL staging views (`stg_*.sql`) and dimensional marts (`mart_*.sql`) executed in-process. |
| **Statistical Analysis** | SciPy, statsmodels, scikit-learn | Two-proportion z-tests, Wald confidence intervals, $\chi^2$ SRM checks, and logistic regression churn scoring. |
| **Testing & Quality** | pytest, ruff, Node test runner | Backend API tests, SQL pipeline tests, frontend client tests, and linting. |

### Data Pipeline Architecture

```
Synthetic Data Generator (Python + NumPy + Faker)
    │
    ▼
Raw Columnar Storage (Parquet)
├── dim_users.parquet (100,000 accounts)
├── fact_events.parquet (1,452,198 product events)
├── fact_subscriptions.parquet (100,000 subscription records)
└── fact_experiments.parquet (20,000 onboarding A/B assignments)
    │
    ▼
DuckDB SQL Pipeline (python -m python.src.run_sql_models)
├── Staging Views (sql/staging/stg_*.sql) — type casting, deduplication, and cleaning
└── Analytical Marts (sql/marts/mart_*.sql)
        ├── mart_funnel.parquet
        ├── mart_cohort_retention.parquet
        ├── mart_experiment_results.parquet
        └── mart_product_growth_daily.parquet
    │
    ▼
Analysis & Modeling Layer (python/src/)
├── analysis.py — Funnel conversion, cohort matrices, hypothesis tests, churn scoring
└── metrics.py — KPI formulas and statistical helpers
    │
    ▼
FastAPI Backend (backend/app/)
├── api/v1/endpoints/ — Tenant-scoped REST endpoints (funnel, cohorts, experiments, churn, auth)
├── services/ — Analytical service layer with DuckDB query execution
├── auth/ — JWT token creation/verification and tenant isolation dependencies
└── schemas/ — Pydantic request/response models for API contracts
    │
    ▼
React + TypeScript Dashboard (frontend/src/)
├── components/ — FunnelVisualizer, CohortRetentionView, ExperimentationView, etc.
├── api/client.ts — Typed API client with auth token management
└── types/api.ts — TypeScript interface definitions matching backend schemas
```

---

## API Endpoints & Dashboard Views

### Backend API (`/api/v1/`)

All analytical endpoints enforce **server-side tenant isolation** via JWT bearer tokens. Each request is scoped to the authenticated tenant's data domain.

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/auth/token` | POST | Obtain tenant-scoped JWT access token |
| `/api/v1/auth/demo-token` | GET | Quick demo token for local development |
| `/api/v1/funnel` | GET | Five-stage conversion funnel with channel benchmarks |
| `/api/v1/cohorts` | GET | Weekly cohort retention matrix and decay analysis |
| `/api/v1/experiments` | GET | A/B test inference with CIs, SRM, and effect sizes |
| `/api/v1/churn` | GET | Churn risk scoring and at-risk account identification |
| `/health` | GET | Service health check |

### React Dashboard Views

- **Funnel Visualizer:** Five-step conversion funnel with stage efficiency table, channel benchmark matrix, and KPI strip.
- **Cohort Retention:** Weekly retention heatmap with configurable cohort parameters.
- **Experimentation Lab:** A/B test results with confidence intervals, effect size visualization, and SRM diagnostics.
- **Filter Bar:** Acquisition channel and date range filtering with reactive data updates.
- **Navigation:** Tab-based navigation with top bar branding.

---

## Core Metric Definitions & Limitations

### Metric Definitions

| Metric | Calculation / Definition |
| :--- | :--- |
| **7-Day Activation Rate** | Accounts that created a workspace within 7 days of signup divided by total signups. |
| **Trial-to-Paid Conversion** | Users who converted to a paid subscription divided by total signups. |
| **Day 30 (D30) Retention** | Active accounts 30 days post-signup divided by cohort signup volume (mature cohorts only). |
| **Churn Rate** | Canceled subscriptions divided by signup volume in the active window. |
| **Ending MRR** | Sum of monthly recurring revenue from active paid subscriptions at the end of the period. |
| **Absolute Lift (pp)** | Difference in proportions: $p_{\text{treatment}} - p_{\text{control}}$, expressed in percentage points. |
| **Relative Lift (%)** | Percentage improvement over baseline: $\frac{p_{\text{treatment}} - p_{\text{control}}}{p_{\text{control}}} \times 100$. |

### Analytical Scope & Known Limitations

- **Parametric Synthetic Distributions:** Data is generated synthetically to model SaaS behavioral dynamics; it does not contain macro anomalies, sudden market shifts, or external shocks.
- **Subscription Model Simplicity:** The underlying subscription generator models three static tiers ($29 Starter, $99 Growth, $299 Enterprise) with flat billing. It does not simulate mid-cycle tier upgrades, seat expansions, or downgrades. Advanced SaaS metrics requiring expansion revenue (such as Net Revenue Retention / NRR, Quick Ratio, or MRR expansion waterfalls) are intentionally omitted to avoid fabricating unsupported metrics.
- **Cohort Maturity Window:** Signup data spans up to June 2025 with events continuing through December 2025. Cohorts near the end of the signup window have limited elapsed observation time. These cells are appropriately represented as unobservable (`N/A`) rather than zero retention.
- **Experiment Scope:** The A/B experiment isolates Day 7 workspace activation. Long-term lifetime value (LTV) and 90-day retention decay by experiment variant are unobservable in the isolated experiment mart.

---

## Project Structure

```
orbit-analysis/
├── backend/                       # FastAPI multi-tenant API
│   └── app/
│       ├── main.py                # Application entry point with CORS and routing
│       ├── config.py              # Settings and storage path resolution
│       ├── api/v1/endpoints/      # Versioned REST endpoints
│       ├── services/              # Analytical service layer (DuckDB queries)
│       ├── schemas/               # Pydantic request/response models
│       └── auth/                  # JWT security, tenant isolation, and user models
├── frontend/                      # React + TypeScript + Vite dashboard
│   ├── src/
│   │   ├── App.tsx                # Root application with tab navigation
│   │   ├── components/            # FunnelVisualizer, CohortRetentionView, etc.
│   │   ├── api/client.ts          # Typed API client with auth token management
│   │   └── types/api.ts           # TypeScript interfaces matching backend schemas
│   ├── test/                      # Frontend client tests
│   ├── package.json               # Frontend dependencies and scripts
│   └── vite.config.ts             # Vite build configuration
├── data/
│   ├── raw/                       # Generated Parquet datasets (gitignored)
│   ├── processed/                 # DuckDB analytical marts (gitignored)
│   └── sample/                    # Sample CSVs for inspection
├── sql/
│   ├── staging/                   # DuckDB staging views (stg_*.sql)
│   └── marts/                     # Analytical mart tables (mart_*.sql)
├── python/
│   └── src/
│       ├── generate_data.py       # Synthetic dataset generator
│       ├── run_sql_models.py      # DuckDB SQL runner
│       ├── analysis.py            # Funnel, cohort, A/B test, churn modeling
│       └── metrics.py             # Growth KPI helper functions
├── tests/                         # pytest test suite
│   ├── test_api_funnel.py         # Funnel API endpoint tests
│   ├── test_api_cohorts.py        # Cohort API tests
│   ├── test_api_experiments.py    # Experimentation API tests
│   ├── test_api_churn.py          # Churn API tests
│   ├── test_sql_pipeline.py       # DuckDB SQL mart transformation tests
│   ├── test_analysis.py           # Statistical analysis tests
│   ├── test_generate_data.py      # Data generation integrity tests
│   ├── test_metrics.py            # KPI calculation tests
│   └── test_theme.py              # Theme token tests
├── docs/                          # Sphinx documentation source
├── pyproject.toml                 # Project metadata, dependencies, and tool config
├── Makefile                       # Make targets for pipeline automation
└── README.md
```

---

## Setup & Execution Guide

### Prerequisites
- **Python 3.13** (required by `pyproject.toml`: `>=3.13,<3.14`).
- **Node.js 18+** (for the React frontend).
- Git.

### 1. Environment Setup

**Windows PowerShell:**
```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install core + backend + dev dependencies
pip install -e ".[dev,backend]"
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,backend]"
```

### 2. Generate Data & Execute SQL Pipeline

```powershell
python -m python.src.generate_data
python -m python.src.run_sql_models
```

### 3. Run Test Suite & Linting

```powershell
python -m pytest
ruff check .
```

### 4. Launch the Application

**Backend (FastAPI):**
```powershell
uvicorn backend.app.main:app --reload --port 8000
```

**Frontend (React + Vite):**
```powershell
cd frontend
npm install
npm run dev
```

The API will be available at `http://localhost:8000` (docs at `/docs`).
The React dashboard will be at `http://localhost:5173`.

---

### Acknowledgment

Orbit Analysis builds upon the original SaaS Growth Analytics project by [Supreetha Gurrala](https://github.com/supreetha9). The current project extends that foundation toward a multi-tenant SaaS product for product and growth analytics, featuring an independently developed FastAPI backend, React + TypeScript dashboard, JWT authentication, tenant isolation, and expanded testing.

## License

This project is licensed under the **MIT License**. The original copyright is preserved alongside the Orbit Analysis continuation.

```text
MIT License

Copyright (c) 2025 Supreetha Gurrala
Copyright (c) 2026 Orbit Analysis Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
