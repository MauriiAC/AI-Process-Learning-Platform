"""Seed script for the procedure-centric demo domain.

Run migrations first:

    alembic upgrade head
    python seed.py
"""

import asyncio
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import async_session
from app.core.security import hash_password
from app.models.assignment import Assignment
from app.models.change_event import ChangeEvent
from app.models.incident import Incident, IncidentAnalysisFinding, IncidentAnalysisRun
from app.models.procedure import (
    Procedure,
    ProcedureVersion,
    ProcedureVersionChunk,
    ProcedureVersionStructure,
    ProcedureVersionTranscript,
    TaskProcedureLink,
)
from app.models.quiz import QuizQuestion
from app.models.role import Role, RoleTaskLink, UserRoleAssignment
from app.models.semantic_segment import SemanticSegment
from app.models.task import Task
from app.models.training import Training, TrainingStructure
from app.models.user import User
from app.models.video_frame import VideoFrame
from app.services.compliance_service import sync_user_procedure_compliance
from app.services.embedding_service import get_embedding

_embedding_counter = 0


DEMO_USERS = [
    {"name": "Admin Demo", "email": "admin@demo.com", "password": "admin123", "location": "Buenos Aires"},
    {"name": "Sofía Jefa de Turno", "email": "sofia@demo.com", "password": "demo123", "location": "Buenos Aires"},
    {"name": "Carlos Cocina", "email": "carlos@demo.com", "password": "demo123", "location": "Buenos Aires"},
    {"name": "Ana Caja", "email": "ana@demo.com", "password": "demo123", "location": "Córdoba"},
]

DEMO_ROLES = [
    {"code": "store-supervisor", "name": "Supervisor de sucursal", "description": "Coordina operación y verifica cumplimiento."},
    {"code": "kitchen-operator", "name": "Operador de cocina", "description": "Ejecuta procedimientos de cocina y control."},
    {"code": "front-desk", "name": "Atención al cliente", "description": "Opera caja, atención y manejo de reclamos."},
]

DEMO_TASKS = [
    {"title": "Controlar temperatura de conservación", "description": "Verificar y registrar temperaturas en heladeras."},
    {"title": "Despachar pedido al cliente", "description": "Entregar pedidos validando contenido y tiempos."},
    {"title": "Gestionar reclamo de cliente", "description": "Registrar, clasificar y escalar reclamos."},
]

DEMO_PROCEDURES = [
    {
        "code": "PROC-COLD-CHAIN",
        "title": "Control de cadena de frío",
        "description": "Mantener y auditar la conservación segura de productos refrigerados.",
        "role_code": "kitchen-operator",
        "task_title": "Controlar temperatura de conservación",
        "content": "Paso 1: revisar temperatura inicial. Paso 2: registrar desvíos. Paso 3: aislar producto comprometido.",
        "training_title": "Cadena de frío y registro seguro",
    },
    {
        "code": "PROC-ORDER-HANDOFF",
        "title": "Entrega y validación de pedidos",
        "description": "Estandarizar la entrega de pedidos y prevenir faltantes.",
        "role_code": "front-desk",
        "task_title": "Despachar pedido al cliente",
        "content": "Paso 1: validar ticket. Paso 2: revisar contenido. Paso 3: confirmar con el cliente.",
        "training_title": "Despacho correcto de pedidos",
    },
    {
        "code": "PROC-CUSTOMER-COMPLAINT",
        "title": "Gestión de reclamos de clientes",
        "description": "Canalizar reclamos, recopilar evidencia y activar acciones correctivas.",
        "role_code": "store-supervisor",
        "task_title": "Gestionar reclamo de cliente",
        "content": "Paso 1: escuchar el reclamo. Paso 2: registrar evidencia. Paso 3: asignar seguimiento y cierre.",
        "training_title": "Análisis y resolución de reclamos",
    },
]


