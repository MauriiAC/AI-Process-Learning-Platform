import { Sparkles } from "lucide-react";

export default function AdminAiAuditsPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-6 pt-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Auditorías automáticas con IA</h1>
        <p className="mt-1 text-sm text-gray-500">
          Próximamente vas a poder revisar auditorías automáticas, hallazgos y recomendaciones generadas por IA.
        </p>
      </div>

      <section className="rounded-3xl border border-dashed border-indigo-200 bg-gradient-to-br from-indigo-50 via-white to-sky-50 px-8 py-14 text-center shadow-sm">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-100 text-indigo-600">
          <Sparkles className="h-8 w-8" />
        </div>
        <h2 className="mt-6 text-xl font-semibold text-gray-900">Funcionalidad en construcción</h2>
        <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-gray-600">
          Estamos trabajando para que el conocimiento de tu negocio se use proactivamente para detectar
          desviaciones en tus procesos, sin necesidad de un auditor experto presencial.
        </p>
      </section>
    </div>
  );
}
