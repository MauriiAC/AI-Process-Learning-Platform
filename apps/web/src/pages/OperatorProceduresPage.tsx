import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, BookOpen, Loader2 } from "lucide-react";
import { Link } from "react-router-dom";

import { getStoredUser } from "@/lib/auth";
import { complianceStatusMeta, type ComplianceItem } from "@/lib/operatorData";
import api from "@/services/api";

export default function OperatorProceduresPage() {
  const user = getStoredUser();

  const { data: compliance = [], isLoading } = useQuery<ComplianceItem[]>({
    queryKey: ["operator-procedures", user?.id],
    queryFn: () => api.get("/compliance", { params: { user_id: user?.id } }).then((r) => r.data),
    enabled: Boolean(user?.id),
  });

  const procedures = useMemo(() => {
    const byProcedure = new Map<string, ComplianceItem>();
    compliance.forEach((item) => {
      if (!byProcedure.has(item.procedure_id)) {
        byProcedure.set(item.procedure_id, item);
      }
    });
    return Array.from(byProcedure.values());
  }, [compliance]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Procedimientos</h1>
        <p className="mt-1 text-sm text-gray-500">
          Procedimientos visibles para tus roles activos, con acceso directo al training relacionado.
        </p>
      </div>

      {!procedures.length ? (
        <div className="rounded-2xl border-2 border-dashed border-gray-200 py-16 text-center">
          <BookOpen className="mx-auto h-10 w-10 text-gray-300" />
          <p className="mt-3 text-sm font-medium text-gray-600">
            No hay procedimientos asociados a este usuario.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {procedures.map((item) => {
            const status = complianceStatusMeta[item.status] ?? {
              label: item.status,
              className: "bg-gray-100 text-gray-700",
            };

            return (
              <Link
                key={item.id}
                to={`/procedures/${item.procedure_id}`}
                className="rounded-2xl border border-gray-200 bg-white p-5 transition hover:-translate-y-0.5 hover:shadow-md"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
                      {item.role_name || "Rol activo"}
                    </p>
                    <h2 className="mt-1 text-lg font-semibold text-gray-900">{item.procedure_title}</h2>
                  </div>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${status.className}`}>
                    {status.label}
                  </span>
                </div>

                <div className="mt-4 flex flex-wrap gap-2 text-xs text-gray-500">
                  <span className="rounded-full bg-gray-100 px-2.5 py-1">
                    {item.version_number ? `Versión v${item.version_number}` : "Sin versión publicada"}
                  </span>
                  {item.last_score != null && (
                    <span className="rounded-full bg-green-50 px-2.5 py-1 text-green-700">
                      Último score: {item.last_score}%
                    </span>
                  )}
                  {item.training_title && (
                    <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-indigo-700">
                      {item.training_title}
                    </span>
                  )}
                </div>

                <div className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-indigo-600">
                  Ver detalle
                  <ArrowRight className="h-4 w-4" />
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
