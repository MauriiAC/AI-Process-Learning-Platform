import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2, FileSearch, Loader2, Sparkles } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { incidentSeverityMeta, incidentStatusMeta, type IncidentItem, type IncidentStatus } from "@/lib/operatorData";
import { getSemanticScoreDetail, getSemanticScoreLabel } from "@/lib/semanticScore";
import api from "@/services/api";

interface AnalysisFinding {
  id: string;
  procedure_id?: string | null;
  procedure_title?: string | null;
  version_number?: number | null;
  reasoning_summary?: string | null;
  recommended_action?: string | null;
}

interface AnalysisRun {
  id: string;
  analysis_summary?: string | null;
  resolution_summary?: string | null;
  findings: AnalysisFinding[];
}

interface ProcedurePreviewMatch {
  procedure_id: string;
  procedure_version_id: string;
  procedure_code: string;
  procedure_title: string;
  version_number: number;
  training_title?: string | null;
  score: number;
  snippet: string;
  step_index?: number | null;
  step_title?: string | null;
  reference_segment_range?: string | null;
}

interface IncidentAnalysisPreview {
  procedure_matches: ProcedurePreviewMatch[];
  similar_analyses: Array<{
    incident_id: string;
    description: string;
    similarity_score: number;
    analysis_run: AnalysisRun;
  }>;
}

function getErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  if (
    typeof error === "object" &&
    error !== null &&
    "response" in error &&
    typeof (error as { response?: { data?: { detail?: string } } }).response?.data?.detail === "string"
  ) {
    return (error as { response?: { data?: { detail?: string } } }).response!.data!.detail!;
  }
  return fallback;
}

