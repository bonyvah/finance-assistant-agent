from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.invoice import InvoiceStatus


class GetInvoiceArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_id: Annotated[int, Field(ge=1, description="Numeric invoice ID, e.g. 7")]


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor: str
    amount: Decimal
    currency: str
    issue_date: date
    due_date: date
    status: InvoiceStatus
    category: str | None


class InvoiceFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Annotated[
        InvoiceStatus | None,
        Field(
            description="Invoice payment status; use 'overdue' for unpaid invoices past their due date"
        ),
    ] = None
    vendor: Annotated[
        str | None,
        Field(
            max_length=100,
            description="Case-insensitive partial match on vendor name, e.g. 'aws'",
        ),
    ] = None
    min_amount: Annotated[
        Decimal | None,
        Field(
            ge=0,
            description="Only invoices with amount greater than or equal to this value",
        ),
    ] = None
    due_before: Annotated[
        date | None,
        Field(
            description="ISO date (YYYY-MM-DD). Only invoices due strictly before this date"
        ),
    ] = None
    limit: Annotated[
        int,
        Field(
            ge=1,
            le=100,
            description="Maximum number of invoices to return (1-100)",
        ),
    ] = 50


class GroupBy(StrEnum):
    VENDOR = "vendor"
    CATEGORY = "category"
    STATUS = "status"


class SpendSummaryArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_by: Annotated[
        GroupBy,
        Field(
            description="Dimension to group totals by: 'vendor', 'category' or 'status'"
        ),
    ]
    from_date: Annotated[
        date | None,
        Field(
            description="ISO date (YYYY-MM-DD). Only invoices issued on or after this date"
        ),
    ] = None
    to_date: Annotated[
        date | None,
        Field(
            description="ISO date (YYYY-MM-DD). Only invoices issued on or before this date"
        ),
    ] = None
    status: Annotated[
        InvoiceStatus | None,
        Field(
            description="Only count invoices with this status; use 'paid' for actual spend, omit for all"
        ),
    ] = None

    @model_validator(mode="after")
    def check_date_range(self) -> Self:
        if self.from_date and self.to_date and self.from_date > self.to_date:
            raise ValueError("from_date must be on or before to_date")
        return self


class SpendSummaryRow(BaseModel):
    key: str | None  # None = invoices with no category
    currency: str
    total: Decimal
    invoice_count: int


class SpendSummaryOut(BaseModel):
    group_by: GroupBy
    rows: list[SpendSummaryRow]
    totals: dict[
        str, Decimal
    ]  # grand total per currency, e.g. {"USD": Decimal("1234.50")}
