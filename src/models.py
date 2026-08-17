from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any


@dataclass
class Customer:
    customer_id: str
    first_name: str
    last_name: str
    email: str
    phone: str | None
    city: str
    state: str
    region: str
    country: str
    segment: str
    signup_date: date | None


@dataclass
class Product:
    product_id: str
    sku: str
    name: str
    category: str
    brand: str
    standard_price: Decimal
    active: bool


@dataclass
class RawSalesRecord:
    order_id: Any
    order_date: Any
    customer_id: Any
    product_id: Any
    quantity: Any
    unit_price: Any
    discount_rate: Any
    sales_channel: Any
    payment_method: Any
    region: Any
    source_file: str | None = None
    row_number: int | None = None


@dataclass
class ValidSalesRecord:
    order_id: int
    order_date: date
    customer_id: str
    product_id: str
    quantity: int
    unit_price: Decimal
    discount_rate: Decimal
    sales_channel: str
    payment_method: str
    region: str


@dataclass
class FactSalesRecord:
    order_id: int
    order_date: date
    customer_id: str
    product_id: str
    quantity: int
    unit_price: Decimal
    discount_rate: Decimal
    gross_sales: Decimal
    discount_amount: Decimal
    net_sales: Decimal
    sales_channel: str
    payment_method: str
    region: str
    loaded_at: datetime | None = None


@dataclass
class RejectedRecord:
    raw_record: RawSalesRecord
    reason: str
    source_file: str | None = None
    row_number: int | None = None
    rejected_at: datetime | None = None
