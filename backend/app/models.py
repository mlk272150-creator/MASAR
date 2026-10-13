from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import relationship

from .database import Base


class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    phone_number = Column(String(20), nullable=True, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    tasks = relationship("Tasks", back_populates="user", foreign_keys="Tasks.user_id")
    ledger_entries = relationship("Ledger", back_populates="user")


class Tasks(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'in_progress', 'completed', 'cancelled')",
            name="ck_tasks_status",
        ),
        CheckConstraint("priority IN ('low', 'medium', 'high')", name="ck_tasks_priority"),
        CheckConstraint("reward_points >= 0", name="ck_tasks_reward_points_nonnegative"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    region = Column(String(100), nullable=False, default="نابلس", server_default="نابلس")
    profession = Column(String(100), nullable=False, default="كهرباء", server_default="كهرباء")
    demand = Column(Float, nullable=False, default=5.5, server_default=text("5.5"))
    supply = Column(Float, nullable=False, default=5.5, server_default=text("5.5"))
    status = Column(String(20), nullable=False, default="pending")
    priority = Column(String(20), nullable=False, default="medium")
    reward_points = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    completed_at = Column(DateTime, nullable=True)

    user = relationship("Users", back_populates="tasks", foreign_keys=[user_id])
    assignee = relationship("Users", foreign_keys=[assignee_id])
    ledger_entries = relationship("Ledger", back_populates="task")


class Ledger(Base):
    __tablename__ = "ledger"
    __table_args__ = (
        CheckConstraint(
            "entry_type IN ('credit', 'debit', 'adjustment', 'escrow_hold', 'escrow_release')",
            name="ck_ledger_entry_type",
        ),
        CheckConstraint("amount_cents != 0", name="ck_ledger_amount_not_zero"),
        Index("uq_ledger_reference", "reference", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    entry_type = Column(String(20), nullable=False, default="credit")
    amount_points = Column("amount_cents", Integer, nullable=False)
    balance_after_points = Column("balance_after_cents", Integer, nullable=False)
    reference = Column(String(120), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("Users", back_populates="ledger_entries")
    task = relationship("Tasks", back_populates="ledger_entries")
