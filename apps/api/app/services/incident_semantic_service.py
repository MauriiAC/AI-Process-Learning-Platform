import re
from typing import Any

from app.services.ai.provider_factory import get_ai_provider

INCIDENT_TYPE_VALUES = (
    "customer_claim",
    "operational_deviation",
    "product_quality_issue",
    "safety_issue",
    "pricing_issue",
    "other",
)
INCIDENT_CATEGORY_VALUES = (
    "food_quality",
    "food_safety",
    "pricing_billing",
    "inventory_availability",
    "equipment_maintenance",
    "service_experience",
    "process_compliance",
    "cleanliness_hygiene",
    "other",
)
DEFAULT_INCIDENT_TYPE = "other"
DEFAULT_INCIDENT_CATEGORY = "other"
MIN_COMPATIBILITY_FOR_RESULT = 0.45
LEGACY_OR_UNKNOWN_CANDIDATE_COMPATIBILITY = 0.55
LEGACY_CANDIDATE_OTHER_COMPATIBILITY = 0.6
UNKNOWN_SOURCE_CATEGORY_COMPATIBILITY = 0.8

_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "customer_claim": ("cliente", "reporta", "reclamo", "queja", "dijo", "dice", "pidio", "pidió"),
    "operational_deviation": ("no siguio", "no siguió", "desvio", "desvío", "incumpl", "omite", "omitio", "omitió"),
    "product_quality_issue": ("cruda", "quemada", "fria", "fría", "vencido", "mal estado", "calidad"),
    "safety_issue": ("riesgo", "seguridad", "contamin", "temperatura", "intoxic", "peligro"),
    "pricing_issue": ("precio", "ticket", "carteler", "gondola", "góndola", "cobro", "promocion", "promoción"),
}
_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "food_quality": ("kamado", "carne", "cruda", "coccion", "cocción", "fria", "frío", "sabor", "producto"),
    "food_safety": ("temperatura", "cadena de frio", "cadena de frío", "lacteo", "lácteo", "vencido", "aislar"),
    "pricing_billing": ("precio", "ticket", "carteler", "gondola", "góndola", "promocion", "promoción", "caja"),
    "inventory_availability": ("faltante", "sin stock", "quiebre", "reposicion", "reposición", "inventario"),
    "equipment_maintenance": ("kamado", "horno", "equipo", "heladera", "freezer", "maquina", "máquina", "balanza"),
    "service_experience": ("espera", "demora", "mala atencion", "mala atención", "cliente enojado", "fila"),
    "process_compliance": ("procedimiento", "paso", "protocolo", "doble chequeo", "handoff", "cumplimiento", "registro"),
    "cleanliness_hygiene": ("higiene", "manos", "limpieza", "sanitiz", "sucio", "contaminacion", "contaminación"),
}
_CATEGORY_GROUPS: dict[str, str] = {
    "food_quality": "product",
    "food_safety": "product",
    "cleanliness_hygiene": "product",
    "equipment_maintenance": "operations",
    "process_compliance": "operations",
    "inventory_availability": "operations",
    "pricing_billing": "customer",
    "service_experience": "customer",
    "other": "other",
}
_EXPLICIT_CATEGORY_COMPATIBILITY: dict[tuple[str, str], float] = {
    ("food_quality", "food_safety"): 0.72,
    ("food_quality", "equipment_maintenance"): 0.62,
    ("food_quality", "process_compliance"): 0.62,
    ("food_safety", "cleanliness_hygiene"): 0.72,
    ("food_safety", "process_compliance"): 0.68,
    ("pricing_billing", "process_compliance"): 0.58,
    ("service_experience", "pricing_billing"): 0.58,
    ("service_experience", "process_compliance"): 0.55,
    ("inventory_availability", "process_compliance"): 0.62,
}


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = value.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _keyword_score_map(text: str, keywords_by_label: dict[str, tuple[str, ...]]) -> dict[str, int]:
    scores: dict[str, int] = {}
    for label, keywords in keywords_by_label.items():
        scores[label] = sum(1 for keyword in keywords if keyword in text)
    return scores


def _pick_best_label(scores: dict[str, int], default: str) -> str:
    best_label = default
    best_score = 0
    for label, score in scores.items():
        if score > best_score:
            best_label = label
            best_score = score
    return best_label


def infer_incident_semantics(text: str) -> dict[str, Any]:
    normalized_text = _normalize_text(text)
    category_scores = _keyword_score_map(normalized_text, _CATEGORY_KEYWORDS)
    incident_category = _pick_best_label(category_scores, DEFAULT_INCIDENT_CATEGORY)
    type_scores = _keyword_score_map(normalized_text, _TYPE_KEYWORDS)
    incident_type = _pick_best_label(type_scores, DEFAULT_INCIDENT_TYPE)

    extracted_entities: list[str] = []
    for keywords in _CATEGORY_KEYWORDS.values():
        extracted_entities.extend(keyword for keyword in keywords if keyword in normalized_text)

    fallback_entities = _unique_preserve_order(extracted_entities)[:6]
    if not fallback_entities:
        fallback_entities = _unique_preserve_order(
            re.findall(r"[a-zA-ZáéíóúñÁÉÍÓÚÑ]{4,}", normalized_text)
        )[:4]

    return {
        "incident_type": incident_type,
        "incident_category": incident_category,
        "incident_entities": fallback_entities,
    }