def _build_structure(title: str, content: str) -> dict:
    steps = [part.strip() for part in content.split(". ") if part.strip()]
    return {
        "title": title,
        "objectives": [
            f"Ejecutar correctamente {title.lower()}",
            "Detectar desvíos operativos y documentarlos",
        ],
        "steps": [
            {
                "title": f"Paso {index + 1}",
                "description": step,
                "segment_ref": f"{index * 10}s-{(index + 1) * 10}s",
            }
            for index, step in enumerate(steps)
        ],
        "critical_points": [
            {
                "point": "Registrar evidencia",
                "why": "Permite trazabilidad y acciones correctivas",
                "segment_ref": "10s-20s",
            }
        ],
    }


def log_progress(message: str) -> None:
    print(f"[seed] {message}", flush=True)


async def safe_embedding(text: str, label: str) -> list[float] | None:
    global _embedding_counter
    _embedding_counter += 1
    log_progress(f"embedding {_embedding_counter}: {label}")
    try:
        return await get_embedding(text)
    except Exception as exc:
        log_progress(f"embedding {_embedding_counter} failed: {label} ({exc})")
        return None


async def get_or_create_user(db, payload: dict) -> User:
    existing = (await db.execute(select(User).where(User.email == payload["email"]))).scalar_one_or_none()
    if existing:
        return existing
    user = User(
        name=payload["name"],
        email=payload["email"],
        hashed_password=hash_password(payload["password"]),
        location=payload["location"],
    )
    db.add(user)
    await db.flush()
    return user


