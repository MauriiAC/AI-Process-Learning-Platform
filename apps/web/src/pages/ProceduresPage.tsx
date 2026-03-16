import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookCopy, FilePlus2, Loader2, Network, Plus } from "lucide-react";
import api from "@/services/api";

interface RoleOption {
  id: string;
  name: string;
}

interface ProcedureVersion {
  id: string;
  version_number: number;
  status: string;
  change_summary?: string | null;
}

interface Procedure {
  id: string;
  code: string;
  title: string;
  description?: string | null;
  owner_role_name?: string | null;
  latest_version?: ProcedureVersion | null;
}

export default function ProceduresPage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    code: "",
    title: "",
    description: "",
    owner_role_id: "",
  });

  const { data: procedures, isLoading } = useQuery<Procedure[]>({
    queryKey: ["procedures"],
    queryFn: () => api.get("/procedures").then((r) => r.data),
  });

  const { data: roles } = useQuery<RoleOption[]>({
    queryKey: ["roles"],
    queryFn: () => api.get("/roles").then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api.post("/procedures", {
        ...form,
        owner_role_id: form.owner_role_id || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["procedures"] });
      setShowForm(false);
      setForm({ code: "", title: "", description: "", owner_role_id: "" });
    },
  });

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Procedimientos</h1>
          <p className="mt-1 text-sm text-gray-500">
            Biblioteca versionada que actúa como fuente de verdad operativa.
          </p>
        </div>
        <button
          onClick={() => setShowForm((value) => !value)}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4" />
          Nuevo procedimiento
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            createMutation.mutate();
          }}
          className="mb-6 grid gap-4 rounded-2xl border border-gray-200 bg-white p-6 md:grid-cols-2"
        >
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-gray-700">Código</span>
            <input
              required
              value={form.code}
              onChange={(event) => setForm((current) => ({ ...current, code: event.target.value }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
              placeholder="PROC-EXAMPLE"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-gray-700">Título</span>
            <input
              required
              value={form.title}
              onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
            />
          </label>
          <label className="block md:col-span-2">
            <span className="mb-1 block text-sm font-medium text-gray-700">Descripción</span>
            <textarea
              rows={3}
              value={form.description}
              onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-gray-700">Rol owner</span>
            <select
              value={form.owner_role_id}
              onChange={(event) =>
                setForm((current) => ({ ...current, owner_role_id: event.target.value }))
              }
              className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
            >
              <option value="">Sin asignar</option>
              {roles?.map((role) => (
                <option key={role.id} value={role.id}>
                  {role.name}
                </option>
              ))}
            </select>
          </label>
          <div className="flex items-end justify-end gap-3">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              {createMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Guardar
            </button>
          </div>
        </form>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
        </div>
      ) : !procedures?.length ? (
        <div className="rounded-2xl border-2 border-dashed border-gray-200 py-16 text-center">
          <BookCopy className="mx-auto h-10 w-10 text-gray-300" />
          <p className="mt-3 text-sm font-medium text-gray-600">Todavía no hay procedimientos</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {procedures.map((procedure) => (
            <Link
              key={procedure.id}
              to={`/procedures/${procedure.id}`}
              className="rounded-2xl border border-gray-200 bg-white p-5 transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
                    {procedure.code}
                  </p>
                  <h2 className="mt-1 text-lg font-semibold text-gray-900">{procedure.title}</h2>
                </div>
                <Network className="h-5 w-5 text-gray-300" />
              </div>
              <p className="mt-3 text-sm text-gray-600">
                {procedure.description || "Sin descripción cargada."}
              </p>
              <div className="mt-4 flex flex-wrap gap-2 text-xs text-gray-500">
                <span className="rounded-full bg-gray-100 px-2.5 py-1">
                  Owner: {procedure.owner_role_name || "Sin rol"}
                </span>
                <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-indigo-700">
                  v{procedure.latest_version?.version_number ?? 0}
                </span>
                <span className="rounded-full bg-gray-100 px-2.5 py-1">
                  {procedure.latest_version?.status ?? "Sin versión"}
                </span>
              </div>
              {procedure.latest_version?.change_summary && (
                <div className="mt-4 flex items-start gap-2 rounded-xl bg-gray-50 px-3 py-2 text-xs text-gray-600">
                  <FilePlus2 className="mt-0.5 h-3.5 w-3.5 text-gray-400" />
                  <span>{procedure.latest_version.change_summary}</span>
                </div>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
