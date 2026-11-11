# Orbit Analysis — B2B SaaS Product & Growth Analytics

An end-to-end product analytics and growth intelligence platform modeling **1.45M+ product events** across **100,000 accounts** for a B2B SaaS company. Features a **FastAPI** multi-tenant backend, **React 18 + TypeScript + Vite** dashboard, **DuckDB** in-process analytical SQL pipeline, and **Python** statistical inference suite. Originally built from the [SaaS Growth Analytics](https://github.com/supreetha9/saas-growth-analytics) foundation.

> **Portfolio & Demonstration Notice:** All data in this repository is generated synthetically using NumPy and Faker for analytics modeling, statistical validation, and portfolio demonstration. It does not represent real customer accounts, proprietary commercial metrics, or measured production systems.

---

## Business Problem & Core Use Cases

A high-velocity B2B self-serve SaaS company experiences strong top-of-funnel signup volume but lacks unified visibility into onboarding friction, customer retention dynamics, experimentation causality, and churn signals. Orbit Analytics provides empirical, statistically sound answers to five mission-critical business growth use cases:

1. **Funnel Friction & Drop-Off Diagnostics:**
   - *Problem:* Where in the five-stage self-serve onboarding journey (`signup` → `workspace_created` → `invite_sent` → `first_project` → `paid`) do accounts stall or abandon the product?
   - *Solution:* Stage-by-stage conversion and leakage analysis with channel-specific benchmarks relative to population baseline.
2. **Cohort Retention & Stickiness Maturity:**
   - *Problem:* How quickly does user engagement decay over a 12-week horizon, and at what percentage does cohort retention plateau into long-term stickiness?
   - *Solution:* Weekly retention heatmap matrices with strict elapsed-period maturity guards (unobserved future weeks explicitly masked as `—` rather than misrepresented as 0% retention).
3. **Experimentation Dual-Lens Analysis (Proxy vs. Downstream ARR):**
   - *Problem:* Did the redesigned onboarding tour (Onboarding V2) produce real business value, or merely inflate early vanity metrics?
   - *Solution:* Dual-lens evaluation pairing 7-day activation hypothesis tests (two-proportion pooled z-test, Wald CIs, Sample Ratio Mismatch diagnostics) with 35-day Intention-To-Treat (ITT) subscription billing linkage (Welch's two-sample t-test for ARPU and post-conversion churn).
4. **Point-in-Time Churn Intelligence & Baseline Comparison:**
   - *Problem:* Can impending subscriber cancellations be identified using early in-product telemetry without data leakage?
   - *Solution:* Strict point-in-time Day-30 observation windows with scikit-learn Logistic Regression evaluated against an out-of-sample Prior Dummy Baseline. Transparent provenance disclosure exposes signal limitations in synthetic data without fabricating false predictive power.
5. **Multi-Tenant Customer Data Onboarding & Partition Isolation:**
   - *Problem:* How can customer growth teams securely upload custom event telemetry without cross-tenant leakage or manual ETL reconfiguration?
   - *Solution:* Cryptographically enforced JWT tenant claims with automatic schema validation, deduplication, observation window completeness checks, and on-demand DuckDB mart materialization into isolated tenant storage.

---

## Key Analytical Findings & Verified Benchmarks

The reference dataset models **100,000 user signups**, **1,452,198 product events**, and **100,000 subscription lifecycle records**:

| Analytical Dimension | Empirical Finding | Verified Benchmark Metric | Business Implication |
| :--- | :--- | :--- | :--- |
| **Primary Funnel Bottleneck** | Highest stage drop-off occurs between sending team invites and creating the first project. | **33.2% drop-off** (46.89% → 31.31% step conversion) | Accounts struggle with project setup; guided templates and sample workspaces needed. |
| **Overall Conversion Efficiency** | Signup-to-paid conversion rate across the full 18-month simulation window. | **15.67%** (15,669 of 100,000 signups convert to paid) | Healthy self-serve freemium conversion benchmark for B2B developer tools. |
| **Top Acquisition Channel** | Referral yields the highest signup-to-paid conversion efficiency. | **18.15%** (vs. Paid Search at 14.39% and 15.67% overall benchmark) | Peer recommendations indicate strong word-of-mouth; prioritize referral viral loops. |
| **Onboarding V2 A/B Test (Activation)** | Statistically significant lift in 7-day workspace creation. | **+3.26 pp absolute lift** (95% CI: [+1.98 pp, +4.54 pp], Z = 4.98, $p < 0.001$) | Streamlined 3-step checklist accelerates initial workspace setup vs multi-page tour. |
| **Onboarding V2 A/B Test (Relative Lift)** | Relative percentage improvement over control baseline (67.27% → 70.53%). | **+4.85% relative lift** | Statistically significant improvement in primary proxy activation metric. |
| **Sample Ratio Mismatch (SRM)** | Split integrity test between control ($n=10,095$) and treatment ($n=9,905$). | **$p = 0.179$ (SRM Passed, $\chi^2 = 1.805, df=1$)** | Assignment allocation matches expected 50/50 split; traffic is unbiased. |
| **Downstream Revenue Decoupling** | 35-day Intention-To-Treat downstream paid conversion. | **+0.02 pp lift** (6.38% vs 6.40%, $p = 0.9506$, Welch ARPU $p = 0.8737$) | **Crucial Insight:** Early activation gains did NOT compound into ARR. Upstream wins require downstream checkout optimization. |
| **Retention Plateau** | Weekly user retention stabilizes after initial onboarding drop. | **~36% mature cohort retention plateau at Week 12** | Demonstrates sustainable product-market fit after initial 4-week attrition. |
| **Point-in-Time Churn Signal** | Out-of-sample ROC-AUC on 30-day post-upgrade feature cutoff. | **ROC-AUC ~0.50, PR-AUC ~0.070, Brier Score ~0.065** | Confirms honest synthetic baseline: uniform cancellations behave like coin flips, matching Prior Dummy Baseline. |

---

## Tech Stack & Architecture

| Layer | Technologies | Architectural Role |
| :--- | :--- | :--- |
| **API Backend** | FastAPI, Pydantic v2, Starlette, Uvicorn | High-performance asynchronous REST API with cryptographic JWT authentication, strict tenant isolation dependencies, and automated OpenAPI documentation (`/docs`). |
| **Frontend Dashboard** | React 18, TypeScript, Vite, Vanilla CSS | Enterprise dark-theme Single Page Application (SPA). Zero external UI frameworks or uncompiled Tailwind; pure native CSS custom properties with responsive laptop, tablet, and mobile layouts. |
| **In-Process Analytical Engine** | DuckDB (Embedded OLAP) | Vectorized columnar SQL execution for dimensional data modeling, windowed aggregations, date-filtered dynamic rollups, and multi-tenant mart materialization. |
| **Statistical Analysis** | SciPy, statsmodels, NumPy, scikit-learn | Two-proportion pooled z-tests, Wald confidence intervals, $\chi^2$ Sample Ratio Mismatch diagnostics, Welch's two-sample t-test for ARPU, and Logistic Regression with DummyClassifier baselines. |
| **Data Generation & Storage** | Python 3.13, Faker, pyarrow, Apache Parquet | Parametric synthetic data generation engine writing compressed columnar Parquet files (`raw/`, `processed/`, and `tenants/{tenant_id}/`). |
| **Quality & Security Testing** | pytest, ruff, Node.js Test Runner | 155 backend unit/integration tests, 20 frontend client tests, strict linting, and end-to-end export consistency verification. |

### Architecture & Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       DATA INGESTION & GENERATION LAYER                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  Synthetic Generator (NumPy + Faker)       Customer CSV Onboarding Upload    │
│  ├── dim_users (100k rows)                 ├── POST /api/v1/onboarding/upload│
│  ├── fact_events (1.45M rows)              ├── Schema validation & cleanup   │
│  ├── fact_subscriptions (100k rows)        ├── Deduplication & window audit │
│  └── fact_experiments (20k rows)          └── Isolated tenant raw storage   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DUCKDB OLAP MODELING LAYER                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Staging Views (sql/staging/stg_*.sql)                                      │
│  ├── Deduplication, timestamp normalization, type coercion                   │
│  Analytical Dimensional Marts (sql/marts/mart_*.sql)                        │
│  ├── mart_funnel.parquet               (5-stage conversion & channel rollup)│
│  ├── mart_cohort_retention.parquet     (Weekly retention matrix)            │
│  ├── mart_experiment_results.parquet   (Variant sample sizes & activation)  │
│  └── mart_product_growth_daily.parquet (Daily active account metrics)       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FASTAPI TENANT-AWARE SERVICE LAYER                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  Authentication & Isolation Boundary (backend/app/auth/)                    │
│  ├── Cryptographic HMAC-SHA256 JWT tokens with verified tenant claims       │
│  ├── RBAC roles: Admin, Analyst, Viewer                                     │
│  Analytical Services (backend/app/services/)                                │
│  ├── FunnelService        ── Fast mart lookup + date-filtered DuckDB rollup  │
│  ├── CohortService        ── Matrix formatting & elapsed-period masking      │
│  ├── ExperimentService    ── Pooled z-tests, Wald CIs, SRM & ITT billing     │
│  ├── ChurnService         ── Point-in-time scikit-learn vs Dummy baseline    │
│  └── IngestionService     ── Customer CSV validation & DuckDB mart generator │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ JSON API & CSV Streams
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                  REACT 18 + TYPESCRIPT FRONTEND DASHBOARD                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  Navigation & TopNav      ── Tenant Switcher, RBAC badges, Onboard modal trigger│
│  Workspace Views          ── Funnel, Cohort Heatmap, Experiments, Churn      │
│  Interactive Features     ── Dynamic filtering, CSV exports, Empty states   │
│  Design System            ── Charcoal dark aesthetic, Teal & Lime accents    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
orbit-analysis/
├── backend/                           # FastAPI multi-tenant REST backend
│   └── app/
│       ├── main.py                    # App entry point, CORS, security headers, global error handler
│       ├── config.py                  # Pydantic Settings, environment variables, security validators
│       ├── api/
│       │   └── v1/
│       │       ├── router.py          # Unified v1 API routing table
│       │       └── endpoints/
│       │           ├── auth.py        # Token issuance & demo authentication
│       │           ├── funnel.py      # Conversion funnel & CSV export
│       │           ├── cohorts.py     # Weekly cohort retention matrix
│       │           ├── experiments.py # A/B testing & downstream revenue intelligence
│       │           ├── churn.py       # Point-in-time churn summary, accounts, & CSV export
│       │           ├── onboarding.py  # Customer data CSV template, status, & ingestion upload
│       │           └── health.py      # Health check endpoint
│       ├── services/                  # Analytical & statistical domain services
│       │   ├── funnel_service.py      # DuckDB ROLLUP & stage calculation
│       │   ├── cohort_service.py      # Maturity-guarded retention matrix calculation
│       │   ├── experiment_service.py  # Z-tests, Wald CIs, SRM, ITT revenue linkage
│       │   ├── churn_service.py       # scikit-learn Pipeline vs DummyClassifier
│       │   └── ingestion_service.py   # CSV validation, deduplication, DuckDB mart generation
│       ├── schemas/                   # Pydantic request and response contract models
│       └── auth/                      # Cryptographic JWT generation, validation, & RBAC dependencies
├── frontend/                          # React 18 + TypeScript + Vite frontend
│   ├── src/
│   │   ├── App.tsx                    # Root dashboard application & workspace router
│   │   ├── main.tsx                   # React DOM entry point
│   │   ├── index.css                  # Enterprise dark styling & responsive media rules
│   │   ├── api/
│   │   │   └── client.ts              # Typed API client, token handling, CSV downloads
│   │   ├── components/
│   │   │   ├── TopNav.tsx             # Brand header, workspace switcher, onboard CTA
│   │   │   ├── NavigationTabs.tsx     # Workspace navigation pill tabs
│   │   │   ├── FilterBar.tsx          # Channel selector, date interval inputs, reset CTA
│   │   │   ├── KpiStrip.tsx           # Top-level conversion & volume KPI cards
│   │   │   ├── FunnelVisualizer.tsx   # 5-stage proportionate horizontal progress bars
│   │   │   ├── StageEfficiencyTable.tsx # Numerical stage drop-off table with CSV export
│   │   │   ├── ChannelBenchmarkMatrix.tsx # Channel performance vs weighted population baseline
│   │   │   ├── CohortRetentionView.tsx# Heatmap matrix with elapsed-period masking
│   │   │   ├── ExperimentationView.tsx# Dual-lens activation & ITT revenue intelligence
│   │   │   ├── ChurnIntelligenceView.tsx # Transparent churn evaluation & exploratory triage
│   │   │   └── DataOnboardingModal.tsx# Accessible modal for CSV upload & data quality audit
│   │   └── types/
│   │       └── api.ts                 # TypeScript type interfaces matching backend schemas
│   ├── test/
│   │   └── client.test.js             # Node test runner suite (20 passing unit tests)
│   ├── package.json                   # Frontend build configuration & dependencies
│   ├── tsconfig.json                  # TypeScript compiler settings
│   └── vite.config.ts                 # Vite development & build setup
├── data/
│   ├── raw/                           # Reference tenant raw Parquet files (gitignored)
│   ├── processed/                     # Reference tenant DuckDB analytical marts (gitignored)
│   ├── tenants/                       # Multi-tenant customer storage partitions (gitignored)
│   └── sample/                        # Small sample CSVs for inspection
├── sql/
│   ├── staging/                       # DuckDB staging views (stg_users, stg_events, etc.)
│   └── marts/                         # DuckDB mart queries (mart_funnel, mart_cohort_retention, etc.)
├── python/
│   └── src/
│       ├── generate_data.py           # 1.45M event synthetic data generation script
│       ├── run_sql_models.py          # CLI runner executing DuckDB SQL pipeline
│       ├── analysis.py                # Standalone analysis functions
│       └── metrics.py                 # Growth formula helper library
├── scripts/
│   └── verify_phase1_exports.py       # End-to-end export & JSON consistency verification script
├── tests/                             # Pytest test suite (155 passing tests)
│   ├── test_api_funnel.py             # Funnel API and tenant isolation tests
│   ├── test_api_cohorts.py            # Cohort retention API tests
│   ├── test_api_experiments.py        # Experiment activation API tests
│   ├── test_api_experiment_revenue.py # Downstream revenue intelligence API tests
│   ├── test_api_churn.py              # Churn model evaluation & accounts API tests
│   ├── test_api_onboarding.py         # Customer data ingestion & validation contract tests
│   ├── test_api_security.py           # Cryptographic JWT, RBAC, & tenant boundary tests
│   ├── test_sql_pipeline.py           # DuckDB SQL transformation integrity tests
│   ├── test_generate_data.py          # Data generation contract tests
│   ├── test_analysis.py               # Statistical calculation unit tests
│   └── test_metrics.py                # Metric helper function tests
├── docs/                              # Sphinx documentation sources
├── pyproject.toml                     # Python dependencies, packaging, & tool configs
├── Makefile                           # Development automation commands
└── README.md                          # Comprehensive project documentation
```

---

## Installation & Setup Instructions

### Prerequisites
- **Python 3.13** (required: `>=3.13,<3.14`).
- **Node.js 18+** & **npm 9+**.
- Git.

### 1. Environment Setup

**Windows PowerShell:**
```powershell
# Clone the repository
git clone <repository_url>
cd orbit-analysis

# Create virtual environment with Python 3.13
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install all backend, analytical, and development dependencies
pip install -e ".[dev,backend]"

# Install frontend dependencies
cd frontend
npm install
cd ..
```

**macOS / Linux:**
```bash
# Clone the repository
git clone <repository_url>
cd orbit-analysis

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev,backend]"

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Generate Synthetic Benchmark Data & Build SQL Marts

Generate the 1.45M+ event dataset and execute the DuckDB transformation pipeline:

```powershell
# Generate dim_users, fact_events, fact_subscriptions, fact_experiments
python -m python.src.generate_data

# Execute SQL pipeline to materialize analytical marts in data/processed/
python -m python.src.run_sql_models
```

---

## Startup Commands

### Start the FastAPI Backend
```powershell
# From project root, with virtual environment activated:
uvicorn backend.app.main:app --reload --port 8000
```
- API Root: `http://localhost:8000`
- Interactive OpenAPI Docs (Swagger UI): `http://localhost:8000/docs`
- Redoc Alternative Documentation: `http://localhost:8000/redoc`
- Health Check: `http://localhost:8000/health`

### Start the React + Vite Frontend
```powershell
# In a separate terminal, navigate to frontend:
cd frontend
npm run dev
```
- Interactive Dashboard: `http://localhost:5173`

---

## Environment Configuration

The application is configured using Pydantic Settings reading environment variables or `.env` files:

| Environment Variable | Default Value | Production Requirement | Description |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | `development` | Set to `production` | Enables HSTS, enforces strict secrets, and disables demo auth. |
| `SECRET_KEY` | `orbit_analytics_dev_secret_key...` | **Required (Min 32 characters)** | HMAC-SHA256 signing secret for JWT access tokens. Application startup aborts in production if default or short key is detected. |
| `ENABLE_DEMO_AUTH` | `true` (dev) / `false` (prod) | Disabled | Controls access to `/api/v1/auth/demo-token`. Automatically forced to `false` in production unless explicitly overridden. |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Set to production domain(s) | Comma-separated list of allowed origins (e.g. `https://analytics.orbitcorp.com`). |
| `DATA_DIR` | `<root>/data` | Persistent volume mount | Base directory for raw parquet files and tenant partitions. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24 hours) | 15–120 minutes recommended | Lifetime of issued bearer JWT access tokens. |

