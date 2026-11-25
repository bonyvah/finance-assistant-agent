from dataclasses import dataclass
from collections.abc import Callable

from pydantic import BaseModel

from app.schemas.invoice import GetInvoiceArgs, InvoiceFilters, SpendSummaryArgs
from app.tools.invoice import get_invoice, search_invoices, summarize_spend


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args_model: type[BaseModel]
    fn: Callable


_TOOL_LIST = [
    Tool(
        name="get_invoice",
        description=(
            "Fetch one invoice by its numeric ID. Use when the user names a specific "
            "invoice number. Returns found=false if it doesn't exist."
        ),
        args_model=GetInvoiceArgs,
        fn=get_invoice,
    ),
    Tool(
        name="search_invoices",
        description=(
            "List invoices filtered by status, vendor, minimum amount or due date, "
            "sorted by due date (soonest first). Use for questions like 'what's overdue' "
            "or 'show my AWS invoices'. Do not use for totals; use summarize_spend."
        ),
        args_model=InvoiceFilters,
        fn=search_invoices,
    ),
    Tool(
        name="summarize_spend",
        description=(
            "Compute total spend and invoice counts grouped by vendor, category or "
            "status, optionally within an issue-date range and for one status. Totals "
            "are per currency. Use for any 'how much' or 'biggest expense' question; "
            "never add up amounts yourself."
        ),
        args_model=SpendSummaryArgs,
        fn=summarize_spend,
    ),
]

TOOLS = {t.name: t for t in _TOOL_LIST}
