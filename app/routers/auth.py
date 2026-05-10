from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserRegisterSchema,
    UserLoginSchema,
    UserResponseSchema,
    TokenSchema,
)
from app.utils.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponseSchema, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegisterSchema, db: Session = Depends(get_db)):
    """Register a new customer or service_provider. Admins cannot register via this endpoint."""

    # Check if phone number already exists
    existing_phone = db.query(User).filter(User.phone_number == user_data.phone_number).first()
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this phone number already exists",
        )

    # Check if email already exists (if provided)
    if user_data.email:
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists",
            )

    # Create the user
    new_user = User(
        full_name=user_data.full_name,
        phone_number=user_data.phone_number,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=user_data.role.value,
        is_active=True,
        is_verified=False,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


from fastapi.security import OAuth2PasswordRequestForm

@router.post("/login", response_model=TokenSchema)
def login(credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticate user with phone number and password, return JWT token."""

    # Note: OAuth2PasswordRequestForm uses the 'username' field, so we map it to phone_number
    user = db.query(User).filter(User.phone_number == credentials.username).first()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact support.",
        )

    access_token = create_access_token(data={"sub": str(user.id)})

    return TokenSchema(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponseSchema)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user