def normalize_incident_semantics(raw: dict[str, Any] | None, *, fallback_text: str) -> dict[str, Any]:
    fallback = infer_incident_semantics(fallback_text)
    payload = raw or {}
    incident_type = payload.get("incident_type")
    if incident_type not in INCIDENT_TYPE_VALUES:
        incident_type = fallback["incident_type"]
    incident_category = payload.get("incident_category")
    if incident_category not in INCIDENT_CATEGORY_VALUES:
        incident_category = fallback["incident_category"]
    raw_entities = payload.get("incident_entities")
    if not isinstance(raw_entities, list):
        raw_entities = []
    normalized_entities = _unique_preserve_order([str(item) for item in raw_entities])[:6]
    if not normalized_entities:
        normalized_entities = fallback["incident_entities"]
    return {
        "incident_type": incident_type,
        "incident_category": incident_category,
        "incident_entities": normalized_entities,
    }


async def classify_incident_semantics(
    *,
    description: str,
    severity: str,
    location: str | None,
    role_code: str | None,
) -> dict[str, Any]:
    provider = get_ai_provider()
    response_schema = {
        "type": "object",
        "properties": {
            "incident_type": {
                "type": "string",
                "enum": list(INCIDENT_TYPE_VALUES),
            },
            "incident_category": {
                "type": "string",
                "enum": list(INCIDENT_CATEGORY_VALUES),
            },
            "incident_entities": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 6,
            },
        },
        "required": ["incident_type", "incident_category", "incident_entities"],
        "additionalProperties": False,
    }
    system_prompt = (
        "Clasifica incidencias operativas para búsqueda semántica. "
        "Debes devolver exclusivamente categorías del enum provisto. "
        "No inventes categorías nuevas. Si hay duda, usa 'other'. "
        "Extrae entidades cortas y útiles para el matching, en minúsculas."
    )
    user_prompt = (
        "Clasifica esta incidencia.\n"
        f"descripcion: {description}\n"
        f"severidad: {severity}\n"
        f"ubicacion: {location or 'sin_ubicacion'}\n"
        f"rol: {role_code or 'sin_rol'}"
    )
    try:
        raw = await provider.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
            response_schema=response_schema,
            schema_name="incident_semantics",
        )
    except Exception:
        raw = None
    return normalize_incident_semantics(raw, fallback_text=description)


def build_incident_embedding_input(
    *,
    description: str,
    severity: str,
    location: str | None,
    role_code: str | None,
    incident_type: str,
    incident_category: str,
    incident_entities: list[str] | None,
) -> str:
    normalized_entities = _unique_preserve_order([str(item) for item in (incident_entities or [])])
    lines = [
        f"incident_type: {incident_type}",
        f"incident_category: {incident_category}",
        f"severity: {severity}",
        f"role: {role_code or 'sin_rol'}",
        f"location: {location or 'sin_ubicacion'}",
        f"entities: {', '.join(normalized_entities) if normalized_entities else 'sin_entidades'}",
        f"description: {description.strip()}",
    ]
    return "\n".join(lines)


def infer_procedure_category(*, procedure_code: str | None, procedure_title: str | None, text: str | None) -> str:
    normalized_text = _normalize_text(" ".join(part for part in [procedure_code, procedure_title, text] if part))
    scores = _keyword_score_map(normalized_text, _CATEGORY_KEYWORDS)
    return _pick_best_label(scores, DEFAULT_INCIDENT_CATEGORY)


def _is_known_category(category: str | None) -> bool:
    return bool(category) and category in INCIDENT_CATEGORY_VALUES


def category_compatibility_score(source_category: str | None, candidate_category: str | None) -> float:
    if not _is_known_category(source_category):
        return 1.0
    if not _is_known_category(candidate_category):
        return LEGACY_OR_UNKNOWN_CANDIDATE_COMPATIBILITY
    if source_category == candidate_category:
        return 1.0
    if candidate_category == DEFAULT_INCIDENT_CATEGORY:
        return LEGACY_CANDIDATE_OTHER_COMPATIBILITY
    if source_category == DEFAULT_INCIDENT_CATEGORY:
        return UNKNOWN_SOURCE_CATEGORY_COMPATIBILITY
    explicit = _EXPLICIT_CATEGORY_COMPATIBILITY.get((source_category, candidate_category))
    if explicit is None:
        explicit = _EXPLICIT_CATEGORY_COMPATIBILITY.get((candidate_category, source_category))
    if explicit is not None:
        return explicit
    if _CATEGORY_GROUPS.get(source_category) == _CATEGORY_GROUPS.get(candidate_category):
        return 0.7
    return 0.3


def is_category_compatible(source_category: str | None, candidate_category: str | None) -> bool:
    return category_compatibility_score(source_category, candidate_category) >= MIN_COMPATIBILITY_FOR_RESULT


def entity_overlap_bonus(incident_entities: list[str] | None, candidate_text: str | None) -> float:
    if not incident_entities or not candidate_text:
        return 0.0
    normalized_text = _normalize_text(candidate_text)
    overlap = sum(1 for entity in _unique_preserve_order(list(incident_entities)) if entity in normalized_text)
    return min(0.09, overlap * 0.03)
