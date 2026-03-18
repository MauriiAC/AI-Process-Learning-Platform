export interface ComplianceItem {
  id: string;
  user_id: string;
  user_name: string;
  procedure_id: string;
  procedure_title: string;
  procedure_version_id: string | null;
  version_number: number | null;
  training_id: string | null;
  training_title: string | null;
  assignment_id: string | null;
  role_assignment_id: string | null;
  role_name: string | null;
  status: string;
  due_date: string | null;
  completed_at: string | null;
  last_score: number | null;
  evidence_json: Record<string, unknown> | null;
  updated_at: string;
}

export interface AssignmentItem {
  id: string;
  training_id: string;
  training_title?: string | null;
  user_id: string;
  user_name?: string | null;
  assignment_type: string;
  due_date?: string | null;
  status: string;
  score?: number | null;
  attempts: number;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface TrainingDetails {
  id: string;
  procedure_version_id: string;
  title: string;
  status: string;
  created_at: string;
  summary?: string | null;
  procedure_id?: string | null;
  procedure_code?: string | null;
  procedure_title?: string | null;
  version_number?: number | null;
  source_asset_type?: string | null;
  source_storage_key?: string | null;
  source_mime?: string | null;
  source_size?: number | null;
  structure?: {
    structure_json?: {
      title?: string;
      objectives?: string[];
      steps?: Array<{
        title: string;
        description: string;
        evidence?: { segment_range?: string; quote?: string };
      }>;
      critical_points?: Array<{
        text: string;
        why?: string;
        evidence?: { segment_range?: string; quote?: string };
      }>;
    };
  } | null;
}

export interface QuizQuestion {
  id: string;
  training_id: string;
  question_json: {
    question: string;
    type: string;
    options: string[];
    correct_answer: string | number;
    evidence?: {
      segment_range?: string;
      quote?: string;
    };
    verified?: boolean;
    position?: number;
  };
}

export interface IncidentItem {
  id: string;
  description: string;
  severity: string;
  role_id?: string | null;
  role_name?: string | null;
  location?: string | null;
  created_at: string;
}

export interface RoleOption {
  id: string;
  name: string;
}

export const complianceStatusMeta: Record<string, { label: string; className: string }> = {
  assigned: { label: "Asignado", className: "bg-blue-100 text-blue-800" },
  in_progress: { label: "En progreso", className: "bg-amber-100 text-amber-800" },
  completed: { label: "Completado", className: "bg-green-100 text-green-800" },
  overdue: { label: "Vencido", className: "bg-red-100 text-red-800" },
};

export const incidentSeverityMeta: Record<string, { label: string; className: string }> = {
  low: { label: "Baja", className: "bg-yellow-100 text-yellow-800" },
  medium: { label: "Media", className: "bg-orange-100 text-orange-800" },
  high: { label: "Alta", className: "bg-red-100 text-red-800" },
  critical: { label: "Crítica", className: "bg-red-200 text-red-900" },
};