export default function OperatorIncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [operatorComment, setOperatorComment] = useState("");
  const [selectedProcedureVersionId, setSelectedProcedureVersionId] = useState("");
  const [selectedRelatedRunId, setSelectedRelatedRunId] = useState("");
  const [analysisPreview, setAnalysisPreview] = useState<IncidentAnalysisPreview | null>(null);
  const [error, setError] = useState("");

  const { data: incident, isLoading } = useQuery<IncidentItem>({
    queryKey: ["operator-incident", id],
    queryFn: () => api.get(`/incidents/${id}`).then((r) => r.data),
    enabled: Boolean(id),
  });

  useEffect(() => {
    if (!incident) {
      return;
    }
    setOperatorComment(incident.operator_comment ?? "");
    setSelectedProcedureVersionId(incident.operator_selected_procedure_version_id ?? "");
    setSelectedRelatedRunId(incident.operator_selected_related_run_id ?? "");
  }, [incident]);

  const analyzeMutation = useMutation({
    mutationFn: () => api.post(`/incidents/${id}/analyze-procedures`).then((r) => r.data as IncidentAnalysisPreview),
    onSuccess: (data) => {
      setAnalysisPreview(data);
      setError("");
    },
    onError: (mutationError) => {
      setError(getErrorMessage(mutationError, "No se pudo consultar ayuda contextual para esta incidencia."));
    },
  });

  const operatorResolutionMutation = useMutation({
    mutationFn: (status: Extract<IncidentStatus, "resolved_by_operator" | "escalated">) =>
      api
        .patch(`/incidents/${id}`, {
          status,
          operator_comment: operatorComment.trim(),
          operator_selected_procedure_version_id: selectedProcedureVersionId || null,
          operator_selected_related_run_id: selectedRelatedRunId || null,
        })
        .then((r) => r.data as IncidentItem),
    onSuccess: async (updatedIncident) => {
      await queryClient.invalidateQueries({ queryKey: ["operator-incidents"] });
      await queryClient.invalidateQueries({ queryKey: ["incident", id] });
      queryClient.setQueryData(["operator-incident", id], updatedIncident);
      setError("");
    },
    onError: (mutationError) => {
      setError(getErrorMessage(mutationError, "No se pudo guardar la resolución operativa."));
    },
  });
  const selectedProcedureMatch = useMemo(
    () =>
      analysisPreview?.procedure_matches.find((match) => match.procedure_version_id === selectedProcedureVersionId) ?? null,
    [analysisPreview, selectedProcedureVersionId],
  );
  const selectedSimilarAnalysis = useMemo(
    () => analysisPreview?.similar_analyses.find((item) => item.analysis_run.id === selectedRelatedRunId) ?? null,
    [analysisPreview, selectedRelatedRunId],
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  if (!incident) {
    return (
      <div className="mx-auto max-w-3xl rounded-2xl border border-amber-200 bg-amber-50 p-6 text-amber-900">
        <h1 className="text-lg font-semibold">Incidencia no encontrada</h1>
        <Link to="/incidents" className="mt-4 inline-flex text-sm font-medium underline">
          Volver a incidencias
        </Link>
      </div>
    );
  }

  const severity = incidentSeverityMeta[incident.severity] ?? {
    label: incident.severity,
    className: "bg-gray-100 text-gray-700",
  };
  const incidentStatus = incidentStatusMeta[incident.status] ?? {
    label: incident.status,
    className: "bg-gray-100 text-gray-700",
  };
  const isClosed = incident.status === "closed";

  function toggleProcedureReference(procedureVersionId: string) {
    setSelectedProcedureVersionId((current) => (current === procedureVersionId ? "" : procedureVersionId));
  }

  function toggleSimilarAnalysis(runId: string) {
    setSelectedRelatedRunId((current) => (current === runId ? "" : runId));
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <Link
        to="/incidents"
        className="inline-flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-700"
      >
        <ArrowLeft className="h-4 w-4" />
        Volver a incidencias
      </Link>

      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${severity.className}`}>
            {severity.label}
          </span>
          <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${incidentStatus.className}`}>
            {incidentStatus.label}
          </span>
          {incident.role_name && (
            <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700">
              {incident.role_name}
            </span>
          )}
        </div>

        <h1 className="mt-4 text-2xl font-bold text-gray-900">Detalle de incidencia</h1>
        <p className="mt-2 text-sm text-gray-500">
          Registrada el {new Date(incident.created_at).toLocaleString("es-AR")}
          {incident.location ? ` · ${incident.location}` : ""}
        </p>

        <div className="mt-6 rounded-xl bg-gray-50 p-5">
          <p className="whitespace-pre-wrap text-sm leading-6 text-gray-700">{incident.description}</p>
        </div>
      </div>

      {(incident.operator_comment || incident.operator_resolution_at) && (
        <section className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald-600" />
            <div className="min-w-0">
              <h2 className="text-base font-semibold text-emerald-900">Última resolución operativa</h2>
              <p className="mt-1 text-sm text-emerald-800">
                {incident.operator_comment || "No hay comentario registrado."}
              </p>
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-emerald-900/80">
                {incident.operator_resolution_at && (
                  <span className="rounded-full bg-white/70 px-2.5 py-1">
                    {new Date(incident.operator_resolution_at).toLocaleString("es-AR")}
                  </span>
                )}
                {incident.operator_resolution_by_name && (
                  <span className="rounded-full bg-white/70 px-2.5 py-1">
                    Registrada por {incident.operator_resolution_by_name}
                  </span>
                )}
                {incident.operator_selected_procedure_title && (
                  <span className="rounded-full bg-white/70 px-2.5 py-1">
                    Procedimiento: {incident.operator_selected_procedure_title}
                    {incident.operator_selected_procedure_version_number != null
                      ? ` · v${incident.operator_selected_procedure_version_number}`
                      : ""}
                  </span>
                )}
                {incident.operator_selected_related_incident_description && (
                  <span className="rounded-full bg-white/70 px-2.5 py-1">
                    Precedente: {incident.operator_selected_related_incident_description}
                  </span>
                )}
              </div>
            </div>
          </div>
        </section>
      )}

      <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Ayuda para resolver</h2>
            <p className="mt-1 text-sm text-gray-500">
              Consulta procedimientos relacionados y análisis previos antes de decidir cómo tratar la incidencia.
            </p>
          </div>
          <button
            type="button"
            onClick={() => analyzeMutation.mutate()}
            disabled={isClosed || analyzeMutation.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            {analyzeMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Buscar ayuda
          </button>
        </div>

        {isClosed && (
          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            La incidencia está cerrada. Puedes revisar el contexto guardado, pero no cambiar la resolución operativa.
          </div>
        )}

        {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

        {(analyzeMutation.isPending || analysisPreview) && (
          <div className="mt-6 space-y-6 border-t border-gray-100 pt-6">
            <div>
              <h3 className="text-sm font-semibold text-gray-900">Procedimientos relacionados</h3>
              <div className="mt-3 space-y-3">
                {analyzeMutation.isPending ? (
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Buscando coincidencias semánticas...
                  </div>
                ) : analysisPreview?.procedure_matches.length ? (
                  analysisPreview.procedure_matches.map((match) => {
                    const isSelected = selectedProcedureVersionId === match.procedure_version_id;
                    return (
                      <div key={match.procedure_version_id} className="rounded-xl border border-gray-200 bg-gray-50 p-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium text-gray-900">
                              {match.procedure_code} · {match.procedure_title} · v{match.version_number}
                            </p>
                            <p className="mt-1 text-xs text-gray-500">{getSemanticScoreLabel(match.score)}</p>
                            <p className="mt-1 text-[11px] text-gray-400">{getSemanticScoreDetail(match.score)}</p>
                            {match.step_title && (
                              <p className="mt-2 text-xs font-medium text-gray-500">
                                Paso {match.step_index}: {match.step_title}
                              </p>
                            )}
                            <p className="mt-2 text-sm text-gray-700">{match.snippet}</p>
                            {match.reference_segment_range && (
                              <p className="mt-2 text-xs text-gray-500">
                                Referencia fuente: {match.reference_segment_range}
                              </p>
                            )}
                            {match.training_title && (
                              <p className="mt-2 text-xs text-gray-500">Training derivado: {match.training_title}</p>
                            )}
                          </div>
                          <div className="flex flex-wrap gap-2">
                            <button
                              type="button"
                              onClick={() => toggleProcedureReference(match.procedure_version_id)}
                              className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                                isSelected
                                  ? "bg-emerald-100 text-emerald-800"
                                  : "border border-gray-300 text-gray-700 hover:bg-white"
                              }`}
                            >
                              {isSelected ? "Referencia seleccionada" : "Usar como referencia"}
                            </button>
                            <Link
                              to={`/procedures/${match.procedure_id}`}
                              className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-white"
                            >
                              Ver procedimiento
                            </Link>
                          </div>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="rounded-xl border border-dashed border-gray-200 px-4 py-5 text-sm text-gray-500">
                    No se encontraron procedimientos suficientemente relacionados.
                  </div>
                )}
              </div>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-gray-900">Análisis previos similares</h3>
              <div className="mt-3 space-y-3">
                {analysisPreview?.similar_analyses.length ? (
                  analysisPreview.similar_analyses.map((related) => {
                    const isSelected = selectedRelatedRunId === related.analysis_run.id;
                    return (
                      <div key={related.analysis_run.id} className="rounded-xl border border-gray-200 bg-gray-50 p-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium text-gray-900">{related.description}</p>
                            <p className="mt-1 text-xs text-gray-500">{getSemanticScoreLabel(related.similarity_score)}</p>
                            <p className="mt-1 text-[11px] text-gray-400">
                              {getSemanticScoreDetail(related.similarity_score)}
                            </p>
                            {related.analysis_run.analysis_summary && (
                              <p className="mt-2 text-sm text-gray-700">{related.analysis_run.analysis_summary}</p>
                            )}
                            {related.analysis_run.resolution_summary && (
                              <p className="mt-1 text-xs text-gray-500">
                                Resolución previa: {related.analysis_run.resolution_summary}
                              </p>
                            )}
                            {!!related.analysis_run.findings.length && (
                              <div className="mt-2 space-y-1">
                                {related.analysis_run.findings.slice(0, 2).map((finding) => (
                                  <p key={finding.id} className="text-xs text-gray-500">
                                    {finding.procedure_title
                                      ? `${finding.procedure_title}${finding.version_number != null ? ` · v${finding.version_number}` : ""}`
                                      : "Hallazgo sin procedimiento asociado"}
                                    {finding.recommended_action ? ` · ${finding.recommended_action}` : ""}
                                  </p>
                                ))}
                              </div>
                            )}
                          </div>
                          <button
                            type="button"
                            onClick={() => toggleSimilarAnalysis(related.analysis_run.id)}
                            className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                              isSelected
                                ? "bg-emerald-100 text-emerald-800"
                                : "border border-gray-300 text-gray-700 hover:bg-white"
                            }`}
                          >
                            {isSelected ? "Precedente seleccionado" : "Usar como referencia"}
                          </button>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="rounded-xl border border-dashed border-gray-200 px-4 py-5 text-sm text-gray-500">
                    No se encontraron análisis previos similares.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-3">
          <FileSearch className="mt-0.5 h-5 w-5 text-indigo-500" />
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-semibold text-gray-900">Resolución operativa</h2>
            <p className="mt-1 text-sm text-gray-500">
              Deja un comentario obligatorio para que el admin tenga contexto antes de cargar el análisis manual.
            </p>
          </div>
        </div>

        <div className="mt-5 rounded-xl bg-gray-50 p-4 text-sm text-gray-700">
          <p className="font-medium text-gray-900">Referencias elegidas</p>
          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            {(selectedProcedureMatch || incident.operator_selected_procedure_title) && (
              <span className="rounded-full bg-white px-2.5 py-1 text-gray-700 ring-1 ring-gray-200">
                Procedimiento:{" "}
                {selectedProcedureMatch
                  ? `${selectedProcedureMatch.procedure_title} · v${selectedProcedureMatch.version_number}`
                  : `${incident.operator_selected_procedure_title}${
                      incident.operator_selected_procedure_version_number != null
                        ? ` · v${incident.operator_selected_procedure_version_number}`
                        : ""
                    }`}
              </span>
            )}
            {(selectedSimilarAnalysis || incident.operator_selected_related_incident_description) && (
              <span className="rounded-full bg-white px-2.5 py-1 text-gray-700 ring-1 ring-gray-200">
                Precedente:{" "}
                {selectedSimilarAnalysis
                  ? selectedSimilarAnalysis.description
                  : incident.operator_selected_related_incident_description}
              </span>
            )}
            {!selectedProcedureVersionId &&
              !selectedRelatedRunId &&
              !incident.operator_selected_procedure_title &&
              !incident.operator_selected_related_incident_description && (
                <span className="text-gray-500">Todavía no seleccionaste una referencia.</span>
              )}
          </div>
        </div>

        <textarea
          rows={4}
          value={operatorComment}
          onChange={(event) => setOperatorComment(event.target.value)}
          disabled={isClosed}
          className="mt-5 w-full rounded-xl border border-gray-300 px-4 py-3 text-sm text-gray-800 disabled:bg-gray-50"
          placeholder="Describe si la ayuda encontrada resolvió el caso o por qué se necesita tratamiento adicional."
        />

        <div className="mt-5 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => operatorResolutionMutation.mutate("resolved_by_operator")}
            disabled={isClosed || operatorResolutionMutation.isPending || !operatorComment.trim()}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
          >
            {operatorResolutionMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            {incident.status === "resolved_by_operator" ? "Actualizar resolución" : "Marcar como resuelta"}
          </button>
          <button
            type="button"
            onClick={() => operatorResolutionMutation.mutate("escalated")}
            disabled={isClosed || operatorResolutionMutation.isPending || !operatorComment.trim()}
            className="inline-flex items-center gap-2 rounded-lg bg-amber-500 px-4 py-2.5 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-60"
          >
            {operatorResolutionMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            {incident.status === "escalated" ? "Actualizar escalamiento" : "Marcar como no resuelta / escalar"}
          </button>
        </div>
      </section>
    </div>
  );
}
