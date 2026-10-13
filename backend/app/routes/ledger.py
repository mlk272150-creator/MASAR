from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Ledger, Tasks, Users
from ..schemas.schemas import LedgerEntryOut, TransferCreate, TransferOut
from .users import get_balance

router = APIRouter(prefix="/ledger", tags=["ledger"])


def reserve_task_escrow(db: Session, task: Tasks, owner_id: int) -> Ledger | None:
    if task.reward_points == 0:
        return None
    if task.assignee_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A task with a reward must have an assignee.",
        )
    if task.assignee_id == owner_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The task owner cannot be its own assignee.",
        )

    task_reference = f"task:{task.id}:escrow"
    existing = db.query(Ledger).filter(Ledger.reference == task_reference).first()
    if existing is not None:
        if existing.user_id != owner_id or existing.amount_points != -task.reward_points:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An escrow entry already exists with different details.",
            )
        return existing

    owner = (
        db.query(Users)
        .filter(Users.id == owner_id)
        .with_for_update()
        .first()
    )
    if owner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task owner not found.")
    if db.query(Users.id).filter(Users.id == task.assignee_id).first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task assignee not found.")

    balance = get_balance(db, owner_id)
    if balance < task.reward_points:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Insufficient points to reserve the task reward.",
        )

    entry = Ledger(
        user_id=owner_id,
        task_id=task.id,
        entry_type="escrow_hold",
        amount_points=-task.reward_points,
        balance_after_points=balance - task.reward_points,
        reference=task_reference,
        description=f"Points reserved for task {task.id}.",
    )
    db.add(entry)
    db.flush()
    return entry


def _get_transfer(db: Session, key: str) -> tuple[Ledger, Ledger] | None:
    debit = (
        db.query(Ledger)
        .filter(Ledger.reference == f"transfer:{key}:debit")
        .first()
    )
    credit = (
        db.query(Ledger)
        .filter(Ledger.reference == f"transfer:{key}:credit")
        .first()
    )
    if debit is None and credit is None:
        return None
    if debit is None or credit is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The idempotency key is already associated with an incomplete transaction.",
        )
    return debit, credit


def _transfer_response(
    key: str,
    debit: Ledger,
    credit: Ledger,
    sender_id: int,
    recipient_id: int,
    amount: int,
) -> TransferOut:
    if (
        debit.user_id != sender_id
        or credit.user_id != recipient_id
        or debit.amount_points != -amount
        or credit.amount_points != amount
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The idempotency key was already used for a different transfer.",
        )
    return TransferOut(
        idempotency_key=key,
        sender_balance_points=debit.balance_after_points,
        recipient_balance_points=credit.balance_after_points,
        entries=[debit, credit],
    )


@router.post("/transfers", response_model=TransferOut, status_code=status.HTTP_201_CREATED)
def transfer_points(payload: TransferCreate, db: Session = Depends(get_db)) -> TransferOut:
    if payload.sender_id == payload.recipient_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Sender and recipient must be different users.",
        )

    # Lock users in a stable order to serialize balance checks without deadlocks.
    users = (
        db.query(Users)
        .filter(Users.id.in_([payload.sender_id, payload.recipient_id]))
        .order_by(Users.id)
        .with_for_update()
        .all()
    )
    if len(users) != 2:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sender or recipient not found.")

    prior_transfer = _get_transfer(db, payload.idempotency_key)
    if prior_transfer is not None:
        return _transfer_response(
            payload.idempotency_key,
            *prior_transfer,
            payload.sender_id,
            payload.recipient_id,
            payload.amount_points,
        )

    sender_balance = get_balance(db, payload.sender_id)
    if sender_balance < payload.amount_points:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Insufficient available points.",
        )
    recipient_balance = get_balance(db, payload.recipient_id)
    debit = Ledger(
        user_id=payload.sender_id,
        entry_type="debit",
        amount_points=-payload.amount_points,
        balance_after_points=sender_balance - payload.amount_points,
        reference=f"transfer:{payload.idempotency_key}:debit",
        description=f"Transfer to user {payload.recipient_id}.",
    )
    credit = Ledger(
        user_id=payload.recipient_id,
        entry_type="credit",
        amount_points=payload.amount_points,
        balance_after_points=recipient_balance + payload.amount_points,
        reference=f"transfer:{payload.idempotency_key}:credit",
        description=f"Transfer from user {payload.sender_id}.",
    )
    db.add_all([debit, credit])
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        prior_transfer = _get_transfer(db, payload.idempotency_key)
        if prior_transfer is None:
            raise
        return _transfer_response(
            payload.idempotency_key,
            *prior_transfer,
            payload.sender_id,
            payload.recipient_id,
            payload.amount_points,
        )
    db.refresh(debit)
    db.refresh(credit)
    return TransferOut(
        idempotency_key=payload.idempotency_key,
        sender_balance_points=debit.balance_after_points,
        recipient_balance_points=credit.balance_after_points,
        entries=[debit, credit],
    )


@router.post("/escrows/{task_id}", response_model=LedgerEntryOut)
def ensure_task_escrow(
    task_id: int,
    owner_id: int,
    db: Session = Depends(get_db),
) -> Ledger:
    task = db.query(Tasks).filter(Tasks.id == task_id).with_for_update().first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    if task.user_id != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the task owner can reserve escrow.")
    entry = reserve_task_escrow(db, task, owner_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This task has no reward to place in escrow.",
        )
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/users/{user_id}", response_model=list[LedgerEntryOut])
def list_user_ledger(user_id: int, db: Session = Depends(get_db)) -> list[Ledger]:
    if db.query(Users.id).filter(Users.id == user_id).first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return (
        db.query(Ledger)
        .filter(Ledger.user_id == user_id)
        .order_by(Ledger.id.desc())
        .all()
    )
