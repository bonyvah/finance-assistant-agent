import random
from datetime import date, timedelta
from decimal import Decimal

from app.db import Base, SessionLocal, engine
from app.models.invoice import Invoice, InvoiceStatus

VENDORS = ["AWS", "Azure", "OpenAI", "Figma", "Notion", "WeWork", "Lenovo", "Slack"]
CATEGORIES = ["cloud", "software", "office", "hardware", None]


def seed(n: int = 20) -> None:
    random.seed(42)  # reproducible data
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    today = date.today()

    with SessionLocal() as s:
        for _ in range(n):
            issue = today - timedelta(days=random.randint(0, 90))
            due = issue + timedelta(days=30)
            if random.random() < 0.4:
                status = InvoiceStatus.PAID
            else:
                status = InvoiceStatus.OVERDUE if due < today else InvoiceStatus.UNPAID
            s.add(
                Invoice(
                    vendor=random.choice(VENDORS),
                    amount=Decimal(random.randint(1_000, 500_000)) / 100,
                    currency="USD",
                    issue_date=issue,
                    due_date=due,
                    status=status,
                    category=random.choice(CATEGORIES),
                )
            )
        s.commit()
    print(f"seeded {n} invoices")


if __name__ == "__main__":
    seed()
