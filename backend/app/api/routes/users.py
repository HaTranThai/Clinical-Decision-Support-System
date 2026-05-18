"""User management routes (Admin)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.db.base import User, Role, AlertAction
from app.core.security import hash_password
from app.schemas.users import UserCreate, UserUpdate, UserOut
from app.api.deps import require_admin

router = APIRouter()


async def _is_admin(db: AsyncSession, user: User) -> bool:
    result = await db.execute(select(Role).where(Role.role_id == user.role_id))
    role = result.scalar_one_or_none()
    return bool(role and role.name == "admin")


async def _count_other_active_admins(db: AsyncSession, user_id) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(User)
        .join(Role, User.role_id == Role.role_id)
        .where(Role.name == "admin", User.is_active.is_(True), User.user_id != user_id)
    )
    return result.scalar() or 0


@router.get("/roles")
async def list_roles(db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    result = await db.execute(select(Role).order_by(Role.name))
    return [{"role_id": str(r.role_id), "name": r.name} for r in result.scalars().all()]


@router.get("", response_model=list[UserOut])
async def list_users(db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    out = []
    for u in users:
        role_result = await db.execute(select(Role).where(Role.role_id == u.role_id))
        role = role_result.scalar_one_or_none()
        out.append(UserOut(
            user_id=str(u.user_id),
            username=u.username,
            display_name=u.display_name,
            role_id=str(u.role_id),
            role_name=role.name if role else None,
            is_active=u.is_active,
            created_at=str(u.created_at) if u.created_at else None,
        ))
    return out


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        role_id=body.role_id,
    )
    db.add(user)
    await db.flush()
    return UserOut(
        user_id=str(user.user_id),
        username=user.username,
        display_name=user.display_name,
        role_id=str(user.role_id),
        is_active=user.is_active,
        created_at=str(user.created_at) if user.created_at else None,
    )


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.display_name is not None:
        user.display_name = body.display_name
    if body.is_active is not None:
        if body.is_active is False:
            if str(user.user_id) == str(admin.user_id):
                raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
            if await _is_admin(db, user) and await _count_other_active_admins(db, user.user_id) == 0:
                raise HTTPException(status_code=400, detail="Cannot deactivate the last active admin")
        user.is_active = body.is_active
    if body.role_id is not None:
        user.role_id = body.role_id
    if body.password is not None:
        user.password_hash = hash_password(body.password)

    await db.flush()
    return UserOut(
        user_id=str(user.user_id),
        username=user.username,
        display_name=user.display_name,
        role_id=str(user.role_id),
        is_active=user.is_active,
        created_at=str(user.created_at) if user.created_at else None,
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if str(user.user_id) == str(admin.user_id):
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    if await _is_admin(db, user) and await _count_other_active_admins(db, user.user_id) == 0:
        raise HTTPException(status_code=400, detail="Cannot delete the last active admin")

    action_count = await db.execute(
        select(func.count()).select_from(AlertAction).where(AlertAction.user_id == user_id)
    )
    if (action_count.scalar() or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail="User has alert action history — deactivate instead of deleting",
        )

    await db.delete(user)
    await db.flush()
    return {"detail": "User deleted"}
