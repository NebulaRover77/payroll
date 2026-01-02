from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)

    # Make optional so ops-console employees don't require an app user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # Ops-console fields
    name = Column(String(200), nullable=False)          # canonical display name
    role = Column(String(200), nullable=False, default="—")
    pay_type = Column(String(20), nullable=False, default="salary")  # hourly|salary
    rate = Column(Numeric(scale=2), nullable=False, default=0)       # hourly or salary per period
    default_hours = Column(Numeric(scale=2), nullable=False, default=0)
    status = Column(String(20), nullable=False, default="active")    # active|on_leave|terminated
    tax = Column(String(20), nullable=False, default="standard")     # standard|low|high

    hire_date = Column(Date, nullable=True)

    # Keep legacy salary field but make it optional (so older code can still use it)
    annual_salary = Column(Numeric(scale=2), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
