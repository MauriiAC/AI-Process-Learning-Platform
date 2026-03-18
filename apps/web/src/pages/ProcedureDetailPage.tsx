import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CalendarClock,
  FileStack,
  FileVideo,
  Link2,
  Loader2,
  Sparkles,
  Trash2,
  Unlink,
  Upload,
} from "lucide-react";
import api from "@/services/api";

interface ProcedureVersion {
  id: string;
  version_number: number;
  status: string;
  change_summary?: string | null;
  change_reason?: string | null;
  effective_from?: string | null;
  content_text?: string | null;
  source_asset_type?: string | null;
  source_storage_key?: string | null;
  source_mime?: string | null;
  source_size?: number | null;
  source_processing_status: string;
  source_processing_error?: string | null;
  source_processed_at?: string | null;
  source_result?: {
    structure: {
      title: string;
      objectives: string[];
      steps: { title: string; description: string; evidence?: { segment_range?: string } }[];
      critical_points: { text: string; why: string; evidence?: { segment_range?: string } }[];
    };
    transcript_raw: string;
  } | null;
  derived_training?: {
    id: string;
    title: string;
    status: string;
  } | null;
}

interface ProcedureDetail {
  id: string;
  code: string;
  title: string;
  description?: string | null;
  owner_role_name?: string | null;
  versions: ProcedureVersion[];
  roles: Array<{ id: string; role_id: string; role_code: string; role_name: string; is_required: boolean }>;
}

interface RoleOption {
  id: string;
  code: string;
  name: string;
}

const ACTIVE_SOURCE_PROCESSING_STATUSES = [
  "UPLOADED",
  "TRANSCRIBING",
  "CHUNKING",
  "INDEXING",
  "EXTRACTING",
] as const;

const SOURCE_PROCESSING_STATUS_LABELS: Record<string, string> = {
  pending: "Pendiente",
  UPLOADED: "Video subido",
  TRANSCRIBING: "Transcribiendo audio",
  CHUNKING: "Capturando frames",
  INDEXING: "Indexando segmentos",
  EXTRACTING: "Extrayendo conocimiento",
  READY: "Listo",
  FAILED: "Error",
};

