"""SQLAlchemy ORM models — mirrors the DDL in ARCHITECTURE.md Section 7."""
from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base


class Provider(Base):
    __tablename__ = "providers"

    provider_id = Column(String(10), primary_key=True)
    specialty = Column(String(100))
    claim_volume_30d_avg = Column(Integer)
    flagged_history_count = Column(Integer, default=0)

    claims = relationship("Claim", back_populates="provider")


class Claim(Base):
    __tablename__ = "claims"

    claim_id = Column(String(15), primary_key=True)
    patient_id = Column(String(10), nullable=False)
    provider_id = Column(String(10), ForeignKey("providers.provider_id"))
    icd10_codes = Column(ARRAY(String))
    cpt_codes = Column(ARRAY(String))
    billed_amount = Column(Numeric(10, 2))
    approved_amount = Column(Numeric(10, 2))
    treatment_date = Column(Date)
    plan_type = Column(String(20))
    prior_auth_required = Column(Boolean)
    prior_auth_obtained = Column(Boolean)
    fraud_label = Column(Boolean)  # ground truth, hidden from the agent pipeline
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    provider = relationship("Provider", back_populates="claims")
    decisions = relationship("Decision", back_populates="claim")
    escalations = relationship("Escalation", back_populates="claim")


class Decision(Base):
    __tablename__ = "decisions"

    decision_id = Column(Integer, primary_key=True, autoincrement=True)
    claim_id = Column(String(15), ForeignKey("claims.claim_id"))
    coding_flags = Column(ARRAY(String))
    fraud_score = Column(Numeric(5, 2))
    fraud_top_features = Column(JSONB)
    retrieved_clauses = Column(JSONB)
    decision_recommendation = Column(String(20))
    decision_rationale = Column(Text)
    final_decision = Column(String(20))
    escalation_reason = Column(Text)
    agent_trace = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    claim = relationship("Claim", back_populates="decisions")


class Escalation(Base):
    __tablename__ = "escalations"

    escalation_id = Column(Integer, primary_key=True, autoincrement=True)
    claim_id = Column(String(15), ForeignKey("claims.claim_id"))
    status = Column(String(20), default="pending")  # pending | resolved
    adjuster_decision = Column(String(20))
    adjuster_notes = Column(Text)
    resolved_by = Column(String(50))  # username of the adjuster/admin who resolved it
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))

    claim = relationship("Claim", back_populates="escalations")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)  # "adjuster" | "admin"
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    claim_id = Column(String(15))
    event_type = Column(String(50))
    event_payload = Column(JSONB)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
