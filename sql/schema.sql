CREATE TABLE IF NOT EXISTS dim_customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    region VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS dim_products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS stg_sales (
    staging_id BIGSERIAL PRIMARY KEY,
    order_id TEXT,
    order_date TEXT,
    customer_id TEXT,
    product_id TEXT,
    quantity TEXT,
    unit_price TEXT,
    discount_rate TEXT,
    sales_channel TEXT,
    payment_method TEXT,
    region TEXT,
    source_file TEXT,
    source_row_number INTEGER,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_sales (
    order_id INTEGER PRIMARY KEY,
    order_date DATE NOT NULL,
    customer_id VARCHAR(50) NOT NULL REFERENCES dim_customers (customer_id),
    product_id VARCHAR(50) NOT NULL REFERENCES dim_products (product_id),
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    discount_rate NUMERIC(5, 4) NOT NULL,
    gross_sales NUMERIC(14, 2) NOT NULL,
    discount_amount NUMERIC(14, 2) NOT NULL,
    net_sales NUMERIC(14, 2) NOT NULL,
    sales_channel VARCHAR(100),
    payment_method VARCHAR(100),
    region VARCHAR(100),
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS etl_rejected_sales (
    rejected_id BIGSERIAL PRIMARY KEY,
    order_id TEXT,
    order_date TEXT,
    customer_id TEXT,
    product_id TEXT,
    quantity TEXT,
    unit_price TEXT,
    discount_rate TEXT,
    sales_channel TEXT,
    payment_method TEXT,
    region TEXT,
    source_file TEXT,
    source_row_number INTEGER,
    rejection_reason TEXT NOT NULL,
    rejected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