function getErrorMessage(error: unknown, fallback: string) {
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

function getSourceProcessingLabel(status: string) {
  return SOURCE_PROCESSING_STATUS_LABELS[status] ?? status;
}

export default function ProcedureDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [versionForm, setVersionForm] = useState({
    change_summary: "",
    change_reason: "",
    effective_from: "",
    content_text: "",
  });
  const [roleId, setRoleId] = useState("");
  const [versionFiles, setVersionFiles] = useState<Record<string, File | null>>({});

  const { data: procedure, isLoading } = useQuery<ProcedureDetail>({
    queryKey: ["procedure", id],
    queryFn: () => api.get(`/procedures/${id}`).then((r) => r.data),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      const data = query.state.data as ProcedureDetail | undefined;
      const hasActiveProcessing = data?.versions?.some((version) =>
        ACTIVE_SOURCE_PROCESSING_STATUSES.includes(
          version.source_processing_status as (typeof ACTIVE_SOURCE_PROCESSING_STATUSES)[number],
        ),
      );
      return hasActiveProcessing ? 3000 : false;
    },
  });

  const { data: roles } = useQuery<RoleOption[]>({
    queryKey: ["roles"],
    queryFn: () => api.get("/roles").then((r) => r.data),
  });

  const createVersionMutation = useMutation({
    mutationFn: () =>
      api.post(`/procedures/${id}/versions`, {
        ...versionForm,
        effective_from: versionForm.effective_from || null,
        status: "draft",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["procedure", id] });
      setVersionForm({ change_summary: "", change_reason: "", effective_from: "", content_text: "" });
    },
  });

  const linkRoleMutation = useMutation({
    mutationFn: () =>
      api.post("/roles/procedure-links", {
        role_id: roleId,
        procedure_id: id,
        is_required: true,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["procedure", id] });
      queryClient.invalidateQueries({ queryKey: ["roles"] });
      setRoleId("");
    },
  });

  const unlinkRoleMutation = useMutation({
    mutationFn: (linkId: string) => api.delete(`/roles/procedure-links/${linkId}`).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["procedure", id] });
      queryClient.invalidateQueries({ queryKey: ["roles"] });
    },
  });

  const uploadSourceMutation = useMutation({
    mutationFn: async ({ versionId, file }: { versionId: string; file: File }) => {
      const { data: presign } = await api.post("/uploads/presign", {
        filename: file.name,
        content_type: file.type,
      });
      await fetch(presign.presigned_url, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": file.type },
      });
      await api.post(`/procedures/versions/${versionId}/source-asset`, {
        storage_key: presign.storage_key,
        mime: file.type,
        size: file.size,
        asset_type: "video",
      });
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["procedure", id] });
      setVersionFiles((current) => ({ ...current, [variables.versionId]: null }));
    },
  });

  const generateTrainingMutation = useMutation({
    mutationFn: (versionId: string) =>
      api.post(`/procedures/versions/${versionId}/generate-training`).then((r) => r.data),
    onSuccess: (data: { training_id: string; job_id: string }) => {
      queryClient.invalidateQueries({ queryKey: ["procedure", id] });
      queryClient.invalidateQueries({ queryKey: ["trainings"] });
      navigate(`/trainings/${data.training_id}`, {
        state: { jobId: data.job_id, activeJobAction: "generate" },
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/procedures/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["procedures"] });
      queryClient.invalidateQueries({ queryKey: ["roles"] });
      queryClient.invalidateQueries({ queryKey: ["trainings"] });
      navigate("/procedures");
    },
  });

  if (isLoading || !procedure) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  const availableRoles =
    roles?.filter((role) => !procedure.roles.some((linked) => linked.role_id === role.id)) ?? [];

  function handleDelete() {
    if (!procedure || deleteMutation.isPending) return;
    const confirmed = window.confirm(
      `¿Seguro que quieres eliminar el procedimiento "${procedure.title}"? También se eliminarán sus versiones y trainings derivados.`
    );
    if (!confirmed) return;
    deleteMutation.mutate();
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <Link
            to="/procedures"
            className="inline-flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-700"
          >
            <ArrowLeft className="h-4 w-4" />
            Volver a procedimientos
          </Link>
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
            className="inline-flex items-center gap-2 rounded-lg border border-red-200 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {deleteMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4" />
            )}
            Eliminar procedimiento
          </button>
        </div>
        <div className="rounded-3xl border border-gray-200 bg-white p-6">
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">{procedure.code}</p>
          <h1 className="mt-1 text-2xl font-bold text-gray-900">{procedure.title}</h1>
          <p className="mt-2 text-sm text-gray-600">{procedure.description || "Sin descripción."}</p>
          <div className="mt-4 flex flex-wrap gap-2 text-xs text-gray-500">
            <span className="rounded-full bg-gray-100 px-2.5 py-1">
              Owner: {procedure.owner_role_name || "Sin rol"}
            </span>
            <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-indigo-700">
              {procedure.versions.length} versiones
            </span>
            <span className="rounded-full bg-green-50 px-2.5 py-1 text-green-700">
              {procedure.versions.filter((version) => version.derived_training).length} trainings derivados
            </span>
          </div>
        </div>
        {deleteMutation.isError && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {getErrorMessage(deleteMutation.error, "No se pudo eliminar el procedimiento.")}
          </div>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-6">
          <section className="rounded-2xl border border-gray-200 bg-white p-5">
            <div className="mb-4 flex items-center gap-2">
              <FileStack className="h-5 w-5 text-indigo-600" />
              <h2 className="text-lg font-semibold text-gray-900">Versiones</h2>
            </div>
            <div className="space-y-3">
              {procedure.versions.map((version) => (
                <div key={version.id} className="rounded-xl border border-gray-200 p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold text-gray-900">v{version.version_number}</p>
                      <p className="text-xs text-gray-500">{version.status}</p>
                    </div>
                    {version.effective_from && (
                      <span className="inline-flex items-center gap-1 text-xs text-gray-500">
                        <CalendarClock className="h-3.5 w-3.5" />
                        {new Date(version.effective_from).toLocaleDateString("es-AR")}
                      </span>
                    )}
                  </div>
                  {version.change_summary && (
                    <p className="mt-3 text-sm text-gray-700">{version.change_summary}</p>
                  )}
                  {version.content_text && (
                    <p className="mt-2 text-xs text-gray-500">{version.content_text}</p>
                  )}
                  <div className="mt-4 rounded-lg border border-gray-100 bg-gray-50 p-3">
                    <div className="flex items-center gap-2">
                      <FileVideo className="h-4 w-4 text-indigo-600" />
                      <p className="text-sm font-medium text-gray-900">Video fuente</p>
                    </div>
                    {version.source_storage_key ? (
                      <p className="mt-2 text-xs text-gray-600">
                        {version.source_storage_key.split("/").pop()}
                        {version.source_size
                          ? ` · ${(version.source_size / 1024 / 1024).toFixed(1)} MB`
                          : ""}
                      </p>
                    ) : (
                      <p className="mt-2 text-xs text-amber-700">Todavía no hay video cargado.</p>
                    )}
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100">
                        <Upload className="h-4 w-4" />
                        {version.source_storage_key ? "Reemplazar video" : "Subir video"}
                        <input
                          type="file"
                          accept="video/*"
                          className="hidden"
                          onChange={(event) =>
                            setVersionFiles((current) => ({
                              ...current,
                              [version.id]: event.target.files?.[0] ?? null,
                            }))
                          }
                        />
                      </label>
                      {versionFiles[version.id] && (
                        <button
                          type="button"
                          onClick={() =>
                            uploadSourceMutation.mutate({
                              versionId: version.id,
                              file: versionFiles[version.id] as File,
                            })
                          }
                          disabled={uploadSourceMutation.isPending}
                          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
                        >
                          {uploadSourceMutation.isPending ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Upload className="h-4 w-4" />
                          )}
                          Confirmar upload
                        </button>
                      )}
                    </div>
                    {versionFiles[version.id] && (
                      <p className="mt-2 text-xs text-gray-500">{versionFiles[version.id]?.name}</p>
                    )}
                    <div className="mt-3 rounded-md bg-white/80 px-3 py-2 text-xs text-gray-600">
                      <span className="font-medium text-gray-800">Source processing:</span>{" "}
                      {getSourceProcessingLabel(version.source_processing_status)}
                      {version.source_processed_at && (
                        <span className="text-gray-400">
                          {" "}
                          · {new Date(version.source_processed_at).toLocaleString("es-AR")}
                        </span>
                      )}
                      {version.source_processing_error && (
                        <p className="mt-1 text-red-600">{version.source_processing_error}</p>
                      )}
                    </div>
                  </div>
                  <VersionSourceResultPanel version={version} />
                  <div className="mt-4 rounded-lg border border-indigo-100 bg-indigo-50 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-indigo-900">Training derivado</p>
                        <p className="mt-1 text-xs text-indigo-700">
                          {version.derived_training
                            ? `${version.derived_training.title} · ${version.derived_training.status}`
                            : "Aún no se generó un training para esta versión."}
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        {version.derived_training && (
                          <Link
                            to={`/trainings/${version.derived_training.id}`}
                            className="rounded-lg border border-indigo-200 px-3 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-100"
                          >
                            Ver training
                          </Link>
                        )}
                        <button
                          type="button"
                          onClick={() => generateTrainingMutation.mutate(version.id)}
                          disabled={
                            !version.source_storage_key ||
                            version.source_processing_status !== "READY" ||
                            generateTrainingMutation.isPending
                          }
                          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
                        >
                          {generateTrainingMutation.isPending ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Sparkles className="h-4 w-4" />
                          )}
                          {version.derived_training ? "Regenerar" : "Generar training"}
                        </button>
                      </div>
                    </div>
                    {version.source_processing_status !== "READY" && version.source_storage_key && (
                      <p className="mt-2 text-xs text-indigo-700">
                        El training se habilita cuando el source processing queda en `READY`.
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-2xl border border-gray-200 bg-white p-5">
            <div className="mb-4 flex items-center gap-2">
              <Link2 className="h-5 w-5 text-indigo-600" />
              <h2 className="text-lg font-semibold text-gray-900">Vínculos operativos</h2>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <p className="mb-2 text-sm font-medium text-gray-700">Roles vinculados</p>
                <div className="space-y-2">
                  {!procedure.roles.length ? (
                    <p className="rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-500">
                      Este procedimiento todavía no tiene roles vinculados.
                    </p>
                  ) : (
                    procedure.roles.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-700"
                      >
                        <div>
                          <p className="font-medium text-gray-800">{item.role_name}</p>
                          <p className="text-xs text-gray-500">
                            {item.role_code} · {item.is_required ? "Requerido" : "Opcional"}
                          </p>
                        </div>
                        <button
                          type="button"
                          disabled={unlinkRoleMutation.isPending}
                          onClick={() => unlinkRoleMutation.mutate(item.id)}
                          className="inline-flex items-center gap-1 rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-60"
                        >
                          <Unlink className="h-3 w-3" />
                          Quitar
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
              <div>
                <p className="mb-2 text-sm font-medium text-gray-700">Trainings derivados</p>
                <div className="space-y-2">
                  {procedure.versions
                    .filter((version) => version.derived_training)
                    .map((version) => (
                      <div key={version.id} className="rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-700">
                        {version.derived_training?.title} · v{version.version_number}
                      </div>
                    ))}
                </div>
              </div>
            </div>
          </section>
        </div>

        <div className="space-y-6">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              createVersionMutation.mutate();
            }}
            className="rounded-2xl border border-gray-200 bg-white p-5"
          >
            <h2 className="text-lg font-semibold text-gray-900">Nueva versión</h2>
            <div className="mt-4 space-y-3">
              <input
                required
                placeholder="Resumen del cambio"
                value={versionForm.change_summary}
                onChange={(event) =>
                  setVersionForm((current) => ({ ...current, change_summary: event.target.value }))
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
              />
              <textarea
                rows={2}
                placeholder="Razón del cambio"
                value={versionForm.change_reason}
                onChange={(event) =>
                  setVersionForm((current) => ({ ...current, change_reason: event.target.value }))
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
              />
              <textarea
                required
                rows={4}
                placeholder="Contenido textual versionado"
                value={versionForm.content_text}
                onChange={(event) =>
                  setVersionForm((current) => ({ ...current, content_text: event.target.value }))
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
              />
              <input
                type="date"
                value={versionForm.effective_from}
                onChange={(event) =>
                  setVersionForm((current) => ({ ...current, effective_from: event.target.value }))
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
              />
            </div>
            <button
              type="submit"
              disabled={createVersionMutation.isPending}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              {createVersionMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Crear versión
            </button>
          </form>

          <div className="rounded-2xl border border-gray-200 bg-white p-5">
            <h2 className="text-lg font-semibold text-gray-900">Vincular rol</h2>
            <div className="mt-4">
              <select
                value={roleId}
                onChange={(event) => setRoleId(event.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
              >
                <option value="">Seleccionar rol</option>
                {availableRoles.map((role) => (
                  <option key={role.id} value={role.id}>
                    {role.code} · {role.name}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              onClick={() => linkRoleMutation.mutate()}
              disabled={!roleId || linkRoleMutation.isPending}
              className="mt-4 rounded-lg border border-indigo-200 px-4 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-50 disabled:opacity-60"
            >
              Vincular rol
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function VersionSourceResultPanel({ version }: { version: ProcedureVersion }) {
  const isProcessing = ACTIVE_SOURCE_PROCESSING_STATUSES.includes(
    version.source_processing_status as (typeof ACTIVE_SOURCE_PROCESSING_STATUSES)[number],
  );

  return (
    <div className="mt-4 rounded-lg border border-emerald-100 bg-emerald-50/60 p-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-emerald-900">Resultado del procesamiento</p>
          <p className="mt-1 text-xs text-emerald-700">
            Estructura extraída y transcripción del video fuente.
          </p>
        </div>
        <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-medium text-emerald-800">
          {getSourceProcessingLabel(version.source_processing_status)}
        </span>
      </div>

      {!version.source_storage_key ? (
        <p className="mt-3 text-xs text-amber-700">
          Sube un video fuente para generar el resultado del procesamiento.
        </p>
      ) : version.source_processing_status === "FAILED" ? (
        <div className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {version.source_processing_error || "No se pudo procesar esta versión."}
        </div>
      ) : isProcessing ? (
        <p className="mt-3 text-xs text-emerald-800">
          Estamos procesando el video de esta versión. El resultado aparecerá acá cuando termine.
        </p>
      ) : version.source_processing_status === "READY" && version.source_result ? (
        <div className="mt-4 space-y-5">
          <div className="space-y-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
                Estructura extraída
              </p>
              <h3 className="mt-1 text-sm font-semibold text-gray-900">
                {version.source_result.structure.title}
              </h3>
            </div>

            {version.source_result.structure.objectives.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-semibold text-gray-700">Objetivos</h4>
                <ul className="list-inside list-disc space-y-1 text-sm text-gray-600">
                  {version.source_result.structure.objectives.map((objective, index) => (
                    <li key={`${version.id}-objective-${index}`}>{objective}</li>
                  ))}
                </ul>
              </div>
            )}

            {version.source_result.structure.steps.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-semibold text-gray-700">Pasos</h4>
                <ol className="space-y-3">
                  {version.source_result.structure.steps.map((step, index) => (
                    <li
                      key={`${version.id}-step-${index}`}
                      className="rounded-lg border border-emerald-100 bg-white/80 p-3"
                    >
                      <p className="text-sm font-medium text-gray-800">
                        {index + 1}. {step.title}
                      </p>
                      <p className="mt-1 text-sm text-gray-600">{step.description}</p>
                      <SegmentEvidenceBadge segmentRange={step.evidence?.segment_range} />
                    </li>
                  ))}
                </ol>
              </div>
            )}

            {version.source_result.structure.critical_points.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-semibold text-gray-700">Puntos críticos</h4>
                <ul className="space-y-2">
                  {version.source_result.structure.critical_points.map((point, index) => (
                    <li
                      key={`${version.id}-critical-point-${index}`}
                      className="rounded-lg border border-amber-100 bg-amber-50 p-3"
                    >
                      <p className="text-sm font-medium text-amber-900">{point.text}</p>
                      <p className="mt-1 text-sm text-amber-800">{point.why}</p>
                      <SegmentEvidenceBadge segmentRange={point.evidence?.segment_range} />
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <details className="rounded-lg border border-gray-200 bg-white">
            <summary className="cursor-pointer list-none px-3 py-2 text-sm font-medium text-gray-800">
              Ver transcripción completa
            </summary>
            <div className="border-t border-gray-200 px-3 py-3">
              <pre className="max-h-72 overflow-auto whitespace-pre-wrap text-xs leading-6 text-gray-600">
                {version.source_result.transcript_raw}
              </pre>
            </div>
          </details>
        </div>
      ) : (
        <p className="mt-3 text-xs text-gray-600">
          El procesamiento terminó, pero esta versión todavía no tiene un resultado visible.
        </p>
      )}
    </div>
  );
}

function SegmentEvidenceBadge({ segmentRange }: { segmentRange?: string }) {
  if (!segmentRange) return null;

  return (
    <div className="mt-2 inline-flex rounded-full bg-emerald-100 px-2.5 py-1 text-[11px] font-medium text-emerald-800">
      Evidencia: {segmentRange}
    </div>
  );
}
