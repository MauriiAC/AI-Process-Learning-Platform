import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.incident import Incident, IncidentAnalysisFinding, IncidentAnalysisRun, IncidentRelatedMatch
from app.models.procedure import ProcedureVersion
from app.models.training import Training


def analysis_run_load_options():
    return (
        selectinload(IncidentAnalysisRun.findings)
        .selectinload(IncidentAnalysisFinding.procedure_version)
        .selectinload(ProcedureVersion.procedure),
        selectinload(IncidentAnalysisRun.findings)
        .selectinload(IncidentAnalysisFinding.procedure_version)
        .selectinload(ProcedureVersion.training),
        selectinload(IncidentAnalysisRun.related_matches).selectinload(IncidentRelatedMatch.related_incident),
        selectinload(IncidentAnalysisRun.related_matches)
        .selectinload(IncidentRelatedMatch.related_analysis_run)
        .selectinload(IncidentAnalysisRun.findings)
        .selectinload(IncidentAnalysisFinding.procedure_version)
        .selectinload(ProcedureVersion.procedure),
        selectinload(IncidentAnalysisRun.related_matches)
        .selectinload(IncidentRelatedMatch.related_analysis_run)
        .selectinload(IncidentAnalysisRun.findings)
        .selectinload(IncidentAnalysisFinding.procedure_version)
        .selectinload(ProcedureVersion.training),
    )


async def get_similar_incident_analysis_runs(
    incident_id: uuid.UUID,
    incident_embedding,
    db: AsyncSession,
    limit: int = 3,
    min_score: float = 0.55,
) -> list[dict]:
    if incident_embedding is None:
        return []

    rows = (
        await db.execute(
            select(
                Incident.id,
                Incident.description,
                Incident.embedding.cosine_distance(incident_embedding).label("distance"),
            )
            .where(Incident.id != incident_id, Incident.embedding.isnot(None))
            .order_by("distance")
            .limit(limit * 3)
        )
    ).all()

    matches: list[dict] = []
    for row in rows:
        similarity = max(0.0, min(1.0, 1 - float(row.distance or 1)))
        if similarity < min_score:
            continue

        prior_run = (
            await db.execute(
                select(IncidentAnalysisRun)
                .where(IncidentAnalysisRun.incident_id == row.id)
                .order_by(IncidentAnalysisRun.created_at.desc())
                .options(*analysis_run_load_options())
            )
        ).scalars().first()
        if prior_run is None:
            continue

        matches.append(
            {
                "incident_id": row.id,
                "description": row.description,
                "similarity_score": similarity,
                "analysis_run": prior_run,
            }
        )
        if len(matches) >= limit:
            break
    return matches


def build_finding_memory_line(finding: IncidentAnalysisFinding) -> str:
    subject = "Vacío procedimental detectado"
    if finding.procedure_version is not None and finding.procedure_version.procedure is not None:
        subject = (
            f"{finding.procedure_version.procedure.title} "
            f"v{finding.procedure_version.version_number}"
        )

    parts = [f"{finding.finding_type}: {subject}"]
    if finding.reasoning_summary:
        parts.append(f"motivo={finding.reasoning_summary}")
    if finding.recommended_action:
        parts.append(f"accion={finding.recommended_action}")
    if (
        finding.procedure_version is not None
        and getattr(finding.procedure_version, "training", None) is not None
        and isinstance(finding.procedure_version.training, Training)
    ):
        parts.append(f"training derivado={finding.procedure_version.training.title}")
    return " | ".join(parts)


def build_incident_analysis_context(match: dict) -> str:
    analysis_run = match["analysis_run"]
    parts = [
        f"Incidente similar previo: {match['description']}",
        f"Similitud: {(match['similarity_score'] * 100):.0f}%",
    ]
    if analysis_run.analysis_summary:
        parts.append(f"Analisis previo: {analysis_run.analysis_summary}")
    if analysis_run.resolution_summary:
        parts.append(f"Resolucion previa: {analysis_run.resolution_summary}")
    if analysis_run.findings:
        findings_summary = "; ".join(build_finding_memory_line(finding) for finding in analysis_run.findings[:3])
        parts.append(f"Hallazgos previos: {findings_summary}")
    return " | ".join(parts)