---

## API Endpoints Reference

All analytical endpoints require a valid Bearer JWT access token passed via the `Authorization: Bearer <token>` header. Analytical queries are strictly scoped to the tenant claim embedded in the token.

### Authentication & Health
| Endpoint | Method | Auth Required | Parameters / Body | Description |
| :--- | :--- | :--- | :--- | :--- |
| `/health` | GET | No | None | Service status and multi-tenant environment info. |
| `/api/v1/auth/token` | POST | No | JSON: `email`, `tenant_id` | Issues a signed JWT for a registered tenant user. |
| `/api/v1/auth/demo-token` | GET | No (Dev only) | Query: `tenant_id` | Issues a demo token for approved reference tenants (`org_orbit_demo`, `org_acme_corp`, `org_starlight_saas`). |

### Funnel Analytics
| Endpoint | Method | Auth Required | Parameters | Description |
| :--- | :--- | :--- | :--- | :--- |
| `/api/v1/funnel` | GET | Bearer JWT | Query: `acquisition_channel`, `start_date`, `end_date` | 5-stage conversion funnel, step drop-offs, and channel benchmarks. |
| `/api/v1/funnel/export` | GET | Bearer JWT | Query: `acquisition_channel`, `start_date`, `end_date` | Downloads authorized CSV file of conversion stages. |

