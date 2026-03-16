import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.procedure import Procedure, TaskProcedureLink
from app.models.role import RoleTaskLink
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate, TrainingSuggestion
from app.services.embedding_service import get_embedding
from app.services.search_service import rank_procedure_versions_by_embedding

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _serialize_task(task: Task) -> TaskOut:
    return TaskOut(
        id=task.id,
        title=task.title,
        description=task.description,
        location=task.location,
        roles=[
            {
                "id": link.role.id,
                "code": link.role.code,
                "name": link.role.name,
            }
            for link in task.role_links
            if getattr(link, "role", None) is not None
        ],
        procedures=[
            {
                "id": link.id,
                "procedure_id": link.procedure_id,
                "code": link.procedure.code,
                "title": link.procedure.title,
                "is_primary": link.is_primary,
            }
            for link in task.procedure_links
            if getattr(link, "procedure", None) is not None
        ],
    )


async def _get_task_or_404(task_id: uuid.UUID, db: AsyncSession) -> Task:
    task = (
        await db.execute(
            select(Task)
            .where(Task.id == task_id)
            .options(
                selectinload(Task.role_links).selectinload(RoleTaskLink.role),
                selectinload(Task.procedure_links).selectinload(TaskProcedureLink.procedure),
            )
        )
    ).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    text_for_embedding = f"{payload.title} {payload.description or ''}"
    embedding = await get_embedding(text_for_embedding)

    task = Task(
        title=payload.title,
        description=payload.description,
        location=payload.location,
        embedding=embedding,
    )
    db.add(task)
    await db.commit()
    result = await db.execute(
        select(Task)
        .where(Task.id == task.id)
        .options(
            selectinload(Task.role_links).selectinload(RoleTaskLink.role),
            selectinload(Task.procedure_links).selectinload(TaskProcedureLink.procedure),
        )
    )
    task = result.scalar_one()
    return _serialize_task(task)


@router.get("", response_model=list[TaskOut])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Task).options(
            selectinload(Task.role_links).selectinload(RoleTaskLink.role),
            selectinload(Task.procedure_links).selectinload(TaskProcedureLink.procedure),
        )
    )
    return [_serialize_task(task) for task in result.scalars().all()]


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return _serialize_task(await _get_task_or_404(task_id, db))


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await _get_task_or_404(task_id, db)
    task.title = payload.title
    task.description = payload.description
    task.location = payload.location
    text_for_embedding = f"{payload.title} {payload.description or ''}"
    task.embedding = await get_embedding(text_for_embedding)
    await db.commit()
    refreshed = await _get_task_or_404(task_id, db)
    return _serialize_task(refreshed)


@router.post("/{task_id}/procedure-links", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def add_procedure_to_task(
    task_id: uuid.UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        await db.execute(
            select(Task)
            .where(Task.id == task_id)
            .options(selectinload(Task.procedure_links).selectinload(TaskProcedureLink.procedure))
        )
    ).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    procedure_id = payload.get("procedure_id")
    if not procedure_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="procedure_id is required")

    procedure = (await db.execute(select(Procedure).where(Procedure.id == procedure_id))).scalar_one_or_none()
    if procedure is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedure not found")

    existing = (
        await db.execute(
            select(TaskProcedureLink).where(
                TaskProcedureLink.task_id == task_id,
                TaskProcedureLink.procedure_id == procedure.id,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(TaskProcedureLink(task_id=task_id, procedure_id=procedure.id, is_primary=False))
        await db.commit()

    refreshed = (
        await db.execute(
            select(Task)
            .where(Task.id == task_id)
            .options(
                selectinload(Task.role_links).selectinload(RoleTaskLink.role),
                selectinload(Task.procedure_links).selectinload(TaskProcedureLink.procedure),
            )
        )
    ).scalar_one()
    return _serialize_task(refreshed)


@router.delete("/{task_id}/procedure-links/{procedure_id}", response_model=TaskOut)
async def remove_procedure_from_task(
    task_id: uuid.UUID,
    procedure_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        await db.execute(
            select(Task)
            .where(Task.id == task_id)
            .options(
                selectinload(Task.role_links).selectinload(RoleTaskLink.role),
                selectinload(Task.procedure_links).selectinload(TaskProcedureLink.procedure),
            )
        )
    ).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    link = (
        await db.execute(
            select(TaskProcedureLink).where(
                TaskProcedureLink.task_id == task_id,
                TaskProcedureLink.procedure_id == procedure_id,
            )
        )
    ).scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedure link not found")

    await db.delete(link)
    await db.commit()

    refreshed = (
        await db.execute(
            select(Task)
            .where(Task.id == task_id)
            .options(
                selectinload(Task.role_links).selectinload(RoleTaskLink.role),
                selectinload(Task.procedure_links).selectinload(TaskProcedureLink.procedure),
            )
        )
    ).scalar_one()
    return _serialize_task(refreshed)


@router.post("/{task_id}/suggest-trainings", response_model=list[TrainingSuggestion])
async def suggest_trainings_for_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.embedding is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task has no embedding")

    matches = await rank_procedure_versions_by_embedding(task.embedding, limit=10, db=db, min_score=0.5)
    return [
        TrainingSuggestion(
            procedure_id=match["procedure_id"],
            procedure_version_id=match["procedure_version_id"],
            training_id=match["training_id"],
            title=(
                match["training_title"]
                or f"{match['procedure_code']} · {match['procedure_title']} · v{match['version_number']}"
            ),
            score=match["score"],
            snippet=match["snippet"][:200],
        )
        for match in matches
    ]
