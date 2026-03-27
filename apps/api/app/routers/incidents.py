import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.incident import (
    Incident,
    IncidentAnalysisFinding,
    IncidentAnalysisRun,
    IncidentRelatedMatch,
    IncidentTrainingLink,
)
from app.models.procedure import ProcedureVersion
from app.models.role import Role
from app.models.training import Training
from app.models.user import User
from app.schemas.incident import (
    IncidentAnalysisPreviewOut,
    IncidentAnalysisFindingOut,
    IncidentAnalysisRunOut,
    IncidentAnalysisRunCreate,
    IncidentAnalysisRunUpdate,
    IncidentCreate,
    IncidentProcedurePreviewOut,
    IncidentLinkRequest,
    IncidentOut,
    IncidentRelatedMatchOut,
    IncidentSimilarAnalysisPreviewOut,
    IncidentUpdate,
)
from app.schemas.task import TrainingSuggestion
from app.services.embedding_service import get_embedding
from app.services.incident_memory_service import (
    analysis_run_load_options,
    build_incident_analysis_context,
    build_finding_memory_line,
    get_similar_incident_analysis_runs,
)
from app.services.incident_semantic_service import (
    build_incident_embedding_input,
    classify_incident_semantics,
)
from app.services.search_service import MIN_SEMANTIC_SEARCH_SCORE, rank_procedure_versions_by_embedding

router = APIRouter(prefix="/incidents", tags=["incidents"])
OPERATOR_RESOLUTION_STATUSES = {"resolved_by_operator", "escalated"}
INCIDENT_REDEFINITION_HINTS = (
    "cambiar",
    "cambio",
    "ajustar",
    "actualizar",
    "redefin",
    "mejorar",
    "otra forma",
    "desactualiz",
    "insuficiente",
    "confuso",
    "ambigu",
    "no contempla",
)
INCIDENT_GAP_HINTS = (
    "no existe procedimiento",
    "falta procedimiento",
    "sin procedimiento",
    "sin protocolo",
    "no estaba definido",
    "no estaba especificado",
    "nadie sabia",
)


def _analysis_run_query():
    return select(IncidentAnalysisRun).options(*analysis_run_load_options())


def _incident_load_options():
    return (
        selectinload(Incident.role),
        selectinload(Incident.operator_resolution_user),
        selectinload(Incident.operator_selected_procedure_version).selectinload(ProcedureVersion.procedure),
        selectinload(Incident.operator_selected_related_run).selectinload(IncidentAnalysisRun.incident),
    )


def _incident_query():
    return select(Incident).options(*_incident_load_options())


def _incident_out(item: Incident) -> IncidentOut:
    selected_version = getattr(item, "operator_selected_procedure_version", None)
    selected_procedure = getattr(selected_version, "procedure", None) if selected_version is not None else None
    selected_run = getattr(item, "operator_selected_related_run", None)
    selected_related_incident = getattr(selected_run, "incident", None) if selected_run is not None else None
    resolution_user = getattr(item, "operator_resolution_user", None)
    return IncidentOut(
        id=item.id,
        description=item.description,
        severity=item.severity,
        status=item.status,
        incident_type=item.incident_type,
        incident_category=item.incident_category,
        incident_entities=list(item.incident_entities_json or []),
        role_id=item.role_id,
        role_name=item.role.name if getattr(item, "role", None) else None,
        role_code=item.role.code if getattr(item, "role", None) else None,
        location=item.location,
        created_by=item.created_by,
        created_at=item.created_at,
        closed_by=item.closed_by,
        closed_at=item.closed_at,
        operator_comment=item.operator_comment,
        operator_resolution_by=item.operator_resolution_by,
        operator_resolution_by_name=resolution_user.name if resolution_user is not None else None,
        operator_resolution_at=item.operator_resolution_at,
        operator_selected_procedure_id=selected_procedure.id if selected_procedure is not None else None,
        operator_selected_procedure_version_id=item.operator_selected_procedure_version_id,
        operator_selected_procedure_title=selected_procedure.title if selected_procedure is not None else None,
        operator_selected_procedure_version_number=(
            selected_version.version_number if selected_version is not None else None
        ),
        operator_selected_related_run_id=item.operator_selected_related_run_id,
        operator_selected_related_incident_id=(
            selected_related_incident.id if selected_related_incident is not None else None
        ),
        operator_selected_related_incident_description=(
            selected_related_incident.description if selected_related_incident is not None else None
        ),
    )