### Cohort Retention
| Endpoint | Method | Auth Required | Parameters | Description |
| :--- | :--- | :--- | :--- | :--- |
| `/api/v1/cohorts` | GET | Bearer JWT | Query: `max_weeks` (1–24), `num_cohorts` (1–52), `min_cohort_size`, `start_date`, `end_date` | Weekly cohort retention heatmap matrix with elapsed-period masking and milestones. |

### Experimentation Intelligence
| Endpoint | Method | Auth Required | Parameters | Description |
| :--- | :--- | :--- | :--- | :--- |
| `/api/v1/experiments` | GET | Bearer JWT | None | Lists registered experiments for the authenticated tenant. |
| `/api/v1/experiments/{name}` | GET | Bearer JWT | Path: `name` | Two-proportion pooled z-test, Wald CIs, Sample Ratio Mismatch diagnostic. |
| `/api/v1/experiments/{name}/revenue` | GET | Bearer JWT | Path: `name` | 35-day ITT paid conversion, Active Snapshot MRR, Welch's t-test for ARPU, post-conversion churn. |

### Churn Intelligence
| Endpoint | Method | Auth Required | Parameters | Description |
| :--- | :--- | :--- | :--- | :--- |
| `/api/v1/churn/summary` | GET | Bearer JWT | None | Day-30 point-in-time scikit-learn model metrics vs Prior Dummy Baseline, calibration assessment, risk percentiles. |
| `/api/v1/churn/accounts` | GET | Bearer JWT | Query: `risk_tier`, `industry`, `plan_type`, `limit` (1–500) | Scored customer accounts prioritized by modeled probability and inactivity. |
| `/api/v1/churn/export` | GET | Bearer JWT | Query: `risk_tier`, `industry`, `plan_type`, `limit` (1–1000) | Downloads authorized CSV export of prioritized at-risk accounts. |

