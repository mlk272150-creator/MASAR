from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Ledger, Tasks, Users
from ..schemas.schemas import TaskCreate, TaskOut, TaskUpdate
from ..services.pricing_service import pricing_service
from .ledger import reserve_task_escrow
from .users import get_balance

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> Tasks:
    owner = (
        db.query(Users)
        .filter(Users.id == payload.user_id)
        .with_for_update()
        .first()
    )
    if owner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task owner not found.")
    if payload.assignee_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Select a worker so the estimated reward can be reserved in escrow.",
        )

    estimated_reward = int(round(pricing_service.estimate(payload.model_dump())))
    task = Tasks(
        user_id=payload.user_id,
        assignee_id=payload.assignee_id,
        title=payload.title,
        description=payload.description,
        region=payload.region,
        profession=payload.profession,
        demand=payload.demand,
        supply=payload.supply,
        priority=payload.priority,
        reward_points=estimated_reward,
        status="pending",
    )
    db.add(task)
    try:
        db.flush()
        if task.reward_points > 0:
            reserve_task_escrow(db, task, payload.user_id)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    db.refresh(task)
    return task


@router.get("", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db)) -> list[Tasks]:
    return db.query(Tasks).order_by(Tasks.id.desc()).all()


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)) -> Tasks:
    task = db.query(Tasks).filter(Tasks.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)) -> Tasks:
    task = db.query(Tasks).filter(Tasks.id == task_id).with_for_update().first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    if task.status == "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Completed tasks cannot be edited.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None or field == "description":
            setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/complete", response_model=TaskOut)
def complete_task(task_id: int, db: Session = Depends(get_db)) -> Tasks:
    task = db.query(Tasks).filter(Tasks.id == task_id).with_for_update().first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    if task.status == "completed":
        return task
    if task.status == "cancelled":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cancelled tasks cannot be completed.")

    if task.reward_points > 0:
        if task.assignee_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The rewarded task has no assignee.",
            )
        hold_reference = f"task:{task.id}:escrow"
        hold = db.query(Ledger).filter(Ledger.reference == hold_reference).first()
        if hold is None or hold.amount_points != -task.reward_points:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The task reward is not fully reserved in escrow.",
            )
        assignee = (
            db.query(Users)
            .filter(Users.id == task.assignee_id)
            .with_for_update()
            .first()
        )
        if assignee is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task assignee no longer exists.")

        balance = get_balance(db, task.assignee_id)
        db.add(
            Ledger(
                user_id=task.assignee_id,
                task_id=task.id,
                entry_type="escrow_release",
                amount_points=task.reward_points,
                balance_after_points=balance + task.reward_points,
                reference=f"task:{task.id}:release",
                description=f"Escrow reward released for completed task {task.id}.",
            )
        )

    task.status = "completed"
    task.completed_at = datetime.utcnow()
    task.updated_at = task.completed_at
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/approve", response_model=TaskOut)
def approve_task(task_id: int, db: Session = Depends(get_db)) -> Tasks:
    task = db.query(Tasks).filter(Tasks.id == task_id).with_for_update().first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    if task.status in ("completed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A {task.status} task cannot be approved.",
        )
    task.status = "approved"
    db.commit()
    db.refresh(task)
    return task
