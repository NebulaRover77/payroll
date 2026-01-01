from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Integer, Numeric, String

from app.db.session import Base


class PayrollRun(Base):
    __tablename__ = "payroll_runs"

    id = Column(Integer, primary_key=True, index=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    total_gross = Column(Numeric(scale=2), nullable=False)
    status = Column(String(50), nullable=False, default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