def _finding_out(item: IncidentAnalysisFinding) -> IncidentAnalysisFindingOut:
    procedure_version = getattr(item, "procedure_version", None)
    procedure = getattr(procedure_version, "procedure", None) if procedure_version is not None else None
    training = getattr(procedure_version, "training", None) if procedure_version is not None else None
    return IncidentAnalysisFindingOut(
        id=item.id,
        analysis_run_id=item.analysis_run_id,
        procedure_id=procedure.id if procedure is not None else None,
        procedure_version_id=item.procedure_version_id,
        procedure_title=procedure.title if procedure is not None else None,
        version_number=procedure_version.version_number if procedure_version is not None else None,
        training_id=training.id if training is not None else None,
        training_title=training.title if training is not None else None,
        finding_type=item.finding_type,
        confidence=item.confidence,
        reasoning_summary=item.reasoning_summary,
        recommended_action=item.recommended_action,
        status=item.status,
        created_at=item.created_at,
    )


def _analysis_run_out(item: IncidentAnalysisRun) -> IncidentAnalysisRunOut:
    return IncidentAnalysisRunOut(
        id=item.id,
        incident_id=item.incident_id,
        source=item.source,
        analysis_summary=item.analysis_summary,
        resolution_summary=item.resolution_summary,
        created_at=item.created_at,
        findings=[_finding_out(finding) for finding in item.findings],
        related_matches=[
            IncidentRelatedMatchOut(
                id=match.id,
                related_incident_id=match.related_incident_id,
                related_incident_description=match.related_incident.description,
                related_analysis_run_id=match.related_analysis_run_id,
                related_analysis_summary=(
                    match.related_analysis_run.analysis_summary if getattr(match, "related_analysis_run", None) else None
                ),
                related_resolution_summary=(
                    match.related_analysis_run.resolution_summary if getattr(match, "related_analysis_run", None) else None
                ),
                related_findings=[
                    _finding_out(finding)
                    for finding in (
                        match.related_analysis_run.findings if getattr(match, "related_analysis_run", None) else []
                    )
                ],
                similarity_score=match.similarity_score,
                rationale=match.rationale,
            )
            for match in item.related_matches
        ],
    )


async def _validate_analysis_run_payload(payload: IncidentAnalysisRunCreate | IncidentAnalysisRunUpdate, db: AsyncSession) -> None:
    version_ids = {finding.procedure_version_id for finding in payload.findings if finding.procedure_version_id is not None}
    if not version_ids:
        return

    rows = list(
        (
            await db.execute(select(ProcedureVersion.id).where(ProcedureVersion.id.in_(version_ids)))
        )
        .scalars()
        .all()
    )
    missing = version_ids - set(rows)
    if missing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedure version not found")


def _apply_incident_status_change(incident: Incident, next_status: str, current_user: User) -> None:
    if next_status == incident.status:
        return
    incident.status = next_status
    if next_status == "closed":
        incident.closed_at = datetime.now(timezone.utc)
        incident.closed_by = current_user.id
        return
    incident.closed_at = None
    incident.closed_by = None
    if next_status in OPERATOR_RESOLUTION_STATUSES:
        incident.operator_resolution_at = datetime.now(timezone.utc)
        incident.operator_resolution_by = current_user.id


def _touch_operator_resolution(incident: Incident, current_user: User) -> None:
    incident.operator_resolution_at = datetime.now(timezone.utc)
    incident.operator_resolution_by = current_user.id


def _incident_role_code(role: Role | None) -> str | None:
    return role.code if role is not None else None


async def _classify_incident_payload(
    *,
    description: str,
    severity: str,
    location: str | None,
    role: Role | None,
) -> dict:
    return await classify_incident_semantics(
        description=description,
        severity=severity,
        location=location,
        role_code=_incident_role_code(role),
    )


