import csv
import json
from abc import ABC, abstractmethod
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from src.models import RawSalesRecord


class ExtractionError(Exception):
    """Raised when a source file cannot be read or parsed."""


class Extractor(ABC):
    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)

    @abstractmethod
    def extract(self) -> list[Any]:
        pass

    def _ensure_file_exists(self) -> None:
        if not self.file_path.exists():
            raise ExtractionError(f"File not found: {self.file_path}")
        if not self.file_path.is_file():
            raise ExtractionError(f"Path is not a file: {self.file_path}")


class CSVExtractor(Extractor):
    def extract(self) -> list[RawSalesRecord]:
        self._ensure_file_exists()

        try:
            with self.file_path.open("r", encoding="utf-8", newline="") as file:
                reader = csv.DictReader(file)
                if reader.fieldnames is None:
                    raise ExtractionError(f"CSV file is missing a header row: {self.file_path}")

                records = []
                for row_number, row in enumerate(reader, start=2):
                    records.append(
                        RawSalesRecord(
                            order_id=row.get("order_id"),
                            order_date=row.get("order_date"),
                            customer_id=row.get("customer_id"),
                            product_id=row.get("product_id"),
                            quantity=row.get("quantity"),
                            unit_price=row.get("unit_price"),
                            discount_rate=row.get("discount_rate"),
                            sales_channel=row.get("sales_channel"),
                            payment_method=row.get("payment_method"),
                            region=row.get("region"),
                            source_file=str(self.file_path),
                            row_number=row_number,
                        )
                    )

                return records
        except OSError as exc:
            raise ExtractionError(f"Could not read CSV file {self.file_path}: {exc}") from exc
        except csv.Error as exc:
            raise ExtractionError(f"Malformed CSV file {self.file_path}: {exc}") from exc


class JSONExtractor(Extractor):
    def extract(self) -> list[dict[str, Any]]:
        self._ensure_file_exists()

        try:
            with self.file_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError as exc:
            raise ExtractionError(f"File not found: {self.file_path}") from exc
        except JSONDecodeError as exc:
            raise ExtractionError(f"Malformed JSON file {self.file_path}: {exc}") from exc
        except OSError as exc:
            raise ExtractionError(f"Could not read JSON file {self.file_path}: {exc}") from exc

        if not isinstance(data, list):
            raise ExtractionError(f"Expected JSON list in {self.file_path}")

        for index, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                raise ExtractionError(
                    f"Expected JSON object at item {index} in {self.file_path}"
                )

        return data
