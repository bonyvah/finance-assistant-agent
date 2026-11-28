from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.schemas.invoice import (
    InvoiceFilters,
    SpendSummaryArgs,
    SpendSummaryOut,
    GroupBy,
    SpendSummaryRow,
)


def list_invoices(session: Session, filters: InvoiceFilters) -> Sequence[Invoice]:
    stmt = select(Invoice)
    if filters.status:
        stmt = stmt.where(Invoice.status == filters.status)
    if filters.vendor:
        stmt = stmt.where(Invoice.vendor.ilike(f"%{filters.vendor}%"))
    if filters.min_amount is not None:
        stmt = stmt.where(Invoice.amount >= filters.min_amount)
    if filters.due_before:
        stmt = stmt.where(Invoice.due_date < filters.due_before)
    return session.scalars(stmt.order_by(Invoice.due_date).limit(filters.limit)).all()


def get_invoice(session: Session, invoice_id: int) -> Invoice | None:
    return session.get(Invoice, invoice_id)


GROUP_COLUMNS = {
    GroupBy.VENDOR: Invoice.vendor,
    GroupBy.CATEGORY: Invoice.category,
    GroupBy.STATUS: Invoice.status,
}


def summarize_spend(session: Session, args: SpendSummaryArgs) -> SpendSummaryOut:
    col = GROUP_COLUMNS[args.group_by]
    total = func.sum(Invoice.amount).label("total")
    stmt = select(
        col.label("key"),
        Invoice.currency,
        total,
        func.count(Invoice.id).label("invoice_count"),
    )
    if args.status:
        stmt = stmt.where(Invoice.status == args.status)
    if args.from_date:
        stmt = stmt.where(Invoice.issue_date >= args.from_date)
    if args.to_date:
        stmt = stmt.where(Invoice.issue_date <= args.to_date)
    stmt = stmt.group_by(col, Invoice.currency).order_by(desc("total"))

    rows = []
    totals = {}
    for r in session.execute(stmt):
        rows.append(
            SpendSummaryRow(
                key=r.key,
                currency=r.currency,
                total=r.total,
                invoice_count=r.invoice_count,
            )
        )
        totals[r.currency] = totals.get(r.currency, Decimal(0)) + r.total
    return SpendSummaryOut(group_by=args.group_by, rows=rows, totals=totals)
