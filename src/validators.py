import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from src.models import Customer, Product, RawSalesRecord, RejectedRecord, ValidSalesRecord


class SalesDataValidator:
    REQUIRED_FIELDS = (
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
    )

    DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    def __init__(
        self,
        customers: Iterable[Customer | dict[str, Any] | str],
        products: Iterable[Product | dict[str, Any] | str],
    ) -> None:
        self.customer_ids = self._extract_ids(customers, "customer_id")
        self.product_ids = self._extract_ids(products, "product_id")

    def validate(
        self, raw_records: Iterable[RawSalesRecord]
    ) -> tuple[list[ValidSalesRecord], list[RejectedRecord]]:
        valid_records: list[ValidSalesRecord] = []
        rejected_records: list[RejectedRecord] = []
        seen_order_ids: set[int] = set()

        for raw_record in raw_records:
            valid_record, rejection_reason = self._validate_record(raw_record, seen_order_ids)
            parsed_order_id = self._parse_int(raw_record.order_id)
            if parsed_order_id is not None:
                seen_order_ids.add(parsed_order_id)

            if valid_record is None:
                rejected_records.append(
                    RejectedRecord(
                        raw_record=raw_record,
                        reason=rejection_reason,
                        source_file=raw_record.source_file,
                        row_number=raw_record.row_number,
                    )
                )
                continue

            valid_records.append(valid_record)

        return valid_records, rejected_records

    def _validate_record(
        self, raw_record: RawSalesRecord, seen_order_ids: set[int]
    ) -> tuple[ValidSalesRecord | None, str]:
        errors: list[str] = []

        missing_fields = [
            field
            for field in self.REQUIRED_FIELDS
            if self._is_missing(getattr(raw_record, field))
        ]
        if missing_fields:
            errors.append(f"Missing required field(s): {', '.join(missing_fields)}")

        order_id = self._parse_int(raw_record.order_id)
        if order_id is None and not self._is_missing(raw_record.order_id):
            errors.append("order_id must be an integer")
        elif order_id in seen_order_ids:
            errors.append(f"Duplicate order_id: {order_id}")

        quantity = self._parse_int(raw_record.quantity)
        if quantity is None and not self._is_missing(raw_record.quantity):
            errors.append("quantity must be an integer")
        elif quantity is not None and quantity <= 0:
            errors.append("quantity must be greater than 0")

        order_date = self._parse_date(raw_record.order_date)
        if order_date is None and not self._is_missing(raw_record.order_date):
            errors.append("order_date must strictly match YYYY-MM-DD")

        unit_price = self._parse_decimal(raw_record.unit_price)
        if unit_price is None and not self._is_missing(raw_record.unit_price):
            errors.append("unit_price must be numeric")
        elif unit_price is not None and unit_price <= 0:
            errors.append("unit_price must be greater than 0")

        discount_rate = self._parse_decimal(raw_record.discount_rate)
        if discount_rate is None and not self._is_missing(raw_record.discount_rate):
            errors.append("discount_rate must be numeric")
        elif discount_rate is not None and not Decimal("0") <= discount_rate <= Decimal("1"):
            errors.append("discount_rate must be between 0 and 1")

        customer_id = self._clean_string(raw_record.customer_id)
        if customer_id and customer_id not in self.customer_ids:
            errors.append(f"Unknown customer_id: {customer_id}")

        product_id = self._clean_string(raw_record.product_id)
        if product_id and product_id not in self.product_ids:
            errors.append(f"Unknown product_id: {product_id}")

        sales_channel = self._clean_string(raw_record.sales_channel)
        payment_method = self._clean_string(raw_record.payment_method)
        region = self._clean_string(raw_record.region)

        if errors:
            return None, "; ".join(errors)

        return (
            ValidSalesRecord(
                order_id=order_id,
                order_date=order_date,
                customer_id=customer_id,
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
                discount_rate=discount_rate,
                sales_channel=sales_channel,
                payment_method=payment_method,
                region=region,
            ),
            "",
        )

    def _extract_ids(self, records: Iterable[Any], id_field: str) -> set[str]:
        ids: set[str] = set()

        for record in records:
            if isinstance(record, str):
                value = record
            elif isinstance(record, dict):
                value = record.get(id_field)
            else:
                value = getattr(record, id_field, None)

            cleaned_value = self._clean_string(value)
            if cleaned_value:
                ids.add(cleaned_value)

        return ids

    def _parse_int(self, value: Any) -> int | None:
        if self._is_missing(value):
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value

        text = str(value).strip()
        if not re.fullmatch(r"[+-]?\d+", text):
            return None

        return int(text)

    def _parse_decimal(self, value: Any) -> Decimal | None:
        if self._is_missing(value) or isinstance(value, bool):
            return None

        try:
            return Decimal(str(value).strip())
        except (InvalidOperation, ValueError):
            return None

    def _parse_date(self, value: Any):
        if self._is_missing(value):
            return None

        text = str(value).strip()
        if not self.DATE_PATTERN.fullmatch(text):
            return None

        try:
            return datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            return None

    def _clean_string(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _is_missing(self, value: Any) -> bool:
        return value is None or str(value).strip() == ""
