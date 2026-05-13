"""
SuperDry - Módulo de autenticação e auditoria
"""
import os
import uuid
import jwt
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, Depends, Header
from passlib.context import CryptContext
from pydantic import BaseModel, Field

# ============================================================
# Config
# ============================================================
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'superdry-secret-key-change-in-production-2025')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================
# Enums e Models
# ============================================================
class UserRole(str, Enum):
    ADMIN = "ADMIN"
    TECNICO = "TECNICO"
    ATENDENTE = "ATENDENTE"
    FINANCEIRO = "FINANCEIRO"
    MANUTENCAO = "MANUTENCAO"


class User(BaseModel):
    id: str = Field(default_factory=lambda: f"USR-{str(uuid.uuid4().int)[:4].zfill(4)}")
    name: str
    email: str
    role: UserRole = UserRole.ATENDENTE
    is_active: bool = True
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserPublic(BaseModel):
    """Representação pública do usuário (sem hash)"""
    id: str
    name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: UserRole = UserRole.ATENDENTE
    is_active: bool = True


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class AuditLog(BaseModel):
    id: str = Field(default_factory=lambda: f"AUD-{uuid.uuid4().hex[:12]}")
    entity_type: str       # "client", "budget", "user", etc.
    entity_id: str
    action: str            # "CREATE", "UPDATE", "DELETE", "LOGIN", etc.
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None  # snapshot ou diff
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# Senha
# ============================================================
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


# ============================================================
# JWT
# ============================================================
def create_access_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")


# ============================================================
# Dependências (importadas pelo server.py com o db injetado)
# ============================================================
def make_auth_dependencies(db):
    """Cria as dependências de auth com referência ao db."""

    async def get_current_user(authorization: Optional[str] = Header(None)) -> UserPublic:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Não autenticado")
        token = authorization.split(" ", 1)[1].strip()
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")
        if not user.get("is_active", True):
            raise HTTPException(status_code=403, detail="Usuário inativo")
        return UserPublic(**{k: v for k, v in user.items() if k != "password_hash"})

    async def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[UserPublic]:
        if not authorization:
            return None
        try:
            return await get_current_user(authorization=authorization)
        except HTTPException:
            return None

    def require_roles(*roles: UserRole):
        async def _checker(current_user: UserPublic = Depends(get_current_user)) -> UserPublic:
            if current_user.role not in roles and current_user.role != UserRole.ADMIN:
                raise HTTPException(status_code=403, detail="Permissão insuficiente")
            return current_user
        return _checker

    async def log_audit(
        entity_type: str,
        entity_id: str,
        action: str,
        user: Optional[UserPublic] = None,
        changes: Optional[Dict[str, Any]] = None,
    ):
        try:
            entry = AuditLog(
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                user_id=(user.id if user else None),
                user_name=(user.name if user else None),
                changes=changes,
            )
            await db.audit_logs.insert_one(entry.dict())
        except Exception as e:
            # auditoria nunca pode quebrar a request
            print(f"[audit] erro ao registrar: {e}")

    return {
        "get_current_user": get_current_user,
        "get_optional_user": get_optional_user,
        "require_roles": require_roles,
        "log_audit": log_audit,
    }


# ============================================================
# Bootstrap admin padrão
# ============================================================
async def ensure_default_admin(db):
    """Garante a existência de pelo menos 1 admin no sistema."""
    admin = await db.users.find_one({"role": UserRole.ADMIN.value})
    if admin:
        return
    default_email = "admin@superdry.com"
    existing = await db.users.find_one({"email": default_email})
    if existing:
        await db.users.update_one(
            {"email": default_email},
            {"$set": {"role": UserRole.ADMIN.value, "is_active": True}},
        )
        return
    user = User(
        name="Administrador",
        email=default_email,
        role=UserRole.ADMIN,
        is_active=True,
        password_hash=hash_password("admin123"),
    )
    await db.users.insert_one(user.dict())
    print(f"[auth] Admin padrão criado: {default_email} / admin123")
