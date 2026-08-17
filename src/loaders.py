import csv
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable

from src.models import Customer, FactSalesRecord, Product, RawSalesRecord, RejectedRecord

try:
    import psycopg
except ModuleNotFoundError:
    psycopg = None


class LoaderError(Exception):
    """Raised when data cannot be loaded."""


class DatabaseConnection:
    def __init__(self, conninfo: str) -> None:
        self.conninfo = conninfo
        self.connection = None

    def open(self):
        if psycopg is None:
            raise LoaderError("psycopg is not installed. Run: pip install -r requirements.txt")

        if self.connection is None or self.connection.closed:
            self.connection = psycopg.connect(self.conninfo)
        return self.connection

    def commit(self) -> None:
        if self.connection is not None:
            self.connection.commit()

    def rollback(self) -> None:
        if self.connection is not None:
            self.connection.rollback()

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()


class RejectedRecordWriter:
    FIELDNAMES = [
        "order_id",
        "order_date",
        "customer_id",
        "product_id",
        "quantity",
        "unit_price",
        "discount_rate",
        "sales_channel",
        "payment_method",
        "region",
        "source_file",
        "source_row_number",
        "rejection_reason",
    ]

    def __init__(self, output_path: str | Path = "data/rejected/rejected_sales.csv") -> None:
        self.output_path = Path(output_path)

    def write(self, rejected_records: Iterable[RejectedRecord]) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        with self.output_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=self.FIELDNAMES)
            writer.writeheader()

            for rejected_record in rejected_records:
                raw_record = rejected_record.raw_record
                writer.writerow(
                    {
                        "order_id": raw_record.order_id,
                        "order_date": raw_record.order_date,
                        "customer_id": raw_record.customer_id,
                        "product_id": raw_record.product_id,
                        "quantity": raw_record.quantity,
                        "unit_price": raw_record.unit_price,
                        "discount_rate": raw_record.discount_rate,
                        "sales_channel": raw_record.sales_channel,
                        "payment_method": raw_record.payment_method,
                        "region": raw_record.region,
                        "source_file": rejected_record.source_file or raw_record.source_file,
                        "source_row_number": rejected_record.row_number or raw_record.row_number,
                        "rejection_reason": rejected_record.reason,
                    }
                )


