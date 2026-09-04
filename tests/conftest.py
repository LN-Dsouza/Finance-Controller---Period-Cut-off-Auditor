import datetime
import os
import tempfile
from typing import Optional

import pytest
from sqlalchemy.orm import Session

_fd, _TEST_DB = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"

from backend.database.connection import SessionLocal, init_db, engine
from backend.database.models import (
    Base, Transaction, PurchaseOrder, Shipment, GoodsReceipt, Invoice, Payment
)


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def add_goods_case(
    db: Session,
    tx_id: str,
    *,
    tx_date: str,
    posting_date: str,
    invoice_date: str,
    grn_date: Optional[str],
    ship_date: Optional[str],
    delivery_date: Optional[str],
    ledger_period: str = "December 2026",
    amount: float = 10000.0,
) -> Transaction:
    def dt(value: Optional[str]):
        return datetime.datetime.strptime(value, "%Y-%m-%d") if value else None

    tx = Transaction(
        transaction_id=tx_id,
        transaction_type="goods_purchase",
        amount=amount,
        currency="INR",
        transaction_date=dt(tx_date),
        posting_date=dt(posting_date),
        ledger_period=ledger_period,
        vendor_id="VEN-TEST",
        status="PENDING",
    )
    db.add(tx)
    po = PurchaseOrder(
        po_id=f"PO-{tx_id}",
        transaction_id=tx_id,
        vendor_id="VEN-TEST",
        po_date=dt(tx_date),
        amount=amount,
        description="Test PO",
    )
    db.add(po)
    if ship_date:
        db.add(Shipment(
            shipment_id=f"SHIP-{tx_id}",
            po_id=po.po_id,
            ship_date=dt(ship_date),
            delivery_date=dt(delivery_date),
            carrier="DHL",
        ))
    if grn_date:
        db.add(GoodsReceipt(
            grn_id=f"GRN-{tx_id}",
            po_id=po.po_id,
            receipt_date=dt(grn_date),
            quantity=1,
            received_by="Jane Doe",
        ))
    db.add(Invoice(
        invoice_id=f"INV-{tx_id}",
        transaction_id=tx_id,
        invoice_date=dt(invoice_date),
        amount=amount,
        vendor_id="VEN-TEST",
    ))
    db.add(Payment(
        payment_id=f"PAY-{tx_id}",
        transaction_id=tx_id,
        payment_date=dt("2027-01-10"),
        amount=amount,
        payment_method="Wire",
    ))
    db.commit()
    return tx
