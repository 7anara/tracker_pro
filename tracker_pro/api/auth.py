from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tracker_pro.config import settings
from tracker_pro.database.db import get_db
from tracker_pro.database.models import User
from tracker_pro.schemas.auth_schema import TokenSchema, UserLoginSchema, UserOutSchema, UserRegisterSchema


auth_router = APIRouter(prefix="/auth", tags=["Auth"])
bearer_scheme = HTTPBearer(auto_error=False)
password_hash = PasswordHash.recommended()
credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid authentication credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise credentials_exception
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = int(payload.get("sub", ""))
    except (JWTError, TypeError, ValueError):
        raise credentials_exception
    user = db.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user


@auth_router.post("/register/", response_model=UserOutSchema, status_code=status.HTTP_201_CREATED)
def register(user: UserRegisterSchema, db: Session = Depends(get_db)):
    record = User(email=str(user.email).lower(), password_hash=password_hash.hash(user.password))
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email is already registered")
    db.refresh(record)
    return record


@auth_router.post("/login/", response_model=TokenSchema)
def login(credentials: UserLoginSchema, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(credentials.email).lower()))
    if user is None or not password_hash.verify(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    return TokenSchema(access_token=create_access_token(user.id))


@auth_router.get("/me/", response_model=UserOutSchema)
def me(current_user: User = Depends(get_current_user)):
    return current_user