async def seed():
    log_progress("inicio")
    async with async_session() as db:
        log_progress("creando usuarios demo")
        admin = None
        users: dict[str, User] = {}
        for item in DEMO_USERS:
            user = await get_or_create_user(db, item)
            users[item["email"]] = user
            if item["email"] == "admin@demo.com":
                admin = user

        if admin is None:
            raise RuntimeError("Admin demo user is required")

        log_progress("creando roles demo")
        roles: dict[str, Role] = {}
        for item in DEMO_ROLES:
            role = (await db.execute(select(Role).where(Role.code == item["code"]))).scalar_one_or_none()
            if role is None:
                role = Role(**item)
                db.add(role)
                await db.flush()
            roles[item["code"]] = role

        log_progress("creando tareas demo")
        tasks: dict[str, Task] = {}
        for item in DEMO_TASKS:
            task = (await db.execute(select(Task).where(Task.title == item["title"]))).scalar_one_or_none()
            if task is None:
                task = Task(
                    title=item["title"],
                    description=item["description"],
                    embedding=await safe_embedding(
                        f"{item['title']} {item['description']}",
                        label=f"task:{item['title']}",
                    ),
                )
                db.add(task)
                await db.flush()
            tasks[item["title"]] = task

        log_progress("creando asignaciones usuario-rol")
        role_assignments_map = {
            "sofia@demo.com": "store-supervisor",
            "carlos@demo.com": "kitchen-operator",
            "ana@demo.com": "front-desk",
        }
        for email, role_code in role_assignments_map.items():
            user = users[email]
            role = roles[role_code]
            existing = (
                await db.execute(
                    select(UserRoleAssignment).where(
                        UserRoleAssignment.user_id == user.id,
                        UserRoleAssignment.role_id == role.id,
                        UserRoleAssignment.status == "active",
                    )
                )
            ).scalar_one_or_none()
            if existing is None:
                db.add(
                    UserRoleAssignment(
                        user_id=user.id,
                        role_id=role.id,
                        location=user.location,
                        status="active",
                        starts_on=date.today() - timedelta(days=30),
                    )
                )

        procedures: dict[str, Procedure] = {}
        versions: dict[str, ProcedureVersion] = {}
        trainings: dict[str, Training] = {}

        for item in DEMO_PROCEDURES:
            log_progress(f"procesando procedimiento {item['code']}")
            role = roles[item["role_code"]]
            procedure = (await db.execute(select(Procedure).where(Procedure.code == item["code"]))).scalar_one_or_none()
            if procedure is None:
                procedure = Procedure(
                    code=item["code"],
                    title=item["title"],
                    description=item["description"],
                    owner_role_id=role.id,
                    status="active",
                    created_by=admin.id,
                )
                db.add(procedure)
                await db.flush()
            procedures[item["code"]] = procedure

            version = (
                await db.execute(
                    select(ProcedureVersion).where(
                        ProcedureVersion.procedure_id == procedure.id,
                        ProcedureVersion.version_number == 1,
                    )
                )
            ).scalar_one_or_none()
            if version is None:
                version = ProcedureVersion(
                    procedure_id=procedure.id,
                    version_number=1,
                    status="published",
                    change_summary="Versión inicial demo",
                    change_reason="Bootstrap del dominio centrado en procedimientos",
                    effective_from=date.today() - timedelta(days=15),
                    content_json={"steps": item["content"].split(". ")},
                    content_text=item["content"],
                    source_asset_type="video",
                    source_storage_key=f"demo/{item['code'].lower()}.mp4",
                    source_mime="video/mp4",
                    source_size=12_000_000,
                    source_processing_status="READY",
                    source_processing_error=None,
                    source_processed_at=datetime.now(timezone.utc),
                    created_by=admin.id,
                    embedding=await safe_embedding(item["content"], label=f"procedure-version:{item['code']}"),
                )
                db.add(version)
                await db.flush()
            versions[item["code"]] = version

            transcript = (
                await db.execute(
                    select(ProcedureVersionTranscript).where(
                        ProcedureVersionTranscript.procedure_version_id == version.id
                    )
                )
            ).scalar_one_or_none()
            if transcript is None:
                db.add(
                    ProcedureVersionTranscript(
                        procedure_version_id=version.id,
                        transcript_raw=item["content"],
                        language="es",
                    )
                )

            existing_chunks = list(
                (
                    await db.execute(
                        select(ProcedureVersionChunk).where(ProcedureVersionChunk.procedure_version_id == version.id)
                    )
                )
                .scalars()
                .all()
            )
            if not existing_chunks:
                sentences = [part.strip() for part in item["content"].split(". ") if part.strip()]
                for index, sentence in enumerate(sentences):
                    db.add(
                        ProcedureVersionChunk(
                            procedure_version_id=version.id,
                            chunk_index=index,
                            text=sentence,
                            start_time=float(index * 10),
                            end_time=float((index + 1) * 10),
                            embedding=await safe_embedding(
                                sentence,
                                label=f"chunk:{item['code']}:#{index + 1}",
                            ),
                        )
                    )

            existing_frames = list(
                (
                    await db.execute(select(VideoFrame).where(VideoFrame.procedure_version_id == version.id))
                )
                .scalars()
                .all()
            )
            if not existing_frames:
                db.add(
                    VideoFrame(
                        procedure_version_id=version.id,
                        timestamp=3.0,
                        storage_key=f"frames/{version.id}/frame_0001.jpg",
                        caption=f"Vista operativa del procedimiento {item['title'].lower()}",
                    )
                )
                db.add(
                    VideoFrame(
                        procedure_version_id=version.id,
                        timestamp=12.0,
                        storage_key=f"frames/{version.id}/frame_0002.jpg",
                        caption="Registro visual de control y validación final",
                    )
                )

            existing_segments = list(
                (
                    await db.execute(
                        select(SemanticSegment).where(SemanticSegment.procedure_version_id == version.id)
                    )
                )
                .scalars()
                .all()
            )
            if not existing_segments:
                db.add(
                    SemanticSegment(
                        procedure_version_id=version.id,
                        start_time=0.0,
                        end_time=10.0,
                        text_fused=item["content"],
                        embedding=await safe_embedding(
                            f"{item['title']} {item['content']}",
                            label=f"semantic-segment:{item['code']}",
                        ),
                    )
                )

            structure = _build_structure(item["title"], item["content"])
            existing_structure = (
                await db.execute(
                    select(ProcedureVersionStructure).where(
                        ProcedureVersionStructure.procedure_version_id == version.id
                    )
                )
            ).scalar_one_or_none()
            if existing_structure is None:
                db.add(
                    ProcedureVersionStructure(
                        procedure_version_id=version.id,
                        structure_json=structure,
                    )
                )
            else:
                existing_structure.structure_json = structure

            task = tasks[item["task_title"]]
            role_task_link = (
                await db.execute(
                    select(RoleTaskLink).where(RoleTaskLink.role_id == role.id, RoleTaskLink.task_id == task.id)
                )
            ).scalar_one_or_none()
            if role_task_link is None:
                db.add(RoleTaskLink(role_id=role.id, task_id=task.id, is_required=True))

            task_procedure_link = (
                await db.execute(
                    select(TaskProcedureLink).where(
                        TaskProcedureLink.task_id == task.id,
                        TaskProcedureLink.procedure_id == procedure.id,
                    )
                )
            ).scalar_one_or_none()
            if task_procedure_link is None:
                db.add(TaskProcedureLink(task_id=task.id, procedure_id=procedure.id, is_primary=True))

            training = (
                await db.execute(select(Training).where(Training.procedure_version_id == version.id))
            ).scalar_one_or_none()
            if training is None:
                training = Training(
                    procedure_version_id=version.id,
                    title=item["training_title"],
                    status="published",
                    summary=f"Training derivado de {item['code']}",
                    created_by=admin.id,
                )
                db.add(training)
                await db.flush()
            existing_training_structure = (
                await db.execute(select(TrainingStructure).where(TrainingStructure.training_id == training.id))
            ).scalar_one_or_none()
            if existing_training_structure is None:
                db.add(TrainingStructure(training_id=training.id, structure_json=structure))
            else:
                existing_training_structure.structure_json = structure
            existing_quiz = (
                await db.execute(select(QuizQuestion).where(QuizQuestion.training_id == training.id))
            ).scalar_one_or_none()
            if existing_quiz is None:
                db.add(
                    QuizQuestion(
                        training_id=training.id,
                        question_json={
                            "position": 1,
                            "type": "mcq",
                            "question": f"¿Cuál es un paso crítico de {item['title'].lower()}?",
                            "options": [
                                "Documentar el proceso y validar desvíos",
                                "Saltar el registro si no hay tiempo",
                                "Esperar indicaciones del cliente",
                                "Delegar el control sin evidencia",
                            ],
                            "correct_answer": 0,
                            "evidence": {
                                "segment_range": "0s-10s",
                                "quote": item["content"][:120],
                            },
                            "verified": True,
                        },
                    )
                )
            trainings[item["code"]] = training

        await db.flush()

        log_progress("creando assignments demo")
        assignment_specs = [
            ("carlos@demo.com", "PROC-COLD-CHAIN", "completed", 93),
            ("ana@demo.com", "PROC-ORDER-HANDOFF", "assigned", None),
            ("sofia@demo.com", "PROC-CUSTOMER-COMPLAINT", "in_progress", None),
        ]
        for email, procedure_code, status_value, score in assignment_specs:
            user = users[email]
            training = trainings[procedure_code]
            existing = (
                await db.execute(
                    select(Assignment).where(Assignment.training_id == training.id, Assignment.user_id == user.id)
                )
            ).scalar_one_or_none()
            if existing is None:
                existing = Assignment(
                    training_id=training.id,
                    user_id=user.id,
                    assignment_type="training",
                    status=status_value,
                    due_date=date.today() + timedelta(days=7),
                    score=score,
                    attempts=1 if score is not None else 0,
                    completed_at=datetime.now(timezone.utc) if status_value == "completed" else None,
                    started_at=datetime.now(timezone.utc) if status_value in {"completed", "in_progress"} else None,
                )
                db.add(existing)

        incident = (
            await db.execute(select(Incident).where(Incident.description.like("%pedido llegó incompleto%")))
        ).scalar_one_or_none()
        if incident is None:
            incident = Incident(
                description="Un cliente reportó que su pedido llegó incompleto y sin validación final.",
                severity="high",
                role_id=roles["front-desk"].id,
                location="Córdoba",
                created_by=admin.id,
                embedding=await safe_embedding(
                    "pedido incompleto validación final entrega cliente",
                    label="incident:pedido incompleto",
                ),
            )
            db.add(incident)
            await db.flush()
        existing_incident_analysis = (
            await db.execute(select(IncidentAnalysisRun).where(IncidentAnalysisRun.incident_id == incident.id))
        ).scalar_one_or_none()
        if existing_incident_analysis is None:
            existing_incident_analysis = IncidentAnalysisRun(
                incident_id=incident.id,
                source="manual",
                analysis_summary=(
                    "Se detectaron multiples causas: no se siguio la validacion final, faltan controles "
                    "preventivos y el flujo de reclamos requiere redefinicion."
                ),
                resolution_summary=(
                    "Reforzar entrenamiento de despacho, redefinir el flujo de reclamos recurrentes y crear "
                    "un control de pre-despacho."
                ),
                created_by=admin.id,
            )
            db.add(existing_incident_analysis)
            await db.flush()

        existing_findings = list(
            (
                await db.execute(
                    select(IncidentAnalysisFinding).where(
                        IncidentAnalysisFinding.analysis_run_id == existing_incident_analysis.id
                    )
                )
            )
            .scalars()
            .all()
        )
        for finding in existing_findings:
            await db.delete(finding)

        db.add(
            IncidentAnalysisFinding(
                analysis_run_id=existing_incident_analysis.id,
                procedure_version_id=versions["PROC-ORDER-HANDOFF"].id,
                finding_type="not_followed",
                confidence=0.94,
                reasoning_summary=(
                    "El equipo no ejecuto la validacion final del pedido antes de entregarlo al cliente."
                ),
                recommended_action=(
                    "Reforzar el training de despacho correcto y exigir checklist visible en mostrador."
                ),
                status="confirmed",
            )
        )
        db.add(
            IncidentAnalysisFinding(
                analysis_run_id=existing_incident_analysis.id,
                procedure_version_id=versions["PROC-CUSTOMER-COMPLAINT"].id,
                finding_type="needs_redefinition",
                confidence=0.72,
                reasoning_summary=(
                    "El procedimiento de gestion de reclamos no contempla bien incidentes repetitivos de "
                    "entrega incompleta ni escalamiento rapido."
                ),
                recommended_action=(
                    "Crear una nueva version del procedimiento de reclamos con disparadores de escalamiento y "
                    "captura de evidencia recurrente."
                ),
                status="confirmed",
            )
        )
        db.add(
            IncidentAnalysisFinding(
                analysis_run_id=existing_incident_analysis.id,
                procedure_version_id=None,
                finding_type="missing_procedure",
                confidence=0.68,
                reasoning_summary=(
                    "Falta un procedimiento preventivo especifico para control final de integridad del pedido "
                    "antes de la entrega."
                ),
                recommended_action="Definir un procedimiento de pre-despacho con doble chequeo y registro.",
                status="confirmed",
            )
        )

        follow_up_incident = (
            await db.execute(select(Incident).where(Incident.description.like("%pedido fue entregado sin chequear%")))
        ).scalar_one_or_none()
        if follow_up_incident is None:
            follow_up_incident = Incident(
                description="Otro cliente indicó que su pedido fue entregado sin chequear y faltaban productos.",
                severity="medium",
                role_id=roles["front-desk"].id,
                location="Buenos Aires",
                created_by=admin.id,
                embedding=await safe_embedding(
                    "pedido entregado sin chequear faltaban productos validación final",
                    label="incident:entrega sin chequear",
                ),
            )
            db.add(follow_up_incident)

        change_event = (await db.execute(select(ChangeEvent).where(ChangeEvent.title == "Nueva exigencia de control de conservación"))).scalar_one_or_none()
        if change_event is None:
            change_event = ChangeEvent(
                title="Nueva exigencia de control de conservación",
                description="Se requiere duplicar la frecuencia de control y documentar acciones correctivas ante desvíos.",
                source_type="regulation",
                status="review",
                effective_from=date.today() + timedelta(days=10),
                context_json={"issuer": "Autoridad Sanitaria Local"},
                created_by=admin.id,
                embedding=await safe_embedding(
                    "control conservación frecuencia acciones correctivas cadena de frío",
                    label="change-event:control de conservación",
                ),
            )
            db.add(change_event)

        log_progress("sincronizando compliance")
        await sync_user_procedure_compliance(db)
        log_progress("commit final")
        await db.commit()

    log_progress("completo")
    print("Seed complete: migrate with Alembic first, then run python seed.py", flush=True)


if __name__ == "__main__":
    asyncio.run(seed())
