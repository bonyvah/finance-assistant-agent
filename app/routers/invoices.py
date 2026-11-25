from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.schemas.invoice import InvoiceFilters, InvoiceOut
from app.dependencies import SessionDep
from app.services import invoices as invoices_service

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("", response_model=list[InvoiceOut])
def list_invoices(session: SessionDep, filters: Annotated[InvoiceFilters, Query()]):
    return invoices_service.list_invoices(session, filters)


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: int, session: SessionDep):
    invoice = invoices_service.get_invoice(session, invoice_id)
    if invoice is None:
        raise HTTPException(404)
    return invoice
