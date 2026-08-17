from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Iterable

from src.models import Customer, FactSalesRecord, Product, ValidSalesRecord


class TransformationError(Exception):
    """Raised when extracted reference data cannot be transformed."""


class SalesDataTransformer:
    MONEY_SCALE = Decimal("0.01")

    def transform_customers(self, customer_records: Iterable[dict[str, Any]]) -> list[Customer]:
        return [self.transform_customer(record) for record in customer_records]

    def transform_products(self, product_records: Iterable[dict[str, Any]]) -> list[Product]:
        return [self.transform_product(record) for record in product_records]

    def transform_sales(self, sales_records: Iterable[ValidSalesRecord]) -> list[FactSalesRecord]:
        return [self.transform_sale(record) for record in sales_records]

    def transform_customer(self, record: dict[str, Any]) -> Customer:
        try:
            return Customer(
                customer_id=str(record["customer_id"]).strip(),
                first_name=str(record["first_name"]).strip(),
                last_name=str(record["last_name"]).strip(),
                email=str(record["email"]).strip(),
                phone=self._optional_string(record.get("phone")),
                city=str(record["city"]).strip(),
                state=str(record["state"]).strip(),
                region=str(record["region"]).strip(),
                country=str(record["country"]).strip(),
                segment=str(record["segment"]).strip(),
                signup_date=self._parse_optional_date(record.get("signup_date")),
            )
        except KeyError as exc:
            raise TransformationError(f"Customer record is missing field: {exc.args[0]}") from exc

    def transform_product(self, record: dict[str, Any]) -> Product:
        try:
            return Product(
                product_id=str(record["product_id"]).strip(),
                sku=str(record["sku"]).strip(),
                name=str(record["name"]).strip(),
                category=str(record["category"]).strip(),
                brand=str(record["brand"]).strip(),
                standard_price=self._parse_decimal(record["standard_price"], "standard_price"),
                active=bool(record["active"]),
            )
        except KeyError as exc:
            raise TransformationError(f"Product record is missing field: {exc.args[0]}") from exc

    def transform_sale(self, record: ValidSalesRecord) -> FactSalesRecord:
        gross_sales = self._round_money(record.quantity * record.unit_price)
        discount_amount = self._round_money(gross_sales * record.discount_rate)
        net_sales = self._round_money(gross_sales - discount_amount)

        return FactSalesRecord(
            order_id=record.order_id,
            order_date=record.order_date,
            customer_id=record.customer_id,
            product_id=record.product_id,
            quantity=record.quantity,
            unit_price=record.unit_price,
            discount_rate=record.discount_rate,
            gross_sales=gross_sales,
            discount_amount=discount_amount,
            net_sales=net_sales,
            sales_channel=record.sales_channel,
            payment_method=record.payment_method,
            region=record.region,
        )

    def _parse_decimal(self, value: Any, field_name: str) -> Decimal:
        try:
            return Decimal(str(value).strip())
        except (InvalidOperation, ValueError, AttributeError) as exc:
            raise TransformationError(f"{field_name} must be numeric") from exc

    def _parse_optional_date(self, value: Any):
        if value is None or str(value).strip() == "":
            return None

        try:
            return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
        except ValueError as exc:
            raise TransformationError("signup_date must use YYYY-MM-DD format") from exc

    def _optional_string(self, value: Any) -> str | None:
        if value is None or str(value).strip() == "":
            return None
        return str(value).strip()

    def _round_money(self, value: Decimal) -> Decimal:
        return value.quantize(self.MONEY_SCALE, rounding=ROUND_HALF_UP)
