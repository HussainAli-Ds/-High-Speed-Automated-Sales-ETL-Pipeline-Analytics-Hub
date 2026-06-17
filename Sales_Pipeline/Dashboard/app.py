"""
Dashboard/app.py
================
Taipy GUI dashboard for the Sales ETL Pipeline.

Reads data exclusively from the PostgreSQL analytical views defined in
init.sql — all aggregation and math stay in SQL, not in Python.

Run with:
    python Dashboard/app.py
or via run_dashboard.bat

Then open:  http://localhost:5000
"""

import sys
from pathlib import Path

# ── Ensure Code/ is importable from Dashboard/ ───────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Code"))

import pandas as pd
from taipy.gui import Gui, State, notify

from config import Config
from db import query_to_df

# ─────────────────────────────────────────────────────────────────────────────
#   DATA FETCH HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _safe_query(sql: str) -> pd.DataFrame:
    """Return query result, or empty DataFrame on any error."""
    try:
        return query_to_df(sql)
    except Exception as exc:
        print(f"[Dashboard] Query error: {exc}")
        return pd.DataFrame()


def fetch_kpis() -> dict:
    df = _safe_query("SELECT * FROM v_kpi_summary LIMIT 1")
    if df.empty:
        return {
            "total_revenue": 0.0,
            "total_transactions": 0,
            "unique_customers": 0,
            "total_units_sold": 0,
            "avg_order_value": 0.0,
            "files_processed": 0,
        }
    row = df.iloc[0]
    return {
        "total_revenue":      float(row.get("total_revenue",      0) or 0),
        "total_transactions": int(row.get("total_transactions",   0) or 0),
        "unique_customers":   int(row.get("unique_customers",     0) or 0),
        "total_units_sold":   int(row.get("total_units_sold",     0) or 0),
        "avg_order_value":    float(row.get("avg_order_value",    0) or 0),
        "files_processed":    int(row.get("files_processed",      0) or 0),
    }


def fetch_daily_sales() -> pd.DataFrame:
    df = _safe_query(
        "SELECT sale_date::text, total_revenue, transaction_count "
        "FROM v_daily_sales ORDER BY sale_date"
    )
    return df if not df.empty else pd.DataFrame(
        columns=["sale_date", "total_revenue", "transaction_count"]
    )


def fetch_regional() -> pd.DataFrame:
    df = _safe_query(
        "SELECT region, total_revenue, total_orders, unique_customers "
        "FROM v_regional_performance"
    )
    return df if not df.empty else pd.DataFrame(
        columns=["region", "total_revenue", "total_orders", "unique_customers"]
    )


def fetch_category() -> pd.DataFrame:
    df = _safe_query(
        "SELECT product_category, total_revenue, total_units "
        "FROM v_category_summary ORDER BY total_revenue DESC"
    )
    return df if not df.empty else pd.DataFrame(
        columns=["product_category", "total_revenue", "total_units"]
    )


def fetch_top_products() -> pd.DataFrame:
    df = _safe_query(
        "SELECT product_name, product_category, total_revenue, "
        "       total_units_sold, avg_price "
        "FROM v_product_performance LIMIT 15"
    )
    return df if not df.empty else pd.DataFrame(
        columns=["product_name", "product_category", "total_revenue",
                 "total_units_sold", "avg_price"]
    )


def fetch_top_customers() -> pd.DataFrame:
    df = _safe_query(
        "SELECT customer_name, city, state, region, "
        "       total_orders, total_spent, avg_order_value "
        "FROM v_top_customers LIMIT 20"
    )
    return df if not df.empty else pd.DataFrame(
        columns=["customer_name", "city", "state", "region",
                 "total_orders", "total_spent", "avg_order_value"]
    )


def fetch_pipeline_stats() -> pd.DataFrame:
    df = _safe_query(
        "SELECT source_file, records_loaded, "
        "       first_loaded_at::text, total_revenue "
        "FROM v_pipeline_stats ORDER BY first_loaded_at DESC"
    )
    return df if not df.empty else pd.DataFrame(
        columns=["source_file", "records_loaded",
                 "first_loaded_at", "total_revenue"]
    )


