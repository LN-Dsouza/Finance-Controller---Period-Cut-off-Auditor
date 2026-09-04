from sqlalchemy import Column, String, Float, DateTime, Integer, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()

class Transaction(Base):
    __tablename__ = "transactions"
    
    transaction_id = Column(String, primary_key=True)
    transaction_type = Column(String, nullable=False)  # 'goods_purchase', 'service_purchase', 'revenue_goods', 'revenue_services'
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    transaction_date = Column(DateTime, nullable=False)  # When the request/deal was initiated
    posting_date = Column(DateTime, nullable=False)      # When it was entered into general ledger
    ledger_period = Column(String, nullable=False)       # e.g., 'December 2026', 'January 2027'
    vendor_id = Column(String, nullable=True)
    customer_id = Column(String, nullable=True)
    status = Column(String, default="PENDING")          # 'PENDING', 'AUDITED', 'REJECTED'

    # Relationships
    purchase_orders = relationship("PurchaseOrder", back_populates="transaction", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="transaction", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="transaction", cascade="all, delete-orphan")
    service_records = relationship("ServiceRecord", back_populates="transaction", cascade="all, delete-orphan")
    contracts = relationship("Contract", back_populates="transaction", cascade="all, delete-orphan")
    evidences = relationship("Evidence", back_populates="transaction", cascade="all, delete-orphan")
    investigations = relationship("Investigation", back_populates="transaction", cascade="all, delete-orphan")
    reviews = relationship("HumanReview", back_populates="transaction", cascade="all, delete-orphan")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    
    po_id = Column(String, primary_key=True)
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), nullable=False)
    vendor_id = Column(String, nullable=False)
    po_date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=True)

    transaction = relationship("Transaction", back_populates="purchase_orders")
    shipments = relationship("Shipment", back_populates="purchase_order", cascade="all, delete-orphan")
    goods_receipts = relationship("GoodsReceipt", back_populates="purchase_order", cascade="all, delete-orphan")


class Shipment(Base):
    __tablename__ = "shipments"
    
    shipment_id = Column(String, primary_key=True)
    po_id = Column(String, ForeignKey("purchase_orders.po_id"), nullable=False)
    ship_date = Column(DateTime, nullable=False)
    delivery_date = Column(DateTime, nullable=True)     # Actual delivery date (can be null if lost/in-transit)
    carrier = Column(String, nullable=True)

    purchase_order = relationship("PurchaseOrder", back_populates="shipments")


class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"
    
    grn_id = Column(String, primary_key=True)
    po_id = Column(String, ForeignKey("purchase_orders.po_id"), nullable=False)
    receipt_date = Column(DateTime, nullable=False)
    quantity = Column(Integer, default=1)
    received_by = Column(String, nullable=True)

    purchase_order = relationship("PurchaseOrder", back_populates="goods_receipts")


class Invoice(Base):
    __tablename__ = "invoices"
    
    invoice_id = Column(String, primary_key=True)
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), nullable=False)
    invoice_date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    tax = Column(Float, default=0.0)
    vendor_id = Column(String, nullable=False)

    transaction = relationship("Transaction", back_populates="invoices")


class Payment(Base):
    __tablename__ = "payments"
    
    payment_id = Column(String, primary_key=True)
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), nullable=False)
    payment_date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String, nullable=True)

    transaction = relationship("Transaction", back_populates="payments")


class ServiceRecord(Base):
    __tablename__ = "service_records"
    
    service_id = Column(String, primary_key=True)
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), nullable=False)
    service_start = Column(DateTime, nullable=False)
    service_end = Column(DateTime, nullable=False)
    completion_status = Column(String, nullable=False)  # 'COMPLETED', 'IN_PROGRESS', 'FAILED'

    transaction = relationship("Transaction", back_populates="service_records")


class Contract(Base):
    __tablename__ = "contracts"
    
    contract_id = Column(String, primary_key=True)
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), nullable=False)
    effective_date = Column(DateTime, nullable=False)
    service_period = Column(String, nullable=True)       # e.g., '12 months', '6 months'
    terms = Column(Text, nullable=True)

    transaction = relationship("Transaction", back_populates="contracts")


class Evidence(Base):
    __tablename__ = "evidence"
    
    evidence_id = Column(String, primary_key=True)
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), nullable=False)
    source_type = Column(String, nullable=False)       # 'goods_receipt', 'shipment', 'invoice', 'payment', 'service_record', 'contract', 'vendor_email', 'delivery_note'
    source_record = Column(String, nullable=False)     # The exact id of the related record
    content = Column(Text, nullable=False)             # Text/content of evidence
    embedding = Column(JSON, nullable=True)            # Embeddings serialized as JSON array of floats for SQLite/fallback
    relevant_date = Column(DateTime, nullable=True)
    reliability = Column(String, default="HIGH")       # 'HIGH', 'MEDIUM', 'LOW'

    transaction = relationship("Transaction", back_populates="evidences")


class Investigation(Base):
    __tablename__ = "investigations"
    
    investigation_id = Column(String, primary_key=True)
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), nullable=False)
    status = Column(String, default="RUNNING")         # 'RESOLVED', 'UNRESOLVED', 'ESCALATED'
    run_id = Column(String, nullable=False)
    cutoff_date = Column(DateTime, nullable=False)
    economic_event_date = Column(DateTime, nullable=True)
    final_classification = Column(String, nullable=False) # 'BEFORE_CUTOFF', 'AFTER_CUTOFF', 'POTENTIAL_MISSTATEMENT', 'UNRESOLVED', 'DATA_QUALITY_EXCEPTION'
    confidence = Column(Float, default=0.0)
    reasoning_summary = Column(Text, nullable=True)
    policy_applied = Column(String, nullable=True)
    known_facts = Column(JSON, default=list)
    missing_evidence = Column(JSON, default=list)
    contradictions = Column(JSON, default=list)
    recommended_action = Column(Text, nullable=True)
    human_review_required = Column(Boolean, default=False)
    steps = Column(JSON, default=list)                 # Agent run execution log list

    transaction = relationship("Transaction", back_populates="investigations")


class HumanReview(Base):
    __tablename__ = "human_reviews"
    
    review_id = Column(String, primary_key=True)
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), nullable=False)
    reviewer = Column(String, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))
    original_classification = Column(String, nullable=False)
    human_decision = Column(String, nullable=False)    # 'APPROVE', 'REJECT', 'REQUEST_MORE_EVIDENCE'
    comment = Column(Text, nullable=True)

    transaction = relationship("Transaction", back_populates="reviews")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    log_id = Column(String, primary_key=True)
    run_id = Column(String, nullable=False)
    transaction_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))
    rules_triggered = Column(JSON, default=list)
    tools_called = Column(JSON, default=list)
    evidence_retrieved = Column(JSON, default=list)
    hypotheses = Column(JSON, default=list)
    verification_results = Column(JSON, default=list)
    classification = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    recommended_action = Column(Text, nullable=True)
    policy_applied = Column(String, nullable=True)
    human_decision = Column(String, nullable=True)
    reviewer = Column(String, nullable=True)
