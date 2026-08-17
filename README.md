# Sales Data Pipeline - Wendi Tan

Object-oriented Python ETL pipeline for loading sales data into PostgreSQL.
The pipeline:

1. Extracts customer and product reference data from JSON.
2. Extracts sales records from CSV.
3. Validates sales records.
4. Separates valid and rejected rows.
5. Transforms valid sales into fact records.
6. Writes rejected records to a local CSV file.
7. Loads dimensions, staging rows, facts, and rejected rows into PostgreSQL.
8. Supports dry-run mode before database loading.

## Project Structure

```text
.
├── data/
│   ├── raw/
│   │   ├── customers.json
│   │   ├── products.json
│   │   └── sales_2026_01.csv
│   └── rejected/
│       └── rejected_sales.csv
├── sql/
│   ├── schema.sql
│   └── analytics.sql
├── src/
│   ├── extractors.py
│   ├── loaders.py
│   ├── models.py
│   ├── pipeline.py
│   ├── transformers.py
│   └── validators.py
├── docker-compose.yml
├── main.py
└── requirements.txt
```

## Main Classes

- `Extractor`, `CSVExtractor`, `JSONExtractor`: read input files.
- `SalesDataValidator`: validates raw sales records and returns valid/rejected collections.
- `SalesDataTransformer`: transforms reference data and calculates sales facts.
- `RejectedRecordWriter`: writes rejected rows to `data/rejected/rejected_sales.csv`.
- `DatabaseConnection`: manages PostgreSQL connections.
- `PostgresLoader`: initializes schema and loads data into PostgreSQL.
- `SalesPipeline`: coordinates the full ETL workflow.

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Dry Run

Use dry-run mode to verify extraction, validation, transformation, and rejected-row handling without connecting to PostgreSQL:

```bash
python main.py --dry-run
```

Expected demo-data summary:

```text
Raw rows: 23
Valid rows: 12
Rejected rows: 11
Loaded fact rows: 0
```

Rejected rows are written to:

```text
data/rejected/rejected_sales.csv
```

## PostgreSQL

Start the local PostgreSQL database:

```bash
docker compose up -d
```

Current local connection settings:

```text
database: sales_db
username: postgres
password: postgres
host: localhost
port: 5433
```

Run the full ETL load:

```bash
python main.py
```

Or pass a custom database URL:

```bash
python main.py --database-url postgresql://postgres:postgres@localhost:5433/sales_db
```

## Database Schema

The schema is defined in `sql/schema.sql` and creates:

- `dim_customers`
- `dim_products`
- `stg_sales`
- `fact_sales`
- `etl_rejected_sales`

The fact table uses foreign keys to customer and product dimensions.

## Analytics

After loading PostgreSQL, run:

```bash
psql postgresql://postgres:postgres@localhost:5433/sales_db -f sql/analytics.sql
```

The analytics script includes:

- row-count checks
- fact table inspection
- rejected-row inspection
- duplicate order checks
- missing product checks
- daily revenue
- top products
- top regions
- highest-LTV customer
- rejected-record summary

## Validation Rules

Sales rows are rejected when they contain:

- missing required fields
- non-integer `order_id`
- non-integer `quantity`
- invalid date format
- non-numeric `unit_price`
- non-numeric `discount_rate`
- `quantity <= 0`
- `unit_price <= 0`
- `discount_rate` outside `0` to `1`
- unknown `customer_id`
- unknown `product_id`
- duplicate `order_id`

Blank strings are treated as missing values.
