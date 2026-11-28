import os

# Must run before any `app` import: app.config builds Settings() at import time.
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite://")

from datetime import date  # noqa: E402
from decimal import Decimal  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models.invoice  # noqa: E402, F401  (registers tables on Base.metadata)
from app.db import Base, get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models.invoice import Invoice, InvoiceStatus  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# Fixed dates + known amounts so every expected number below is hand-checkable.
SAMPLE = [
    # id, vendor, amount, currency, issue, due, status, category
    (1, "AWS", "100.00", "USD", date(2026, 1, 5), date(2026, 2, 4), InvoiceStatus.PAID, "cloud"),
    (2, "AWS", "250.50", "USD", date(2026, 2, 10), date(2026, 3, 12), InvoiceStatus.UNPAID, "cloud"),
    (3, "Figma", "45.00", "USD", date(2026, 1, 20), date(2026, 2, 19), InvoiceStatus.OVERDUE, "software"),
    (4, "Notion", "12.00", "USD", date(2026, 3, 1), date(2026, 3, 31), InvoiceStatus.PAID, None),
    (5, "Lenovo", "1999.99", "USD", date(2026, 2, 15), date(2026, 3, 17), InvoiceStatus.PAID, "hardware"),
    (6, "Hetzner", "80.00", "EUR", date(2026, 2, 1), date(2026, 3, 3), InvoiceStatus.UNPAID, "cloud"),
]


@pytest.fixture
def sample_invoices(db_session):
    rows = [
        Invoice(
            id=i, vendor=v, amount=Decimal(a), currency=c,
            issue_date=iss, due_date=due, status=st, category=cat,
        )
        for i, v, a, c, iss, due, st, cat in SAMPLE
    ]
    db_session.add_all(rows)
    db_session.flush()
    return rows


@pytest.fixture
def client(db_session, sample_invoices):
    def override():
        yield db_session

    app.dependency_overrides[get_session] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
