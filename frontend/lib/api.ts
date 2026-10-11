export type CaseRecord = {
  id: string;
  name: string;
  notes?: string | null;
  claims: Record<string, string>;
  state: string;
  created_at: string;
  updated_at: string;
};

export type Check = {
  id: string;
  job_id?: string | null;
  field: string;
  submitted_value?: string | null;
  evidence_value?: string | null;
  status: string;
  method: string;
  explanation: string;
  evidence_record_id?: string | null;
  checked_at: string;
  metadata: Record<string, unknown>;
};

export type DocumentRecord = {
  id: string;
  filename: string;
  mime: string;
  size_bytes: number;
  sha256: string;
  document_type: string;
  extraction_method: string;
  ocr_required: boolean;
  created_at: string;
};

export type AnalysisJob = {
  id: string;
  status: string;
  error_code?: string | null;
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
};

export type SourceInfo = {
  id: string;
  name: string;
  type: string;
  official: boolean;
  automation_mode: string;
  health: string;
  limitations: string;
  supported_fields: string[];
};

export type TimelineEvent = {
  id: string;
  action: string;
  created_at: string;
  metadata: Record<string, unknown>;
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
  ) {
    super(message);
  }
}

async function errorFrom(response: Response): Promise<ApiError> {
  const body = await response.json().catch(() => ({}));
  const detail = body?.detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    return new ApiError(detail.message || detail.code || response.statusText, response.status, detail.code);
  }
  if (Array.isArray(detail)) {
    // FastAPI validation errors: [{loc, msg, ...}]
    const message = detail.map((item: { loc?: unknown[]; msg?: string }) => `${item.loc?.slice(-1)[0] ?? ""}: ${item.msg}`).join("; ");
    return new ApiError(message, response.status, "VALIDATION_ERROR");
  }
  const message = typeof detail === "string" ? detail : body?.error?.message || response.statusText || "Request failed";
  return new ApiError(message, response.status, body?.error?.code);
}

export async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) throw await errorFrom(response);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function postJson<T>(url: string, body: unknown, method = "POST"): Promise<T> {
  return jsonFetch<T>(url, {
    method,
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function uploadFile<T>(url: string, file: File): Promise<T> {
  const form = new FormData();
  form.set("file", file);
  return jsonFetch<T>(url, { method: "POST", body: form });
}
