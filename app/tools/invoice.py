from sqlalchemy.orm import Session

from app.schemas.invoice import (
    GetInvoiceArgs,
    InvoiceFilters,
    InvoiceOut,
    SpendSummaryArgs,
)
from app.services import invoices as invoices_service


def search_invoices(session: Session, filters: InvoiceFilters) -> dict:
    res = invoices_service.list_invoices(session, filters)
    invoices = [InvoiceOut.model_validate(i).model_dump(mode="json") for i in res]
    return {"count": len(invoices), "invoices": invoices}


def get_invoice(session: Session, args: GetInvoiceArgs) -> dict:
    invoice = invoices_service.get_invoice(session, args.invoice_id)
    if invoice is None:
        return {"found": False, "invoice_id": args.invoice_id}
    return {
        "found": True,
        "invoice": InvoiceOut.model_validate(invoice).model_dump(mode="json"),
    }


def summarize_spend(session: Session, args: SpendSummaryArgs) -> dict:
    summary = invoices_service.summarize_spend(session, args)
    return {"summary": summary.model_dump(mode="json")}
