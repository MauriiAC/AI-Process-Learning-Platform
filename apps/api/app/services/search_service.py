from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.semantic_segment import SemanticSegment
from app.models.procedure import ProcedureVersion
from app.schemas.search import SearchResult
from app.services.embedding_service import get_embedding


async def rank_procedure_versions_by_embedding(
    query_embedding: list[float],
    limit: int,
    db: AsyncSession,
    min_score: float = 0.0,
) -> list[dict]:
    stmt = (
        select(
            SemanticSegment.procedure_version_id,
            SemanticSegment.text_fused,
            SemanticSegment.start_time,
            SemanticSegment.end_time,
            SemanticSegment.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .where(SemanticSegment.embedding.isnot(None))
        .order_by("distance")
        .limit(limit * 5)
    )
    rows = (await db.execute(stmt)).all()

    ordered_version_ids: list = []
    match_by_version_id: dict = {}
    for row in rows:
        score = round(1 - float(row.distance or 1), 4)
        if score < min_score or row.procedure_version_id in match_by_version_id:
            continue
        ordered_version_ids.append(row.procedure_version_id)
        match_by_version_id[row.procedure_version_id] = {
            "procedure_version_id": row.procedure_version_id,
            "snippet": row.text_fused[:300],
            "start_time": row.start_time,
            "end_time": row.end_time,
            "score": score,
        }
        if len(ordered_version_ids) >= limit:
            break

    if not ordered_version_ids:
        return []

    versions = (
        await db.execute(
            select(ProcedureVersion)
            .where(ProcedureVersion.id.in_(ordered_version_ids))
            .options(
                selectinload(ProcedureVersion.procedure),
                selectinload(ProcedureVersion.training),
            )
        )
    ).scalars().all()
    version_by_id = {version.id: version for version in versions}

    results: list[dict] = []
    for version_id in ordered_version_ids:
        version = version_by_id.get(version_id)
        if version is None or version.procedure is None:
            continue
        match = match_by_version_id[version_id]
        results.append(
            {
                **match,
                "procedure_id": version.procedure_id,
                "procedure_code": version.procedure.code,
                "procedure_title": version.procedure.title,
                "version_number": version.version_number,
                "training_id": version.training.id if version.training else None,
                "training_title": version.training.title if version.training else None,
            }
        )
    return results


async def semantic_search(query: str, limit: int, db: AsyncSession) -> list[SearchResult]:
    query_embedding = await get_embedding(query)
    matches = await rank_procedure_versions_by_embedding(query_embedding, limit=limit, db=db, min_score=0.55)
    return [SearchResult(**match) for match in matches]
