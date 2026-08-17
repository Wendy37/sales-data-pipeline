from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from src.extractors import CSVExtractor, JSONExtractor
from src.loaders import DatabaseConnection, PostgresLoader, RejectedRecordWriter
from src.models import FactSalesRecord, RawSalesRecord, RejectedRecord
from src.transformers import SalesDataTransformer
from src.validators import SalesDataValidator


@dataclass
class PipelineResult:
    customer_count: int
    product_count: int
    raw_sales_count: int
    valid_sales_count: int
    rejected_sales_count: int
    fact_sales_count: int
    dry_run: bool


class SalesPipeline:
    def __init__(
        self,
        customers_path: str | Path = "data/raw/customers.json",
        products_path: str | Path = "data/raw/products.json",
        sales_path: str | Path = "data/raw/sales_2026_01.csv",
        rejected_output_path: str | Path = "data/rejected/rejected_sales.csv",
        database_url: str | None = None,
        schema_path: str | Path = "sql/schema.sql",
        dry_run: bool = False,
        sample_size: int = 5,
    ) -> None:
        self.customers_path = Path(customers_path)
        self.products_path = Path(products_path)
        self.sales_path = Path(sales_path)
        self.database_url = database_url
        self.schema_path = Path(schema_path)
        self.dry_run = dry_run
        self.sample_size = sample_size
        self.transformer = SalesDataTransformer()
        self.rejected_writer = RejectedRecordWriter(rejected_output_path)

    def run(self) -> PipelineResult:
        customer_rows = JSONExtractor(self.customers_path).extract()
        product_rows = JSONExtractor(self.products_path).extract()

        customers = self.transformer.transform_customers(customer_rows)
        products = self.transformer.transform_products(product_rows)

        raw_sales_records = CSVExtractor(self.sales_path).extract()

        validator = SalesDataValidator(customers, products)
        valid_sales_records, rejected_records = validator.validate(raw_sales_records)
        fact_sales_records = self.transformer.transform_sales(valid_sales_records)

        self.rejected_writer.write(rejected_records)

        result = PipelineResult(
            customer_count=len(customers),
            product_count=len(products),
            raw_sales_count=len(raw_sales_records),
            valid_sales_count=len(valid_sales_records),
            rejected_sales_count=len(rejected_records),
            fact_sales_count=len(fact_sales_records),
            dry_run=self.dry_run,
        )

        if self.dry_run:
            self._print_dry_run_summary(result, fact_sales_records, rejected_records)
            return result

        if not self.database_url:
            raise ValueError("database_url is required when dry_run is False")

        valid_source_records = self._valid_source_records(raw_sales_records, rejected_records)
        self._load_to_postgres(customers, products, valid_source_records, fact_sales_records, rejected_records)
        self._print_load_summary(result)
        return result

    def _load_to_postgres(
        self,
        customers,
        products,
        valid_source_records: Sequence[RawSalesRecord],
        fact_sales_records: Sequence[FactSalesRecord],
        rejected_records: Sequence[RejectedRecord],
    ) -> None:
        database = DatabaseConnection(self.database_url)
        loader = PostgresLoader(database, self.schema_path)

        try:
            with loader.transaction():
                loader.initialize_tables()
                loader.load_customers(customers)
                loader.load_products(products)
                loader.load_staging_sales(valid_source_records)
                loader.load_fact_sales(fact_sales_records)
                loader.load_rejected_sales(rejected_records)
        finally:
            database.close()

    def _valid_source_records(
        self,
        raw_sales_records: Sequence[RawSalesRecord],
        rejected_records: Sequence[RejectedRecord],
    ) -> list[RawSalesRecord]:
        rejected_record_ids = {id(record.raw_record) for record in rejected_records}
        return [
            record
            for record in raw_sales_records
            if id(record) not in rejected_record_ids
        ]

    def _print_dry_run_summary(
        self,
        result: PipelineResult,
        fact_sales_records: Sequence[FactSalesRecord],
        rejected_records: Sequence[RejectedRecord],
    ) -> None:
        print("Dry run complete. PostgreSQL was not contacted or modified.")
        print("Summary:")
        print(f"  Customers extracted: {result.customer_count}")
        print(f"  Products extracted: {result.product_count}")
        print(f"  Sales rows extracted: {result.raw_sales_count}")
        print(f"  Valid sales rows: {result.valid_sales_count}")
        print(f"  Rejected sales rows: {result.rejected_sales_count}")
        print(f"  Fact rows calculated: {result.fact_sales_count}")
        print(f"  Rejected rows written to: {self.rejected_writer.output_path}")

        if fact_sales_records:
            print(f"Sample transformed fact rows ({min(self.sample_size, len(fact_sales_records))}):")
            for record in fact_sales_records[: self.sample_size]:
                print(
                    "  "
                    f"order_id={record.order_id}, "
                    f"order_date={record.order_date}, "
                    f"customer_id={record.customer_id}, "
                    f"product_id={record.product_id}, "
                    f"quantity={record.quantity}, "
                    f"gross_sales={record.gross_sales}, "
                    f"discount_amount={record.discount_amount}, "
                    f"net_sales={record.net_sales}"
                )

        if rejected_records:
            print(f"Sample rejection reasons ({min(self.sample_size, len(rejected_records))}):")
            for record in rejected_records[: self.sample_size]:
                print(f"  row={record.row_number}, reason={record.reason}")

    def _print_load_summary(self, result: PipelineResult) -> None:
        print("ETL load complete.")
        print("Summary:")
        print(f"  Customers loaded: {result.customer_count}")
        print(f"  Products loaded: {result.product_count}")
        print(f"  Source sales rows extracted: {result.raw_sales_count}")
        print(f"  Valid fact rows loaded: {result.fact_sales_count}")
        print(f"  Rejected rows loaded: {result.rejected_sales_count}")
        print(f"  Rejected rows written to: {self.rejected_writer.output_path}")


SalesETLPipeline = SalesPipeline
