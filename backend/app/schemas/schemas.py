from datetime import datetime
from typing import Literal, Optional

from pydantic import model_validator

from pydantic import BaseModel, ConfigDict, Field


PalestinianCity = Literal["نابلس", "رام الله", "الخليل", "جنين", "طولكرم"]
TaskProfession = Literal["كهرباء", "دهان", "صيانة", "برمجة"]


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=255)
    phone_number: Optional[str] = Field(default=None, min_length=7, max_length=20)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    phone_number: Optional[str] = Field(default=None, min_length=7, max_length=20)
    email: Optional[str] = None
    password: str

    @model_validator(mode="after")
    def require_login_identifier(self) -> "UserLogin":
        if bool(self.phone_number) == bool(self.email):
            raise ValueError("Provide either a phone number or an email address.")
        return self


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BalanceOut(BaseModel):
    user_id: int
    balance_points: int


class PricingFeatures(BaseModel):
    region: PalestinianCity
    profession: TaskProfession
    demand: float = Field(default=5.5, ge=1, le=10)
    supply: float = Field(default=5.5, ge=1, le=10)


class TaskCreate(PricingFeatures):
    user_id: int = Field(gt=0, description="User posting and funding the task")
    assignee_id: Optional[int] = Field(default=None, gt=0)
    title: str = Field(min_length=3, max_length=150)
    description: Optional[str] = None
    priority: Literal["low", "medium", "high"] = "medium"


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=150)
    description: Optional[str] = None
    priority: Optional[Literal["low", "medium", "high"]] = None


class TaskOut(BaseModel):
    id: int
    user_id: int
    assignee_id: Optional[int]
    title: str
    description: Optional[str]
    region: PalestinianCity
    profession: TaskProfession
    demand: float
    supply: float
    status: Literal["pending", "approved", "in_progress", "completed", "cancelled"]
    priority: Literal["low", "medium", "high"]
    reward_points: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TransferCreate(BaseModel):
    sender_id: int = Field(gt=0)
    recipient_id: int = Field(gt=0)
    amount_points: int = Field(gt=0)
    idempotency_key: str = Field(
        min_length=8,
        max_length=80,
        pattern=r"^[A-Za-z0-9._:-]+$",
    )


class LedgerEntryOut(BaseModel):
    id: int
    user_id: int
    task_id: Optional[int]
    entry_type: Literal["credit", "debit", "adjustment", "escrow_hold", "escrow_release"]
    amount_points: int
    balance_after_points: int
    reference: Optional[str]
    description: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransferOut(BaseModel):
    idempotency_key: str
    sender_balance_points: int
    recipient_balance_points: int
    entries: list[LedgerEntryOut]


class PricingRequest(BaseModel):
    requested_task: PricingFeatures


class PricingResponse(BaseModel):
    predicted_price_points: float
    training_examples: int
    model: str
    note: str


class WorkerReputationInput(BaseModel):
    worker_id: int = Field(gt=0)
    completed_jobs: int = Field(ge=0, le=10_000_000)
    on_time_rate: float = Field(ge=0, le=1)
    average_rating: float = Field(ge=1, le=5)
    reviews: list[str] = Field(default_factory=list, max_length=200)


class ReputationRequest(BaseModel):
    workers: list[WorkerReputationInput] = Field(min_length=2, max_length=2000)


class WorkerReputationOut(BaseModel):
    worker_id: int
    reputation_score: float
    trust_tier: Literal["emerging", "established", "trusted"]
    cohort_cluster: int
    sentiment_score: float


class ReputationResponse(BaseModel):
    method: str
    workers: list[WorkerReputationOut]
    note: str
