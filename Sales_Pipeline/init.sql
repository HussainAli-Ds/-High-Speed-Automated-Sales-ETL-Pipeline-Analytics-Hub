-- ============================================================
--   init.sql  —  Sales ETL Pipeline  |  Full Analytics Layer
--   Table uses DOUBLE PRECISION (matches Arrow float64 / ADBC).
--   All computation stays in SQL. Python = load only.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ══════════════════════════════════════════════════════════════
--   STAGING TABLE
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS staging_sales (
    id               BIGSERIAL          PRIMARY KEY,
    sale_date        DATE,
    customer_name    TEXT,
    city             TEXT,
    state            TEXT,
    region           TEXT,
    product_category TEXT,
    product_name     TEXT,
    quantity         INTEGER,
    price_per_unit   DOUBLE PRECISION,
    sales_amount     DOUBLE PRECISION,
    source_file      TEXT,
    loaded_at        TIMESTAMPTZ        NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ss_sale_date        ON staging_sales (sale_date);
CREATE INDEX IF NOT EXISTS idx_ss_region           ON staging_sales (region);
CREATE INDEX IF NOT EXISTS idx_ss_city             ON staging_sales (city);
CREATE INDEX IF NOT EXISTS idx_ss_product_category ON staging_sales (product_category);
CREATE INDEX IF NOT EXISTS idx_ss_customer_name    ON staging_sales (customer_name);
CREATE INDEX IF NOT EXISTS idx_ss_source_file      ON staging_sales (source_file);
CREATE INDEX IF NOT EXISTS idx_ss_loaded_at        ON staging_sales (loaded_at);

-- ══════════════════════════════════════════════════════════════
--   KPI SUMMARY
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW v_kpi_summary AS
SELECT
    COALESCE(ROUND(SUM(sales_amount)::NUMERIC, 2), 0)   AS total_revenue,
    COALESCE(COUNT(*), 0)                               AS total_transactions,
    COALESCE(COUNT(DISTINCT customer_name), 0)          AS unique_customers,
    COALESCE(SUM(quantity), 0)                          AS total_units_sold,
    COALESCE(ROUND(AVG(sales_amount)::NUMERIC, 2), 0)   AS avg_order_value,
    COALESCE(COUNT(DISTINCT source_file), 0)            AS files_processed,
    COALESCE(COUNT(DISTINCT product_name), 0)           AS unique_products,
    MIN(sale_date)                                      AS earliest_sale,
    MAX(sale_date)                                      AS latest_sale,
    MAX(loaded_at)                                      AS last_loaded
FROM staging_sales;

-- ══════════════════════════════════════════════════════════════
--   DAILY SALES
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW v_daily_sales AS
SELECT
    sale_date,
    COUNT(*)                                                  AS transaction_count,
    SUM(quantity)                                             AS total_quantity,
    ROUND(SUM(sales_amount)::NUMERIC, 2)                      AS total_revenue,
    ROUND(SUM(quantity * price_per_unit)::NUMERIC, 2)         AS calculated_revenue,
    ROUND(AVG(sales_amount)::NUMERIC, 2)                      AS avg_order_value
FROM staging_sales
WHERE sale_date IS NOT NULL
GROUP BY sale_date
ORDER BY sale_date;

-- ══════════════════════════════════════════════════════════════
--   MONTHLY KPIS
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW v_monthly_kpis AS
SELECT
    TO_CHAR(sale_date, 'YYYY-MM')                    AS month,
    COUNT(*)                                         AS total_orders,
    SUM(quantity)                                    AS total_items_sold,
    ROUND(SUM(sales_amount)::NUMERIC, 2)             AS total_revenue,
    ROUND(AVG(sales_amount)::NUMERIC, 2)             AS average_order_value
FROM staging_sales
WHERE sale_date IS NOT NULL
GROUP BY TO_CHAR(sale_date, 'YYYY-MM')
ORDER BY month DESC;

-- ══════════════════════════════════════════════════════════════
--   REGIONAL PERFORMANCE
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW v_regional_performance AS
SELECT
    region,
    state,
    COUNT(DISTINCT customer_name)                    AS unique_customers,
    COUNT(*)                                         AS total_orders,
    SUM(quantity)                                    AS total_quantity,
    ROUND(SUM(sales_amount)::NUMERIC, 2)             AS total_revenue,
    ROUND(AVG(sales_amount)::NUMERIC, 2)             AS avg_order_value,
    ROUND(
        (100.0 * SUM(sales_amount) / NULLIF(SUM(SUM(sales_amount)) OVER (), 0))::NUMERIC, 2
    )                                                AS revenue_share_pct
FROM staging_sales
GROUP BY region, state
ORDER BY total_revenue DESC;

-- ══════════════════════════════════════════════════════════════
--   CITY PERFORMANCE (heatmap + bubble + tables)
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW v_city_performance AS
SELECT
    city,
    state,
    region,
    COUNT(DISTINCT customer_name)                    AS unique_customers,
    COUNT(*)                                         AS total_orders,
    SUM(quantity)                                    AS total_quantity,
    ROUND(SUM(sales_amount)::NUMERIC, 2)             AS total_revenue,
    ROUND(AVG(sales_amount)::NUMERIC, 2)             AS avg_order_value
FROM staging_sales
GROUP BY city, state, region
ORDER BY total_revenue DESC;

-- ══════════════════════════════════════════════════════════════
--   CATEGORY SUMMARY
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW v_category_summary AS
SELECT
    product_category,
    COUNT(DISTINCT product_name)                     AS product_count,
    COUNT(*)                                         AS total_orders,
    SUM(quantity)                                    AS total_units,
    ROUND(SUM(sales_amount)::NUMERIC, 2)             AS total_revenue,
    ROUND(AVG(sales_amount)::NUMERIC, 2)             AS avg_order_value,
    ROUND(MIN(price_per_unit)::NUMERIC, 2)           AS min_price,
    ROUND(MAX(price_per_unit)::NUMERIC, 2)           AS max_price
FROM staging_sales
GROUP BY product_category
ORDER BY total_revenue DESC;

-- ══════════════════════════════════════════════════════════════
--   PRODUCT PERFORMANCE
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW v_product_performance AS
SELECT
    product_name,
    product_category,
    COUNT(*)                                         AS total_orders,
    SUM(quantity)                                    AS total_units_sold,
    ROUND(SUM(sales_amount)::NUMERIC, 2)             AS total_revenue,
    ROUND(AVG(price_per_unit)::NUMERIC, 2)           AS avg_price,
    ROUND(AVG(sales_amount)::NUMERIC, 2)             AS avg_order_value,
    ROUND(
        (100.0 * SUM(sales_amount) / NULLIF(SUM(SUM(sales_amount)) OVER (), 0))::NUMERIC, 2
    )                                                AS revenue_share_pct
FROM staging_sales
GROUP BY product_name, product_category
ORDER BY total_revenue DESC;

-- ══════════════════════════════════════════════════════════════
--   TOP CUSTOMERS
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW v_top_customers AS
SELECT
    customer_name,
    city,
    state,
    region,
    COUNT(*)                                         AS total_orders,
    SUM(quantity)                                    AS total_quantity,
    ROUND(SUM(sales_amount)::NUMERIC, 2)             AS total_spent,
    ROUND(AVG(sales_amount)::NUMERIC, 2)             AS avg_order_value,
    MIN(sale_date)                                   AS first_purchase,
    MAX(sale_date)                                   AS last_purchase
FROM staging_sales
GROUP BY customer_name, city, state, region
ORDER BY total_spent DESC;

-- ══════════════════════════════════════════════════════════════
--   PRODUCT × REGION  (table 5)
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW v_product_region AS
SELECT
    product_name,
    product_category,
    region,
    SUM(quantity)                                    AS total_quantity,
    ROUND(SUM(sales_amount)::NUMERIC, 2)             AS total_revenue,
    ROUND(AVG(price_per_unit)::NUMERIC, 2)           AS avg_price
FROM staging_sales
GROUP BY product_name, product_category, region
ORDER BY total_revenue DESC;

-- ══════════════════════════════════════════════════════════════
--   PRODUCT × CITY  (table 6)
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW v_product_city AS
SELECT
    product_name,
    product_category,
    city,
    state,
    SUM(quantity)                                    AS total_quantity,
    ROUND(SUM(sales_amount)::NUMERIC, 2)             AS total_revenue,
    ROUND(AVG(price_per_unit)::NUMERIC, 2)           AS avg_price
FROM staging_sales
GROUP BY product_name, product_category, city, state
ORDER BY total_revenue DESC;

-- ══════════════════════════════════════════════════════════════
--   DATE × QUANTITY × REVENUE  (table 7)
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW v_date_summary AS
SELECT
    sale_date,
    COUNT(*)                                         AS order_count,
    SUM(quantity)                                    AS total_quantity,
    ROUND(SUM(sales_amount)::NUMERIC, 2)             AS total_revenue
FROM staging_sales
WHERE sale_date IS NOT NULL
GROUP BY sale_date
ORDER BY sale_date DESC;

-- ══════════════════════════════════════════════════════════════
--   DATE × REGION  (table 8)
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW v_date_region AS
SELECT
    sale_date,
    region,
    SUM(quantity)                                    AS total_quantity,
    ROUND(SUM(sales_amount)::NUMERIC, 2)             AS total_revenue,
    COUNT(*)                                         AS order_count
FROM staging_sales
WHERE sale_date IS NOT NULL
GROUP BY sale_date, region
ORDER BY sale_date DESC, total_revenue DESC;

-- ══════════════════════════════════════════════════════════════
--   DATE × CITY  (table 9)
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW v_date_city AS
SELECT
    sale_date,
    city,
    state,
    region,
    SUM(quantity)                                    AS total_quantity,
    ROUND(SUM(sales_amount)::NUMERIC, 2)             AS total_revenue,
    COUNT(*)                                         AS order_count
FROM staging_sales
WHERE sale_date IS NOT NULL
GROUP BY sale_date, city, state, region
ORDER BY sale_date DESC, total_revenue DESC;

-- ══════════════════════════════════════════════════════════════
--   REGION × MONTH HEATMAP  (for Plotly heatmap chart)
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW v_heatmap_region_month AS
SELECT
    region,
    TO_CHAR(sale_date, 'YYYY-MM')                    AS month,
    ROUND(SUM(sales_amount)::NUMERIC, 2)             AS revenue,
    SUM(quantity)                                    AS total_units
FROM staging_sales
WHERE sale_date IS NOT NULL AND region IS NOT NULL
GROUP BY region, TO_CHAR(sale_date, 'YYYY-MM')
ORDER BY month, region;

-- ══════════════════════════════════════════════════════════════
--   CUSTOMER HIERARCHY  (for Icicle/Tree chart)
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW v_customer_hierarchy AS
SELECT
    region,
    customer_name,
    SUM(quantity)                                    AS total_quantity,
    ROUND(SUM(sales_amount)::NUMERIC, 2)             AS total_spent,
    COUNT(*)                                         AS total_orders
FROM staging_sales
GROUP BY region, customer_name
ORDER BY total_spent DESC;

-- ══════════════════════════════════════════════════════════════
--   PIPELINE STATS
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW v_pipeline_stats AS
SELECT
    source_file,
    COUNT(*)                                         AS records_loaded,
    MIN(loaded_at)                                   AS first_loaded_at,
    MAX(loaded_at)                                   AS last_loaded_at,
    MIN(sale_date)                                   AS earliest_sale_date,
    MAX(sale_date)                                   AS latest_sale_date,
    ROUND(SUM(sales_amount)::NUMERIC, 2)             AS total_revenue,
    COUNT(DISTINCT customer_name)                    AS unique_customers
FROM staging_sales
GROUP BY source_file
ORDER BY first_loaded_at DESC;

-- ══════════════════════════════════════════════════════════════
DO $$ BEGIN
  RAISE NOTICE '✅ Sales Pipeline DB + Views initialised.';
END $$;