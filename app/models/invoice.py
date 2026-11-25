import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import Enum, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class InvoiceStatus(enum.StrEnum):
    PAID = "paid"
    UNPAID = "unpaid"
    OVERDUE = "overdue"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor: Mapped[str] = mapped_column(String(100), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    issue_date: Mapped[date]
    due_date: Mapped[date]
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), index=True)
    category: Mapped[str | None] = mapped_column(String(50))