async def _build_incident_embedding(
    *,
    description: str,
    severity: str,
    location: str | None,
    role: Role | None,
    semantics: dict,
) -> list[float]:
    return await get_embedding(
        build_incident_embedding_input(
            description=description,
            severity=severity,
            location=location,
            role_code=_incident_role_code(role),
            incident_type=semantics["incident_type"],
            incident_category=semantics["incident_category"],
            incident_entities=semantics["incident_entities"],
        )
    )


def _default_action_for_type(finding_type: str) -> str:
    if finding_type == "not_followed":
        return "Verificar cumplimiento operativo y reforzar el entrenamiento asociado."
    if finding_type == "needs_redefinition":
        return "Revisar el procedimiento y crear una nueva version con pasos y controles mas claros."
    if finding_type == "missing_procedure":
        return "Disenar y documentar un procedimiento nuevo para cubrir este escenario."
    return "Validar el rol de este procedimiento en el incidente y definir la remediacion mas adecuada."


def _contains_any(text: str, fragments: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(fragment in lowered for fragment in fragments)


def _dominant_precedent_finding_type(precedent_findings: list[tuple[dict, IncidentAnalysisFinding]]) -> str | None:
    prioritized = [finding.finding_type for _related, finding in precedent_findings if finding.finding_type != "contributing_factor"]
    if prioritized:
        return prioritized[0]
    if precedent_findings:
        return precedent_findings[0][1].finding_type
    return None


def _infer_finding_type_for_match(
    incident: Incident,
    match: dict,
    precedent_findings: list[tuple[dict, IncidentAnalysisFinding]],
) -> str:
    precedent_type = _dominant_precedent_finding_type(precedent_findings)
    if precedent_type in {"not_followed", "needs_redefinition", "missing_procedure"}:
        return precedent_type

    description = incident.description or ""
    if _contains_any(description, INCIDENT_REDEFINITION_HINTS):
        return "needs_redefinition"

    if match.get("step_title") or match.get("reference_segment_range") or match.get("reference_quote"):
        return "not_followed"

    if (match.get("score") or 0) >= 0.72:
        return "needs_redefinition"

    return "not_followed"


def _finding_payload_to_model(payload, source: str) -> IncidentAnalysisFinding:
    return IncidentAnalysisFinding(
        procedure_version_id=payload.procedure_version_id,
        finding_type=payload.finding_type,
        confidence=payload.confidence,
        reasoning_summary=payload.reasoning_summary,
        recommended_action=payload.recommended_action or _default_action_for_type(payload.finding_type),
        status=payload.status or ("confirmed" if source == "manual" else "suggested"),
    )


@router.post("", response_model=IncidentOut, status_code=status.HTTP_201_CREATED)
async def create_incident(
    payload: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role: Role | None = None
    if payload.role_id:
        role = (await db.execute(select(Role).where(Role.id == payload.role_id))).scalar_one_or_none()
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    semantics = await _classify_incident_payload(
        description=payload.description,
        severity=payload.severity,
        location=payload.location,
        role=role,
    )
    embedding = await _build_incident_embedding(
        description=payload.description,
        severity=payload.severity,
        location=payload.location,
        role=role,
        semantics=semantics,
    )

    incident = Incident(
        description=payload.description,
        severity=payload.severity,
        status="open",
        incident_type=semantics["incident_type"],
        incident_category=semantics["incident_category"],
        incident_entities_json=semantics["incident_entities"],
        role_id=payload.role_id,
        location=payload.location,
        created_by=current_user.id,
        embedding=embedding,
    )
    db.add(incident)
    await db.commit()
    result = await db.execute(_incident_query().where(Incident.id == incident.id))
    incident = result.scalar_one()
    return _incident_out(incident)


@router.get("", response_model=list[IncidentOut])
async def list_incidents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(_incident_query().order_by(Incident.created_at.desc()))
    return [_incident_out(item) for item in result.scalars().all()]


@router.get("/{incident_id}", response_model=IncidentOut)
async def get_incident(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    incident = (await db.execute(_incident_query().where(Incident.id == incident_id))).scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return _incident_out(incident)


@router.patch("/{incident_id}", response_model=IncidentOut)
async def update_incident(
    incident_id: uuid.UUID,
    payload: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    incident = (await db.execute(select(Incident).where(Incident.id == incident_id))).scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    changes = payload.model_dump(exclude_unset=True)
    role: Role | None = None
    if "operator_comment" in changes:
        changes["operator_comment"] = (changes["operator_comment"] or "").strip() or None
    if "role_id" in changes and changes["role_id"] is not None:
        role = (await db.execute(select(Role).where(Role.id == changes["role_id"]))).scalar_one_or_none()
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    elif incident.role_id is not None:
        role = (await db.execute(select(Role).where(Role.id == incident.role_id))).scalar_one_or_none()
    if "operator_selected_procedure_version_id" in changes and changes["operator_selected_procedure_version_id"] is not None:
        version = (
            await db.execute(
                select(ProcedureVersion.id).where(
                    ProcedureVersion.id == changes["operator_selected_procedure_version_id"]
                )
            )
        ).scalar_one_or_none()
        if version is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedure version not found")
    if "operator_selected_related_run_id" in changes and changes["operator_selected_related_run_id"] is not None:
        related_run = (
            await db.execute(
                select(IncidentAnalysisRun.id).where(
                    IncidentAnalysisRun.id == changes["operator_selected_related_run_id"]
                )
            )
        ).scalar_one_or_none()
        if related_run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Related analysis run not found")

    next_status = changes.get("status", incident.status)
    if "status" in changes and next_status in OPERATOR_RESOLUTION_STATUSES and not changes.get("operator_comment"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Operator comment is required when marking an incident as resolved or escalated",
        )

    for field, value in changes.items():
        if field == "status":
            _apply_incident_status_change(incident, value, current_user)
            continue
        setattr(incident, field, value)

    semantic_inputs_changed = bool({"description", "severity", "role_id", "location"}.intersection(changes))
    if semantic_inputs_changed:
        next_description = changes.get("description", incident.description)
        next_severity = changes.get("severity", incident.severity)
        next_location = changes.get("location", incident.location)
        if "role_id" in changes and changes["role_id"] is None:
            role = None
        semantics = await _classify_incident_payload(
            description=next_description,
            severity=next_severity,
            location=next_location,
            role=role,
        )
        incident.incident_type = semantics["incident_type"]
        incident.incident_category = semantics["incident_category"]
        incident.incident_entities_json = semantics["incident_entities"]
        incident.embedding = await _build_incident_embedding(
            description=next_description,
            severity=next_severity,
            location=next_location,
            role=role,
            semantics=semantics,
        )
    if next_status in OPERATOR_RESOLUTION_STATUSES and {
        "operator_comment",
        "operator_selected_procedure_version_id",
        "operator_selected_related_run_id",
        "status",
    }.intersection(changes):
        _touch_operator_resolution(incident, current_user)

    await db.commit()
    incident = (await db.execute(_incident_query().where(Incident.id == incident_id))).scalar_one()
    return _incident_out(incident)


@router.delete("/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    incident = (await db.execute(select(Incident).where(Incident.id == incident_id))).scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    await db.delete(incident)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{incident_id}/suggest-trainings", response_model=list[TrainingSuggestion])
async def suggest_trainings_for_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    if incident.embedding is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incident has no embedding")

    matches = await rank_procedure_versions_by_embedding(
        incident.embedding,
        limit=10,
        db=db,
        min_score=MIN_SEMANTIC_SEARCH_SCORE,
        context_category=incident.incident_category,
        context_entities=list(incident.incident_entities_json or []),
    )
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


@router.get("/{incident_id}/analysis-runs", response_model=list[IncidentAnalysisRunOut])
async def get_incident_analysis_runs(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rows = list(
        (
            await db.execute(
                _analysis_run_query()
                .where(IncidentAnalysisRun.incident_id == incident_id)
                .order_by(IncidentAnalysisRun.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [_analysis_run_out(row) for row in rows]


@router.post(
    "/{incident_id}/analysis-runs",
    response_model=IncidentAnalysisRunOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_incident_analysis_run(
    incident_id: uuid.UUID,
    payload: IncidentAnalysisRunCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    incident = (await db.execute(select(Incident).where(Incident.id == incident_id))).scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    if incident.status == "closed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Closed incidents cannot receive new analysis runs")
    await _validate_analysis_run_payload(payload, db)

    run = IncidentAnalysisRun(
        incident_id=incident_id,
        source="manual",
        analysis_summary=payload.analysis_summary,
        resolution_summary=payload.resolution_summary,
        created_by=current_user.id,
    )
    run.findings = [_finding_payload_to_model(finding, source="manual") for finding in payload.findings]
    db.add(run)
    await db.commit()
    run = (
        await db.execute(_analysis_run_query().where(IncidentAnalysisRun.id == run.id))
    ).scalar_one()
    return _analysis_run_out(run)


@router.patch(
    "/{incident_id}/analysis-runs/{run_id}",
    response_model=IncidentAnalysisRunOut,
)
async def update_incident_analysis_run(
    incident_id: uuid.UUID,
    run_id: uuid.UUID,
    payload: IncidentAnalysisRunUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = (
        await db.execute(
            select(IncidentAnalysisRun).where(
                IncidentAnalysisRun.id == run_id,
                IncidentAnalysisRun.incident_id == incident_id,
            )
        )
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident analysis run not found")
    incident = (await db.execute(select(Incident).where(Incident.id == incident_id))).scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    if incident.status == "closed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Closed incidents cannot be edited")

    await _validate_analysis_run_payload(payload, db)
    run.analysis_summary = payload.analysis_summary
    run.resolution_summary = payload.resolution_summary
    run.findings = [_finding_payload_to_model(finding, source=run.source) for finding in payload.findings]
    await db.commit()
    run = (
        await db.execute(_analysis_run_query().where(IncidentAnalysisRun.id == run.id))
    ).scalar_one()
    return _analysis_run_out(run)


@router.post("/{incident_id}/analyze-procedures", response_model=IncidentAnalysisPreviewOut)
async def analyze_incident_procedures(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    incident = (await db.execute(select(Incident).where(Incident.id == incident_id))).scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    if incident.embedding is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incident has no embedding")
    if incident.status == "closed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Closed incidents cannot be analyzed")

    related_incidents = await get_similar_incident_analysis_runs(
        incident_id,
        incident.embedding,
        db=db,
        incident_category=incident.incident_category,
    )
    matches = await rank_procedure_versions_by_embedding(
        incident.embedding,
        limit=5,
        db=db,
        min_score=MIN_SEMANTIC_SEARCH_SCORE,
        context_category=incident.incident_category,
        context_entities=list(incident.incident_entities_json or []),
    )
    return IncidentAnalysisPreviewOut(
        procedure_matches=[
            IncidentProcedurePreviewOut(
                procedure_id=match["procedure_id"],
                procedure_version_id=match["procedure_version_id"],
                procedure_code=match["procedure_code"],
                procedure_title=match["procedure_title"],
                version_number=match["version_number"],
                training_id=match["training_id"],
                training_title=match["training_title"],
                score=match["score"],
                snippet=match["snippet"],
                step_index=match.get("step_index"),
                step_title=match.get("step_title"),
                reference_segment_range=match.get("reference_segment_range"),
                reference_quote=match.get("reference_quote"),
                match_source=match.get("match_source"),
            )
            for match in matches
        ],
        similar_analyses=[
            IncidentSimilarAnalysisPreviewOut(
                incident_id=related["incident_id"],
                description=related["description"],
                similarity_score=related["similarity_score"],
                analysis_run=_analysis_run_out(related["analysis_run"]),
            )
            for related in related_incidents
        ],
    )


@router.post("/{incident_id}/link-training", status_code=status.HTTP_201_CREATED)
async def link_training_to_incident(
    incident_id: uuid.UUID,
    payload: IncidentLinkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    result = await db.execute(select(Training).where(Training.id == payload.training_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")

    duplicate = (
        await db.execute(
            select(IncidentTrainingLink).where(
                IncidentTrainingLink.incident_id == incident_id,
                IncidentTrainingLink.training_id == payload.training_id,
            )
        )
    ).scalar_one_or_none()
    if duplicate:
        return {"detail": "Training linked to incident"}

    link = IncidentTrainingLink(
        incident_id=incident_id,
        training_id=payload.training_id,
        source=payload.source,
    )
    db.add(link)
    await db.commit()
    return {"detail": "Training linked to incident"}
