from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.invoice import InvoiceStatus
from app.schemas.invoice import GroupBy, InvoiceFilters, SpendSummaryArgs
from app.services import invoices as svc


def ids(invoices):
    return [i.id for i in invoices]


# ---------- list_invoices ----------

def test_list_no_filters_returns_all_sorted_by_due_date(db_session, sample_invoices):
    result = svc.list_invoices(db_session, InvoiceFilters())
    assert ids(result) == [1, 3, 6, 2, 5, 4]


@pytest.mark.parametrize(
    "filters, expected",
    [
        ({"status": "paid"}, {1, 4, 5}),
        ({"vendor": "aws"}, {1, 2}),  # case-insensitive partial
        ({"vendor": "ws"}, {1, 2}),
        ({"min_amount": "250.50"}, {2, 5}),  # inclusive
        ({"due_before": "2026-03-03"}, {1, 3}),  # strict: id 6 is due ON 03-03
        ({"status": "unpaid", "vendor": "aws"}, {2}),  # combo
        ({"vendor": "nobody"}, set()),  # empty
    ],
)
def test_list_filters(db_session, sample_invoices, filters, expected):
    result = svc.list_invoices(db_session, InvoiceFilters(**filters))
    assert set(ids(result)) == expected


def test_list_limit_keeps_earliest_due(db_session, sample_invoices):
    result = svc.list_invoices(db_session, InvoiceFilters(limit=2))
    assert ids(result) == [1, 3]


@pytest.mark.parametrize(
    "bad",
    [{"min_amount": -5}, {"limit": 0}, {"limit": 101}, {"status": "lost"}, {"foo": 1}],
)
def test_filters_reject_bad_input(bad):
    with pytest.raises(ValidationError):
        InvoiceFilters(**bad)


# ---------- get_invoice ----------

def test_get_invoice_found(db_session, sample_invoices):
    inv = svc.get_invoice(db_session, 5)
    assert inv is not None and inv.vendor == "Lenovo"


def test_get_invoice_missing_returns_none(db_session, sample_invoices):
    assert svc.get_invoice(db_session, 999) is None


# ---------- summarize_spend ----------

def rows_by_key(summary):
    return {(r.key, r.currency): (r.total, r.invoice_count) for r in summary.rows}


def test_summary_by_vendor(db_session, sample_invoices):
    s = svc.summarize_spend(db_session, SpendSummaryArgs(group_by=GroupBy.VENDOR))
    rows = rows_by_key(s)
    assert rows[("AWS", "USD")] == (Decimal("350.50"), 2)
    assert rows[("Hetzner", "EUR")] == (Decimal("80.00"), 1)
    assert s.totals == {"USD": Decimal("2407.49"), "EUR": Decimal("80.00")}
    # biggest first
    assert s.rows[0].key == "Lenovo"


def test_summary_totals_equal_sum_of_rows(db_session, sample_invoices):
    s = svc.summarize_spend(db_session, SpendSummaryArgs(group_by=GroupBy.STATUS))
    for cur, total in s.totals.items():
        assert total == sum(r.total for r in s.rows if r.currency == cur)


def test_summary_null_category_is_own_group(db_session, sample_invoices):
    s = svc.summarize_spend(db_session, SpendSummaryArgs(group_by=GroupBy.CATEGORY))
    assert rows_by_key(s)[(None, "USD")] == (Decimal("12.00"), 1)


def test_summary_currencies_never_mix(db_session, sample_invoices):
    s = svc.summarize_spend(db_session, SpendSummaryArgs(group_by=GroupBy.CATEGORY))
    rows = rows_by_key(s)
    assert rows[("cloud", "USD")] == (Decimal("350.50"), 2)
    assert rows[("cloud", "EUR")] == (Decimal("80.00"), 1)


def test_summary_status_filter(db_session, sample_invoices):
    s = svc.summarize_spend(
        db_session, SpendSummaryArgs(group_by=GroupBy.VENDOR, status=InvoiceStatus.PAID)
    )
    assert s.totals == {"USD": Decimal("2111.99")}


def test_summary_date_range_is_inclusive(db_session, sample_invoices):
    s = svc.summarize_spend(
        db_session,
        SpendSummaryArgs(
            group_by=GroupBy.VENDOR, from_date=date(2026, 2, 1), to_date=date(2026, 2, 15)
        ),
    )
    # ids 6 (issued 02-01), 2 (02-10), 5 (02-15)
    assert s.totals == {"USD": Decimal("2250.49"), "EUR": Decimal("80.00")}


def test_summary_empty_range(db_session, sample_invoices):
    s = svc.summarize_spend(
        db_session,
        SpendSummaryArgs(group_by=GroupBy.VENDOR, from_date=date(2030, 1, 1)),
    )
    assert s.rows == [] and s.totals == {}


def test_summary_rejects_inverted_range():
    with pytest.raises(ValidationError):
        SpendSummaryArgs(
            group_by=GroupBy.VENDOR, from_date=date(2026, 3, 1), to_date=date(2026, 1, 1)
        )
