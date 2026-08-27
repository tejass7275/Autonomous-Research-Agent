"""
history.py
Endpoints for user authentication (register/login) and retrieving a user's
research history (past searches, questions, and summaries) for the
dashboard's history panel.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.models.user import User
from api.models.query_log import QueryLog
from api.schemas.schemas import (
    UserCreate,
    UserResponse,
    LoginRequest,
    Token,
    HistoryListResponse,
)
from api.core.security import hash_password, verify_password, create_access_token, get_current_user_id

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])
history_router = APIRouter(prefix="/api/history", tags=["history"])


@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@auth_router.post("/login", response_model=Token)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(subject=str(user.id))
    return Token(access_token=access_token)


@history_router.get("", response_model=HistoryListResponse)
def get_history(
    limit: int = Query(default=50, ge=1, le=200),
    query_type: str = Query(default=None, description="Filter by: search | qa | summary"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Return the current user's recent research activity, newest first."""
    query = db.query(QueryLog).filter(QueryLog.user_id == UUID(user_id))
    if query_type:
        query = query.filter(QueryLog.query_type == query_type)

    total = query.count()
    logs = query.order_by(QueryLog.created_at.desc()).limit(limit).all()

    return HistoryListResponse(total=total, results=logs)


@history_router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history_entry(
    log_id: UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    entry = (
        db.query(QueryLog)
        .filter(QueryLog.id == log_id, QueryLog.user_id == UUID(user_id))
        .first()
    )
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History entry not found")
    db.delete(entry)
    db.commit()
    return None