### Customer Data Onboarding
| Endpoint | Method | Auth Required | Parameters / Body | Description |
| :--- | :--- | :--- | :--- | :--- |
| `/api/v1/onboarding/template` | GET | No | None | Downloads canonical CSV template with valid schema headers and sample events. |
| `/api/v1/onboarding/status` | GET | Bearer JWT | None | Retrieves latest ingestion timestamps, accepted/rejected counts, and window coverage. |
| `/api/v1/onboarding/upload` | POST | Bearer JWT (Admin/Analyst) | Multipart Form: `file` (.csv) | Validates and ingests customer CSV telemetry, materializing tenant-isolated DuckDB marts. |

---

## Customer Data Onboarding & Schema Contracts

Organizations can onboard their own product telemetry using the **Data Onboarding Modal** or the `/api/v1/onboarding/upload` API endpoint.

### Schema Contract
Uploaded files must be UTF-8 encoded CSV files satisfying the following column schema:

| Column Name | Required | Data Type | Example Value | Description |
| :--- | :--- | :--- | :--- | :--- |
| `user_id` | **Yes** | String / Text | `usr_91024` | Unique account identifier. |
| `event_name` | **Yes** | String / Text | `workspace_created` | Canonical event name (case-insensitive). |
| `event_timestamp` | **Yes** | ISO Timestamp | `2025-01-04 10:15:00` | Timestamp of event occurrence (`YYYY-MM-DD HH:MM:SS` or ISO 8601). |
| `acquisition_channel` | No | String / Text | `Organic` | Attribution channel (e.g. `Direct`, `Organic`, `Referral`, `Paid Search`, `Partner`). |

