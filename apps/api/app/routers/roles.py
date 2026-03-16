import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.role import Role, RoleTaskLink, UserRoleAssignment
from app.models.task import Task
from app.models.user import User
from app.schemas.role import (
    RoleCreate,
    RoleDetailOut,
    RoleOut,
    RoleTaskLinkCreate,
    RoleTaskLinkOut,
    RoleUpdate,
    UserRoleAssignmentCreate,
    UserRoleAssignmentOut,
)

router = APIRouter(prefix="/roles", tags=["roles"])


def _role_out(role: Role) -> RoleOut:
    return RoleOut.model_validate(role)


def _role_detail_out(role: Role) -> RoleDetailOut:
    return RoleDetailOut(
        **RoleOut.model_validate(role).model_dump(),
        tasks=[
            {
                "id": link.id,
                "task_id": link.task_id,
                "task_title": link.task.title,
                "is_required": link.is_required,
            }
            for link in role.task_links
        ],
    )


async def _get_role_or_404(role_id: uuid.UUID, db: AsyncSession) -> Role:
    role = (await db.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


@router.get("", response_model=list[RoleOut])
async def list_roles(db: AsyncSession = Depends(get_db)):
    return [_role_out(role) for role in (await db.execute(select(Role).order_by(Role.name.asc()))).scalars().all()]


@router.post("", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = (
        await db.execute(select(Role).where((Role.code == payload.code) | (Role.name == payload.name)))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role already exists")

    role = Role(code=payload.code, name=payload.name, description=payload.description)
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return _role_out(role)


@router.get("/assignments", response_model=list[UserRoleAssignmentOut])
async def list_user_role_assignments(db: AsyncSession = Depends(get_db)):
    assignments = list(
        (await db.execute(select(UserRoleAssignment).order_by(UserRoleAssignment.created_at.desc()))).scalars().all()
    )
    return [
        UserRoleAssignmentOut(
            id=item.id,
            user_id=item.user_id,
            user_name=item.user.name,
            role_id=item.role_id,
            role_name=item.role.name,
            role_code=item.role.code,
            location=item.location,
            status=item.status,
            starts_on=item.starts_on,
            ends_on=item.ends_on,
            created_at=item.created_at,
        )
        for item in assignments
    ]


@router.post("/assignments", response_model=UserRoleAssignmentOut, status_code=status.HTTP_201_CREATED)
async def create_user_role_assignment(
    payload: UserRoleAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = (await db.execute(select(User).where(User.id == payload.user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    role = (await db.execute(select(Role).where(Role.id == payload.role_id))).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    assignment = UserRoleAssignment(**payload.model_dump())
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return UserRoleAssignmentOut(
        id=assignment.id,
        user_id=assignment.user_id,
        user_name=assignment.user.name,
        role_id=assignment.role_id,
        role_name=assignment.role.name,
        role_code=assignment.role.code,
        location=assignment.location,
        status=assignment.status,
        starts_on=assignment.starts_on,
        ends_on=assignment.ends_on,
        created_at=assignment.created_at,
    )


@router.get("/task-links", response_model=list[RoleTaskLinkOut])
async def list_role_task_links(db: AsyncSession = Depends(get_db)):
    links = list((await db.execute(select(RoleTaskLink))).scalars().all())
    return [
        RoleTaskLinkOut(
            id=link.id,
            role_id=link.role_id,
            role_name=link.role.name,
            task_id=link.task_id,
            task_title=link.task.title,
            is_required=link.is_required,
        )
        for link in links
    ]


@router.post("/task-links", response_model=RoleTaskLinkOut, status_code=status.HTTP_201_CREATED)
async def create_role_task_link(
    payload: RoleTaskLinkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = (await db.execute(select(Role).where(Role.id == payload.role_id))).scalar_one_or_none()
    task = (await db.execute(select(Task).where(Task.id == payload.task_id))).scalar_one_or_none()
    if role is None or task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role or task not found")

    existing = (
        await db.execute(
            select(RoleTaskLink).where(RoleTaskLink.role_id == payload.role_id, RoleTaskLink.task_id == payload.task_id)
        )
    ).scalar_one_or_none()
    if existing:
        return RoleTaskLinkOut(
            id=existing.id,
            role_id=existing.role_id,
            role_name=existing.role.name,
            task_id=existing.task_id,
            task_title=existing.task.title,
            is_required=existing.is_required,
        )

    link = RoleTaskLink(**payload.model_dump())
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return RoleTaskLinkOut(
        id=link.id,
        role_id=link.role_id,
        role_name=link.role.name,
        task_id=link.task_id,
        task_title=link.task.title,
        is_required=link.is_required,
    )


@router.delete("/task-links/{link_id}", response_model=RoleDetailOut)
async def delete_role_task_link(
    link_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    link = (await db.execute(select(RoleTaskLink).where(RoleTaskLink.id == link_id))).scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role task link not found")
    role_id = link.role_id
    await db.delete(link)
    await db.commit()
    return _role_detail_out(await _get_role_or_404(role_id, db))


@router.get("/{role_id}", response_model=RoleDetailOut)
async def get_role(role_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return _role_detail_out(await _get_role_or_404(role_id, db))


@router.patch("/{role_id}", response_model=RoleDetailOut)
async def update_role(
    role_id: uuid.UUID,
    payload: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = await _get_role_or_404(role_id, db)
    role.code = payload.code
    role.name = payload.name
    role.description = payload.description
    role.is_active = payload.is_active
    await db.commit()
    await db.refresh(role)
    return _role_detail_out(role)
