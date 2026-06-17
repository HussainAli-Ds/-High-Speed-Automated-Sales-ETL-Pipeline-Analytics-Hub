# 🚀 High-Speed Automated Sales ETL Pipeline & Analytics Hub

> **Built by [Hussain Ali](https://github.com/HussainAli-Ds)** — Data professional specializing in high-performance automation systems and enterprise-grade data pipelines.

An end-to-end, event-driven data engineering platform that eliminates the most painful bottlenecks in traditional analytics workflows — from messy vendor spreadsheets to a live glassmorphic dashboard, in near real-time.

---

## 📌 Table of Contents

- [The Problem & Solution](#-the-problem--solution)
- [System Architecture](#-system-architecture--data-flow)
- [Key Engineering Highlights](#-key-engineering-highlights)
- [Engineering Challenges Solved](#-engineering-challenges-solved)
- [Project Structure](#-project-structure)
- [Analytical Views Layer](#-analytical-views-layer)
- [Setup & Deployment](#-setup--deployment)
- [Connect](#-lets-connect)

---

## 💡 The Problem & Solution

**Traditional analytics pipelines suffer from:**

- ❌ Manually handling, parsing, and cleaning disparate vendor spreadsheet layouts
- ❌ Sluggish row-by-row transactional database writes and heavy ORM overhead
- ❌ Inefficient architectures that re-calculate heavy metrics on every page refresh

**This platform solves all three with a seamless operational loop:**

```
Raw Excel Spreadsheets
  ──▶ Python Ingestion Engine
    ──▶ Binary ADBC Stream
      ──▶ PostgreSQL Indexed Views
        ──▶ Telegram Alert Monitoring
          ──▶ Glassmorphic Taipy Dashboard
```

---

## 🏗️ System Architecture & Data Flow

This platform enforces a strict **"compute-at-the-storage-layer"** philosophy. The Python automation layer acts as a lean entry conductor — handling async file events, schema standardization, and zero-copy binary streaming — while **100% of KPI calculations and filter predicates are offloaded to indexed PostgreSQL views**.

```
[ Excel File Drops ] ──▶ ( Watchdog File Event Trigger )
                                      │
                                      ▼
                         [ Asynchronous Python Engine ]
                  ┌──────────────────────────────────────────┐
                  │  1. Concurrent Windows File Lock Handling │
                  │  2. Fuzzy String Canonical Alignment      │
                  │  3. Memory-Efficient Polars Vector Cast   │
                  └──────────────────────────────────────────┘
                                      │
                                      ▼  (ADBC Binary COPY Stream)
                            [ PostgreSQL Core ]
                  ┌──────────────────────────────────────────┐
                  │  1. Unified Raw Staging Tier (FLOAT8)    │
                  │  2. Optimized Target Indexing Structures │
                  │  3. Pushed-Down Materialized View Matrix │
                  └──────────────────────────────────────────┘
                                      │
                  ┌───────────────────┴────────────────────┐
                  ▼                                        ▼
     [ Telegram Telemetry Engine ]          [ Glassmorphic Taipy UI ]
  ┌────────────────────────────────┐     ┌────────────────────────────────┐
  │  Real-Time Pipeline Heartbeats │     │  Reactive Analytical Bindings  │
  │  Live Exception Alert Streams  │     │  Predicate-Pushed Filters      │
  └────────────────────────────────┘     └────────────────────────────────┘
```

---

## ⚡ Key Engineering Highlights

**Sub-Second Binary Bulk Ingestion**
Bypasses sluggish pandas iteration by using memory-mapped Polars DataFrames and ADBC (Arrow Database Connectivity) to stream raw binary structures straight into PostgreSQL via native low-level `COPY` protocols.

**Fuzzy Schema Alignment Engine**
Employs optimized string-matching (`thefuzz` / `rapidfuzz`) to automatically evaluate token ratios and dynamically map messy or inconsistent vendor column headers into a single clean relational schema.

**Resilient Directory Watcher**
An async directory watcher (`watchdog`) with defensive retry back-offs that gracefully navigates Windows background I/O file locks — automatically archiving processed files chronologically or routing corrupt spreadsheets into an isolated quarantine folder.

**High-Speed Relational Storage**
Structured indices over highly-queried temporal and categorical constraints (`sale_date`, `region`, `city`, `product_category`) ensure dashboard filter predicates are pushed directly to the index layer for instant results.

**Premium Glassmorphic UI**
Built with Taipy GUI and Plotly — featuring full background-blur layers (`backdrop-filter`), hardware-accelerated CSS3 fade transitions, and reactive state sync bindings for smooth, real-time data visualization.

**Infrastructure Observability via Telegram**
An async notification layer dispatches ingestion metrics, performance profiles, and runtime exceptions directly to admin devices via the Telegram Bot API.

---

## 🧠 Engineering Challenges Solved

**Windows Multi-Process File-Lock Conflicts**
Background Excel processes frequently cause write-access collisions during automated file tracking. Solved with a polling fallback system that actively interrogates OS file handles until safe, non-blocking read access is confirmed.

**Library Version & Binary Dependency Conflicts**
Integrating fast data layers (ADBC, Arrow) with interactive UI frameworks requires precise dependency management. Explicit compiler variant pinning across all environments eliminates memory layout discrepancies entirely.

**Full Offload to SQL Computation Layer**
Moving 100% of analytics out of Python and into PostgreSQL required a full architectural re-design. Nested analytical views now compute composite attributes — including regional market shares and temporal density matrices — using native indexing structures.

---

## 📂 Project Structure

```
├── .dockerignore              # Container deployment exclusions
├── .gitignore                 # Version control constraints
├── README.md                  # Project documentation (you are here)
├── run_dashboard.bat          # Fast-boot script for the frontend
│
├── Code/
│   ├── config.py              # Environment and system configuration
│   ├── logger.py              # Formatted log stream managers
│   ├── db.py                  # ADBC engine setup & database connections
│   ├── column_mapper.py       # Levenshtein-distance schema mapping engine
│   ├── processor.py           # Core ETL validation and transformation routine
│   ├── telegram_bot.py        # Telemetry and exception notification pipeline
│   └── pipeline.py            # Event-loop directory watcher entry point
│
└── Dashboard/
    ├── app.py                 # Taipy state coordination and UI components
    └── css/
        └── style.css          # Glassmorphism styling layers
```

---

## 📊 Analytical Views Layer

The interactive frontend communicates exclusively with **11 tuned PostgreSQL views** configured in `init.sql`.

| Database View | UI Component | Computed Output |
|---|---|---|
| `v_kpi_summary` | KPI Metrics Grid | Total Revenue, Units Sold, AOV, DB Latency |
| `v_daily_sales` | Revenue Stream Chart | Chronological revenue trajectory (Line Chart) |
| `v_product_performance` | Product Volume Charts | Units sold & aggregate revenue (Bar / Table) |
| `v_city_performance` | City Density Cluster | High-performance regional nodes (Bubble Chart) |
| `v_regional_performance` | Regional Intensity Map | Geographic distribution & concentration indexes |
| `v_top_customers` | Customer Hierarchy Grid | High-yield customer profiles & total spend |
| `v_product_region` | Cross-Sectional Grid | Regional distribution by product SKU |
| `v_product_city` | Cross-Sectional Grid | City-by-city product transaction breakdown |
| `v_date_summary` | Chrono Table | Volumetric and sales velocity trends by date |
| `v_date_region` | Chrono Table | Time-series intersections grouped by region |
| `v_date_city` | Chrono Table | Time-series intersections grouped by city |

---

## 🛠️ Setup & Deployment

### 1. Database Provisioning

Run `init.sql` against your target cluster to create all storage nodes, index tables, and views:

```bash
psql -h localhost -U postgres -d sales_database -f init.sql
```

### 2. Python Environment

```bash
# Create and activate isolated virtual environment
python -m venv venv
venv\Scripts\activate        # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables (`.env`)

Create a `.env` file in the project root:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sales_analytics
DB_USER=postgres
DB_PASSWORD=your_secure_password_here

TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

### 4. Running the System

Open **two terminal windows** (both inside the virtual environment):

```bash
# Terminal 1 — Background ingestion worker
python Code/pipeline.py

# Terminal 2 — Analytics dashboard
.\run_dashboard.bat
```

Then open **http://localhost:5000** in your browser. Drop any vendor Excel file into the monitored input directory to watch the pipeline process it in real time.

---

## 🐳 Automated Deployment Matrix via Docker Compose

Skip local database setups, virtual environment dependencies, and platform driver compilations. Initialize the complete architecture stack natively inside isolated runtime vectors using a single command string:

```bash
# Build the application image and deploy the entire multi-container platform
docker-compose up --build
```
## 📬 Let's Connect

I'm actively building optimized, enterprise-ready data architectures, scalable pipeline workflows, and high-performance analytics platforms. Open to collaborations, open-source contributions, freelance projects, and full-time opportunities.

| | |
|---|---|
| 📧 **Email** | ha780383@gmail.com |
| 📱 **Phone** | +92 335 7897412 |
| 💻 **GitHub** | [HussainAli-Ds](https://github.com/HussainAli-Ds) |

---

*Built with a commitment to clean design, high performance, and robust system architecture.*
