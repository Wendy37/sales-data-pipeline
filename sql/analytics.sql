-- Check row counts
SELECT COUNT(*) FROM dim_customers;
SELECT COUNT(*) FROM dim_products;
SELECT COUNT(*) FROM stg_sales;
SELECT COUNT(*) FROM fact_sales;
SELECT COUNT(*) FROM etl_rejected_sales;

-- Inspect factual table
SELECT *
FROM fact_sales
ORDER BY order_id;

-- Check rejected rows
SELECT *
FROM etl_rejected_sales
ORDER BY rejected_at;

-- Data-quality check
SELECT
    order_id,
    COUNT(*) AS cnt
FROM fact_sales
GROUP BY order_id
HAVING COUNT(*) > 1;

-- Missing products
SELECT f.*
FROM fact_sales f
LEFT JOIN dim_products p
    ON f.product_id = p.product_id
WHERE p.product_id IS NULL;

-- Analytics queries
-- 1. Daily revenue
SELECT
    order_date,
    SUM(net_sales) AS daily_revenue
FROM fact_sales
GROUP BY order_date
ORDER BY order_date;

-- 2. Top products
SELECT
    p.product_name,
    SUM(f.net_sales) AS total_revenue
FROM fact_sales f
JOIN dim_products p
    ON f.product_id = p.product_id
GROUP BY p.product_name
ORDER BY total_revenue DESC;

-- 3. Top regions in terms of total revenue
SELECT
    c.region,
    SUM(f.net_sales) AS total_revenue
FROM fact_sales f
JOIN dim_customers c
    ON f.customer_id = c.customer_id
GROUP BY c.region
ORDER BY total_revenue DESC;

-- 4. Highest-LTV customer
SELECT
    c.customer_id,
    c.customer_name,
    SUM(f.net_sales) AS lifetime_value
FROM fact_sales f
JOIN dim_customers c
    ON f.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY lifetime_value DESC
LIMIT 1;

-- 5. Rejected-record summary
SELECT
    rejection_reason,
    COUNT(*) AS rejected_count
FROM etl_rejected_sales
GROUP BY rejection_reason
ORDER BY rejected_count DESC;