### Canonical Events Mapping
The ingestion service automatically normalizes raw event variations to the 5 standard conversion stages:

| Canonical Stage | Accepted Raw Aliases | Funnel Stage Order |
| :--- | :--- | :--- |
| `signup` | `signup`, `user_signup`, `sign_up` | Stage 1 (Baseline) |
| `workspace_created` | `workspace_created`, `workspace`, `create_workspace` | Stage 2 |
| `invite_sent` | `invite_sent`, `invite`, `send_invite` | Stage 3 |
| `first_project` | `first_project`, `project`, `create_project` | Stage 4 |
| `paid` | `paid`, `upgrade`, `subscription_paid`, `checkout_completed` | Stage 5 (Goal) |

### Validation Rules & Protections
1. **File Size Limit:** Maximum 10 MB per file (`HTTP 413` if exceeded).
2. **Row Limit:** Maximum 100,000 rows per file.
3. **Timestamp Validation:** Events earlier than year 2015 or more than 24 hours in the future are rejected.
4. **Duplicate Deduplication:** Duplicate `(user_id, event_name, event_timestamp)` records are automatically identified and excluded.
5. **Window Completeness Advisory:** If the observed date span is less than 14 days, a data quality advisory warning is surfaced.
6. **All-Invalid Rejection:** If all rows fail validation, the file is rejected with `HTTP 422 Unprocessable Entity` accompanied by sample rejection diagnostics.

