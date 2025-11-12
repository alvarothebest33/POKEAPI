from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session, select
from typing import Annotated

from fastapi.security import OAuth2PasswordRequestForm

from app.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_user_by_username
)
from app.database import get_session
from app.models import User, UserCreate, UserRead, Token
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Autenticación"]
)


# REGISTRO (funciona con JSON)
@router.post("/register", response_model=UserRead, summary="Registrarse")
@limiter.limit("5/hour")
def register_user(
        request: Request,
        user_create: UserCreate,
        session: Annotated[Session, Depends(get_session)]
):

    # Verificar si existe usuario o email
    existing_user = session.exec(
        select(User).where(
            (User.username == user_create.username) |
            (User.email == user_create.email)
        )
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario o el email ya están registrados."
        )

    # Hashear contraseña correctamente
    hashed_password = get_password_hash(user_create.password)

    # Crear usuario
    db_user = User(
        username=user_create.username,
        email=user_create.email,
        hashed_password=hashed_password
    )

    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return db_user


# LOGIN (USA OAuth2PasswordRequestForm, NO JSON)
@router.post("/login", response_model=Token, summary="Iniciar sesion")
@limiter.limit("10/minute")
def login_for_access_token(
        request: Request,
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        session: Annotated[Session, Depends(get_session)]
):

    # Buscamos usuario por username
    user = get_user_by_username(session, form_data.username)

    # Verificación segura
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nombre de usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Crear token JWT
    token_data = {
        "sub": user.username,
        "user_id": user.id
    }
    access_token = create_access_token(data=token_data)

    return {"access_token": access_token, "token_type": "bearer"}
