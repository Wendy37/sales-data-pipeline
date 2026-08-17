import argparse

from src.pipeline import SalesPipeline


DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/sales_db"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the sales ETL pipeline.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run extraction, validation, transformation, and rejected-file output without PostgreSQL writes.",
    )
    parser.add_argument(
        "--database-url",
        default=DEFAULT_DATABASE_URL,
        help="PostgreSQL connection URL used when --dry-run is not set.",
    )
    parser.add_argument(
        "--customers",
        default="data/raw/customers.json",
        help="Path to the customers JSON input file.",
    )
    parser.add_argument(
        "--products",
        default="data/raw/products.json",
        help="Path to the products JSON input file.",
    )
    parser.add_argument(
        "--sales",
        default="data/raw/sales_2026_01.csv",
        help="Path to the sales CSV input file.",
    )
    return parser.parse_args()


def print_run_summary(result) -> None:
    print("Run summary:")
    print(f"  Raw rows: {result.raw_sales_count}")
    print(f"  Valid rows: {result.valid_sales_count}")
    print(f"  Rejected rows: {result.rejected_sales_count}")
    print(f"  Loaded fact rows: {0 if result.dry_run else result.fact_sales_count}")


def main() -> None:
    args = parse_args()

    pipeline = SalesPipeline(
        customers_path=args.customers,
        products_path=args.products,
        sales_path=args.sales,
        database_url=args.database_url,
        dry_run=args.dry_run,
    )
    result = pipeline.run()
    print_run_summary(result)


if __name__ == "__main__":
    main()