---

## Testing & Verification Suite

The repository contains automated test suites across both backend and frontend layers:

```
┌────────────────────────────────────────────────────────┐
│ TEST EXECUTION SUMMARY                                 │
├────────────────────────────────────────────────────────┤
│ Backend pytest suite:     155 passed, 1 skipped (0 fail)│
│ Frontend Node test suite: 20 passed (0 fail)           │
│ Production build:         tsc && vite build (Clean)    │
│ Python linting:           ruff check . (0 errors)      │
│ Export consistency:       scripts/verify_phase1_exports│
└────────────────────────────────────────────────────────┘
```

### 1. Run Backend Pytest Suite
```powershell
python -m pytest
```
*Executes all 155 tests covering API endpoints, tenant isolation boundaries, RBAC permissions, statistical formulas, DuckDB SQL pipelines, and customer CSV ingestion.*

### 2. Run Ruff Linting
```powershell
ruff check .
```

### 3. Run Frontend Unit Tests
```powershell
cd frontend
npm test
```
*Executes 20 Node test runner tests validating parameter serialization, date range bounds, relative lift formulas, SRM detection, ARPU calculations, and empty-state handling.*

### 4. Run Frontend Production TypeScript Build
```powershell
cd frontend
npm run build
```
*Compiles TypeScript through `tsc` and bundles through Vite with zero type errors.*

### 5. Verify CSV Export & JSON Consistency
```powershell
python scripts/verify_phase1_exports.py
```
*Compares live API JSON outputs against streamed CSV exports for both funnel stages and at-risk accounts.*

---

## Working Dashboard Visual Representations

The React dashboard provides a responsive enterprise interface configured with charcoal backgrounds (`#090D12`, `#161B22`), muted borders (`#30363D`), and teal/lime accents (`#14B8A6`, `#84CC16`).

