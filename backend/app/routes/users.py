import hashlib
import hmac
import re
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Ledger, Users
from ..schemas.schemas import BalanceOut, UserCreate, UserLogin, UserOut

router = APIRouter(tags=["users"])

PHONE_DIGITS = re.compile(r"^\+?[0-9]{7,15}$")


def normalize_phone(phone_number: str) -> str:
    normalized = re.sub(r"[\s()-]", "", phone_number)
    if not PHONE_DIGITS.fullmatch(normalized):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Enter a valid phone number using 7 to 15 digits.",
        )
    return normalized


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return f"pbkdf2_sha256${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    if "$" not in encoded:
        legacy_digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy_digest, encoded)
    try:
        algorithm, salt_hex, digest_hex = encoded.split("$", maxsplit=2)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            310_000,
        ).hex()
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, digest_hex)


def get_balance(db: Session, user_id: int) -> int:
    return int(
        db.query(func.coalesce(func.sum(Ledger.amount_points), 0))
        .filter(Ledger.user_id == user_id)
        .scalar()
    )


@router.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)) -> Users:
    phone_number = normalize_phone(payload.phone_number) if payload.phone_number else None
    user = Users(
        username=payload.username,
        email=payload.email,
        phone_number=phone_number,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username, email, or phone number is already registered.",
        ) from exc
    db.refresh(user)
    return user


@router.post("/auth/login")
@router.post("/users/login")
def login_user(payload: UserLogin, db: Session = Depends(get_db)) -> dict[str, object]:
    if payload.phone_number:
        phone_number = normalize_phone(payload.phone_number)
        user = db.query(Users).filter(Users.phone_number == phone_number).first()
    else:
        user = db.query(Users).filter(Users.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or email address or password.",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive.")
    if "$" not in user.hashed_password:
        user.hashed_password = hash_password(payload.password)
        db.commit()

    return {
        "message": "Login successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "phone_number": user.phone_number,
        },
        "balance_points": get_balance(db, user.id),
        "token": f"demo-token-{user.id}",
    }


@router.get("/users/{user_id}/balance", response_model=BalanceOut)
def read_balance(user_id: int, db: Session = Depends(get_db)) -> BalanceOut:
    if db.query(Users.id).filter(Users.id == user_id).first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return BalanceOut(user_id=user_id, balance_points=get_balance(db, user_id))


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)) -> list[Users]:
    return db.query(Users).order_by(Users.id).all()


@router.get("/users/{user_id}", response_model=UserOut)
def read_user(user_id: int, db: Session = Depends(get_db)) -> Users:
    user = db.query(Users).filter(Users.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user
