from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.utils.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _find_user(db: Session, username: str | None, email: str | None) -> User | None:
    if username is not None:
        user = db.query(User).filter(User.username == username).first()
        if user is not None:
            return user
    if email is not None:
        return db.query(User).filter(User.email == email).first()
    return None


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    """
    Create a new user account. The password is hashed with bcrypt before
    it is stored; the hash is never returned in API responses.
    """
    existing = (
        db.query(User)
        .filter(
            or_(User.username == payload.username, User.email == payload.email)
        )
        .first()
    )
    if existing is not None:
        if existing.username == payload.username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        username=payload.username,
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        # A concurrent registration took the username/email first.
        db.rollback()
        constraint = None
        if exc.orig is not None and getattr(exc.orig, "diag", None) is not None:
            constraint = exc.orig.diag.constraint_name
        if constraint == "ix_users_username":
            detail = "Username already registered"
        elif constraint == "ix_users_email":
            detail = "Email already registered"
        else:
            detail = "Username or email already registered"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        ) from exc
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Authenticate with a username or email plus password and receive a
    short-lived JWT access token.
    """
    if payload.username is None and payload.email is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide a username or an email",
        )

    user = _find_user(db, payload.username, payload.email)

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
        )

    return TokenResponse(access_token=create_access_token(subject=str(user.id)))


@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)) -> User:
    """
    Return the currently authenticated user. Useful for verifying that the
    bearer token works.
    """
    return current_user