# ─────────────────────────────────────────────────────────────────────────────
#   INITIAL STATE VALUES
# ─────────────────────────────────────────────────────────────────────────────

_kpis            = fetch_kpis()

total_revenue     = f"₹ {_kpis['total_revenue']:,.2f}"
total_transactions= str(_kpis["total_transactions"])
unique_customers  = str(_kpis["unique_customers"])
total_units_sold  = str(_kpis["total_units_sold"])
avg_order_value   = f"₹ {_kpis['avg_order_value']:,.2f}"
files_processed   = str(_kpis["files_processed"])

daily_data        = fetch_daily_sales()
regional_data     = fetch_regional()
category_data     = fetch_category()
product_data      = fetch_top_products()
customer_data     = fetch_top_customers()
pipeline_data     = fetch_pipeline_stats()

status_message    = "✅ Data loaded from PostgreSQL views."


# ─────────────────────────────────────────────────────────────────────────────
#   CALLBACKS
# ─────────────────────────────────────────────────────────────────────────────

def on_refresh(state: State) -> None:
    """Refresh all data from the database when the user clicks Refresh."""
    try:
        kpis = fetch_kpis()
        state.total_revenue      = f"₹ {kpis['total_revenue']:,.2f}"
        state.total_transactions = str(kpis["total_transactions"])
        state.unique_customers   = str(kpis["unique_customers"])
        state.total_units_sold   = str(kpis["total_units_sold"])
        state.avg_order_value    = f"₹ {kpis['avg_order_value']:,.2f}"
        state.files_processed    = str(kpis["files_processed"])

        state.daily_data    = fetch_daily_sales()
        state.regional_data = fetch_regional()
        state.category_data = fetch_category()
        state.product_data  = fetch_top_products()
        state.customer_data = fetch_top_customers()
        state.pipeline_data = fetch_pipeline_stats()

        state.status_message = "✅ Dashboard refreshed successfully."
        notify(state, "success", "Data refreshed!")
    except Exception as exc:
        state.status_message = f"❌ Refresh failed: {exc}"
        notify(state, "error", f"Refresh failed: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
#   PAGE LAYOUT  (Taipy Markdown)
# ─────────────────────────────────────────────────────────────────────────────

page = """
<|toggle|theme|>

# 📊 Sales Analytics Dashboard

<|layout|columns=1 1 1 1|gap=1rem|
<|card|
### 💰 Total Revenue
<|{total_revenue}|text|class_name=h3|>
|>

<|card|
### 🛒 Transactions
<|{total_transactions}|text|class_name=h3|>
|>

<|card|
### 👥 Customers
<|{unique_customers}|text|class_name=h3|>
|>

<|card|
### 📦 Units Sold
<|{total_units_sold}|text|class_name=h3|>
|>
|>

<|layout|columns=1 1|gap=1rem|
<|card|
### 🏷️ Avg Order Value
<|{avg_order_value}|text|class_name=h3|>
|>

<|card|
### 📁 Files Processed
<|{files_processed}|text|class_name=h3|>
|>
|>

---

## 📅 Daily Revenue Trend

<|{daily_data}|chart|type=line|x=sale_date|y=total_revenue|title=Daily Revenue|>

---

## 🗺️ Revenue by Region

<|{regional_data}|chart|type=bar|x=region|y[1]=total_revenue|y[2]=total_orders|title=Regional Performance|>

---

## 🏷️ Revenue by Category

<|{category_data}|chart|type=bar|x=product_category|y=total_revenue|title=Category Revenue|>

---

## 🏆 Top 15 Products

<|{product_data}|table|show_all=true|>

---

## 👤 Top 20 Customers

<|{customer_data}|table|show_all=true|>

---

## 📁 Pipeline Ingestion Log

<|{pipeline_data}|table|show_all=true|>

---

<|{status_message}|text|>

<|Refresh Data|button|on_action=on_refresh|>
"""


# ─────────────────────────────────────────────────────────────────────────────
#   LAUNCH
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    gui = Gui(page)
    gui.run(
        title        = "Sales Analytics Dashboard",
        host         = Config.DASHBOARD_HOST,
        port         = Config.DASHBOARD_PORT,
        use_reloader = False,
        dark_mode    = False,
    )