class PostgresLoader:
    def __init__(
        self,
        database: DatabaseConnection,
        schema_path: str | Path = "sql/schema.sql",
    ) -> None:
        self.database = database
        self.schema_path = Path(schema_path)
        self._transaction_depth = 0

    @contextmanager
    def transaction(self):
        self.database.open()
        self._transaction_depth += 1

        try:
            yield self
            if self._transaction_depth == 1:
                self.database.commit()
        except Exception as exc:
            if self._transaction_depth == 1:
                self.database.rollback()
            if psycopg is not None and isinstance(exc, psycopg.Error):
                raise LoaderError(f"Database load failed: {exc}") from exc
            raise
        finally:
            self._transaction_depth -= 1

    def initialize_tables(self) -> None:
        if not self.schema_path.exists():
            raise LoaderError(f"Schema file not found: {self.schema_path}")

        schema_sql = self.schema_path.read_text(encoding="utf-8")
        self._execute_in_transaction(lambda cursor: cursor.execute(schema_sql))

    def load_customers(self, customers: Iterable[Customer]) -> None:
        sql = """
            INSERT INTO dim_customers (customer_id, customer_name, region)
            VALUES (%s, %s, %s)
            ON CONFLICT (customer_id) DO UPDATE SET
                customer_name = EXCLUDED.customer_name,
                region = EXCLUDED.region
        """

        values = [
            (
                customer.customer_id,
                f"{customer.first_name} {customer.last_name}",
                customer.region,
            )
            for customer in customers
        ]

        self._executemany_in_transaction(sql, values)

    def load_products(self, products: Iterable[Product]) -> None:
        sql = """
            INSERT INTO dim_products (product_id, product_name, category)
            VALUES (%s, %s, %s)
            ON CONFLICT (product_id) DO UPDATE SET
                product_name = EXCLUDED.product_name,
                category = EXCLUDED.category
        """

        values = [
            (
                product.product_id,
                product.name,
                product.category,
            )
            for product in products
        ]

        self._executemany_in_transaction(sql, values)

    def load_staging_sales(self, sales_records: Iterable[RawSalesRecord]) -> None:
        sql = """
            INSERT INTO stg_sales (
                order_id,
                order_date,
                customer_id,
                product_id,
                quantity,
                unit_price,
                discount_rate,
                sales_channel,
                payment_method,
                region,
                source_file,
                source_row_number
            )
            SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            WHERE NOT EXISTS (
                SELECT 1
                FROM stg_sales
                WHERE source_file IS NOT DISTINCT FROM %s
                    AND source_row_number IS NOT DISTINCT FROM %s
            )
        """

        values = [
            (
                record.order_id,
                record.order_date,
                record.customer_id,
                record.product_id,
                record.quantity,
                record.unit_price,
                record.discount_rate,
                record.sales_channel,
                record.payment_method,
                record.region,
                record.source_file,
                record.row_number,
                record.source_file,
                record.row_number,
            )
            for record in sales_records
        ]

        self._executemany_in_transaction(sql, values)

    def load_fact_sales(self, fact_records: Iterable[FactSalesRecord]) -> None:
        sql = """
            INSERT INTO fact_sales (
                order_id,
                order_date,
                customer_id,
                product_id,
                quantity,
                unit_price,
                discount_rate,
                gross_sales,
                discount_amount,
                net_sales,
                sales_channel,
                payment_method,
                region,
                loaded_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP))
            ON CONFLICT (order_id) DO UPDATE SET
                order_date = EXCLUDED.order_date,
                customer_id = EXCLUDED.customer_id,
                product_id = EXCLUDED.product_id,
                quantity = EXCLUDED.quantity,
                unit_price = EXCLUDED.unit_price,
                discount_rate = EXCLUDED.discount_rate,
                gross_sales = EXCLUDED.gross_sales,
                discount_amount = EXCLUDED.discount_amount,
                net_sales = EXCLUDED.net_sales,
                sales_channel = EXCLUDED.sales_channel,
                payment_method = EXCLUDED.payment_method,
                region = EXCLUDED.region,
                loaded_at = EXCLUDED.loaded_at
        """

        values = [
            (
                record.order_id,
                record.order_date,
                record.customer_id,
                record.product_id,
                record.quantity,
                record.unit_price,
                record.discount_rate,
                record.gross_sales,
                record.discount_amount,
                record.net_sales,
                record.sales_channel,
                record.payment_method,
                record.region,
                record.loaded_at,
            )
            for record in fact_records
        ]

        self._executemany_in_transaction(sql, values)

    def load_rejected_sales(self, rejected_records: Iterable[RejectedRecord]) -> None:
        sql = """
            INSERT INTO etl_rejected_sales (
                order_id,
                order_date,
                customer_id,
                product_id,
                quantity,
                unit_price,
                discount_rate,
                sales_channel,
                payment_method,
                region,
                source_file,
                source_row_number,
                rejection_reason,
                rejected_at
            )
            SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP)
            WHERE NOT EXISTS (
                SELECT 1
                FROM etl_rejected_sales
                WHERE source_file IS NOT DISTINCT FROM %s
                    AND source_row_number IS NOT DISTINCT FROM %s
                    AND rejection_reason = %s
            )
        """

        values = []
        for rejected_record in rejected_records:
            raw_record = rejected_record.raw_record
            values.append(
                (
                    raw_record.order_id,
                    raw_record.order_date,
                    raw_record.customer_id,
                    raw_record.product_id,
                    raw_record.quantity,
                    raw_record.unit_price,
                    raw_record.discount_rate,
                    raw_record.sales_channel,
                    raw_record.payment_method,
                    raw_record.region,
                    rejected_record.source_file or raw_record.source_file,
                    rejected_record.row_number or raw_record.row_number,
                    rejected_record.reason,
                    rejected_record.rejected_at,
                    rejected_record.source_file or raw_record.source_file,
                    rejected_record.row_number or raw_record.row_number,
                    rejected_record.reason,
                )
            )

        self._executemany_in_transaction(sql, values)

    def _execute_in_transaction(self, operation) -> None:
        connection = self.database.open()

        if self._transaction_depth > 0:
            with connection.cursor() as cursor:
                operation(cursor)
            return

        try:
            with connection.cursor() as cursor:
                operation(cursor)
            self.database.commit()
        except Exception as exc:
            self.database.rollback()
            if psycopg is not None and isinstance(exc, psycopg.Error):
                raise LoaderError(f"Database load failed: {exc}") from exc
            raise

    def _executemany_in_transaction(self, sql: str, values: list[tuple]) -> None:
        if not values:
            return

        self._execute_in_transaction(lambda cursor: cursor.executemany(sql, values))