### 1. Funnel Intelligence Workspace
```text
+----------------------------------------------------------------------------------------------------+
| [Logo] Orbit Analysis  Multi-Tenant Cloud | Workspace: [ Orbit Reference SaaS Corp (org_orbit_demo) ] [Onboard Data] |
+----------------------------------------------------------------------------------------------------+
| [ Funnel Workspace ]   [ Cohort Retention ]   [ Experimentation Lab ]   [ Churn Intelligence ]     |
+----------------------------------------------------------------------------------------------------+
| Channel: [ All Channels v ]  From: [ YYYY-MM-DD ]  To: [ YYYY-MM-DD ]   [ Apply Filter ]  [ Reset ]|
+----------------------------------------------------------------------------------------------------+
| 01. STAGE: Signup       02. STAGE: Workspace      03. STAGE: Invite         04. STAGE: Project     |
| 100,000 users           70,500 users              46,890 users              31,310 users           |
| [^] 100.0% Baseline     [^] 70.5% (-29.5%)        [^] 66.5% (-33.5%)        [v] 66.8% (-33.2%)     |
+----------------------------------------------------------------------------------------------------+
| FIVE-STAGE BEHAVIORAL CONVERSION FUNNEL                                       Overall: 15.67%      |
| 1. Signup               [===================================================] 100,000  (100.0%)    |
| 2. Workspace Created    [=====================================>             ]  70,500  ( 70.5%)    |
| 3. Invite Sent          [========================>                          ]  46,890  ( 46.9%)    |
| 4. First Project        [=================>                                 ]  31,310  ( 31.3%)    |
| 5. Paid Conversion      [========>                                          ]  15,669  ( 15.7%)    |
+----------------------------------------------------------------------------------------------------+
| STAGE EFFICIENCY & DROP-OFF TABLE [Export CSV]   | CHANNEL BENCHMARKING MATRIX                     |
| Stage        Entering   Lost      Step%  Overall%| Channel       Signups   Paid    Conv%   Variance    |
| 1. Signup    100,000    -         100%   100.0%  | REFERRAL      18,200    3,303   18.15%  +2.48 pp    |
| 2. Workspace  70,500    29,500    70.5%   70.5%  | ORGANIC       24,100    3,892   16.15%  +0.48 pp    |
| 3. Invite     46,890    23,610    66.5%   46.9%  | DIRECT        20,300    3,165   15.59%  -0.08 pp    |
| 4. Project    31,310    15,580    66.8%   31.3%  | PARTNER       16,400    2,427   14.80%  -0.87 pp    |
| 5. Paid       15,669    15,641    50.0%   15.7%  | PAID SEARCH   21,000    3,022   14.39%  -1.28 pp    |
+----------------------------------------------------------------------------------------------------+
```

### 2. Cohort Retention Heatmap
```text
+----------------------------------------------------------------------------------------------------+
| Horizon: [ Weeks 0 - 12 v ]  Cohorts: [ Last 15 v ]  Min Size: [ 500 ]  [ Reset Cohort Defaults ]  |
+----------------------------------------------------------------------------------------------------+
| [!] Retention Maturity Guard: Unelapsed future weeks are masked as (—), not misrepresented as 0%.  |
+----------------------------------------------------------------------------------------------------+
| Cohort Week  Size    W0    W1    W2    W3    W4    W5    W6    W7    W8    W9    W10   W11   W12   |
| 2024-01-01   1,420  100%   72%   58%   51%   47%   44%   42%   40%   39%   38%   37%   36%   36%   |
| 2024-01-08   1,380  100%   71%   57%   50%   46%   43%   41%   39%   38%   37%   36%   36%   35%   |
| ...          ...    ...    ...   ...   ...   ...   ...   ...   ...   ...   ...   ...   ...   ...   |
| 2024-06-17   1,610  100%   73%   59%   52%   48%   45%   43%   41%    —     —     —     —     —    |
| 2024-06-24   1,590  100%   72%   58%   51%   47%   44%   42%    —     —     —     —     —     —    |
+----------------------------------------------------------------------------------------------------+
```

