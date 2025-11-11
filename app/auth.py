from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext  # Para hashear con bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from typing import Annotated

from app.config import settings
from app.models import User, TokenData
from app.database import get_session

# Configuración de Hashing
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# Funciones de Hashing

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Verifica contraseña plana con hasheada
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    # Genera un hash bcrypt de la contraseña
    return pwd_context.hash(password)


#Funciones de JWT

def create_access_token(data: dict) -> str:
    # Crea un nuevo token JWT
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    # IAT
    to_encode.update({"iat": datetime.utcnow()})

    # Firmamos token con la SECRET_KEY
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


# Dependencia de Usuario
def get_user_by_username(session: Session, username: str) -> User | None:
    #Busca usuario en base de datos
    statement = select(User).where(User.username == username)
    return session.exec(statement).first()

def get_current_user(
        token: Annotated[str, Depends(oauth2_scheme)],
        session: Annotated[Session, Depends(get_session)]
) -> User:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decodificamos el token usando la SECRET_KEY
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        token_data = TokenData(username=username, user_id=payload.get("user_id"))

    except JWTError:
        # Si el token ha expirado, lanzamos error
        raise credentials_exception

    # Buscamos el usuario en la BD
    user = get_user_by_username(session, token_data.username)
    if user is None:
        raise credentials_exception
    return user