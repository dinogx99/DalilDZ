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

export async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const message = body?.detail?.message || body?.detail || body?.error?.message || response.statusText;
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return response.json() as Promise<T>;
}