### 3. Experimentation Lab (Dual-Lens Workspace)
```text
+----------------------------------------------------------------------------------------------------+
| Select Experiment: [ onboarding_v2 v ]  |  [ View Activation Proxy ]  [ View Downstream Billing ]  |
+----------------------------------------------------------------------------------------------------+
| [OK] STATISTICALLY SIGNIFICANT LIFT (ALPHA = 0.05)                                                 |
| Treatment (+3.26 pp absolute, +4.85% relative) increased 7-day activation (Z = 4.98, p < 0.001).  |
| 95% Confidence Interval: [+1.98 pp, +4.54 pp]. Sample Ratio Mismatch check passed (p = 0.179).    |
+----------------------------------------------------------------------------------------------------+
| [DOWNSTREAM REVENUE & BILLING INTELLIGENCE — COMMERCIAL OUTCOME]                                   |
| [!] PROXY METRIC DECOUPLING ADVISORY: 7-day activation gain did NOT translate to downstream ARR!  |
| Control Paid Conv: 6.38% (644 / 10,095)  |  Treatment Paid Conv: 6.40% (634 / 9,905) | Diff: +0.02pp|
| Control Mean ARPU: $3.89                |  Treatment Mean ARPU: $3.87               | Diff: -$0.015|
| Two-Proportion Conversion Test: p = 0.9506 (Not Significant)                                       |
| Welch's Two-Sample ARPU Test:   p = 0.8737 (Not Significant)                                       |
+----------------------------------------------------------------------------------------------------+
```

### 4. Churn Intelligence Workspace
```text
+----------------------------------------------------------------------------------------------------+
| [!] AUDITED MODEL DISCLOSURE: SYNTHETIC DATA & BASELINE DISCRIMINATION                             |
| Uniform synthetic cancellations behave as Bernoulli coin flips. When evaluated point-in-time       |
| without leakage, out-of-sample ROC-AUC is 0.5012 (chance = 0.50) and PR-AUC is 0.0701. The model   |
| matches the Dummy Prior Baseline. Risk tiers reflect empirical percentiles for exploratory triage. |
+----------------------------------------------------------------------------------------------------+
| ROC-AUC: 0.5012 (Baseline: 0.5000)  |  PR-AUC: 0.0701 (Baseline: 0.0701)  | Brier: 0.0652 (Good)   |
+----------------------------------------------------------------------------------------------------+
| PRIORITIZED AT-RISK ACCOUNTS FOR RETENTION OUTREACH [Export CSV]                                   |
| Account ID  Probability  Risk Tier  Days Inactive  Plan        Industry     Recommended Action     |
| usr_04281   13.42%       High       28.4 days      Enterprise  Healthcare   Audit 20+d inactivity  |
| usr_08912   12.89%       High       24.1 days      Pro         Finance      Check feature usage    |
+----------------------------------------------------------------------------------------------------+
```

---

## Production Deployment & Cloud Considerations

The following checklist details the architectural considerations for cloud-native deployment:

1. **State & Storage Architecture:**
   - *Current:* Local filesystem storage for Parquet datasets in `data/raw/`, `data/processed/`, and `data/tenants/`.
   - *Cloud Migration:* Configure cloud object storage (AWS S3, Google Cloud Storage, or Azure Blob Storage) with standard IAM policies. DuckDB supports direct zero-copy S3/GCS reads via the `httpfs` extension (`read_parquet('s3://orbit-analytics-data/...')`).
2. **Secrets & Security:**
   - Production secrets (`SECRET_KEY`) must be injected securely via AWS Secrets Manager, GCP Secret Manager, or Kubernetes Secrets.
   - Restrict `CORS_ORIGINS` strictly to authorized company domains.
   - Demo authentication (`ENABLE_DEMO_AUTH=false`) is forced off in production.
3. **Database & High Concurrency:**
   - For enterprise workloads exceeding hundreds of concurrent analytical writers, consider decoupling analytical queries from the API process via a distributed DuckDB cluster (e.g. MotherDuck) or Postgres with columnar storage extensions (Citrus / pgvector).
4. **Containerization:**
   - Standard dual-container deployment:
     - Backend: Lightweight Python 3.13 Debian-slim container running `uvicorn` with multiple worker processes.
     - Frontend: Static Nginx container serving compiled Vite production assets (`frontend/dist/`) with caching headers.
5. **Observability & Logging:**
   - Add structured JSON logging (e.g. structlog) with correlation IDs passed via request headers.
   - Integrate OpenTelemetry for APM tracing and Prometheus metrics endpoints.

---

## Acknowledgment & License

Orbit Analysis builds upon the original SaaS Growth Analytics project by [Supreetha Gurrala](https://github.com/supreetha9). The current repository extends that foundation into a production-grade multi-tenant platform with an independently architected FastAPI backend, React 18 + TypeScript dashboard, cryptographic tenant isolation, point-in-time churn intelligence, customer data onboarding, and rigorous statistical testing.

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
