"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { EvidenceTable } from "../../../components/EvidenceTable";
import { StatusBadge } from "../../../components/StatusBadge";
import type { CaseRecord, Check, DocumentRecord } from "../../../lib/api";
import { jsonFetch } from "../../../lib/api";

type TimelineEvent = {
  id: string;
  action: string;
  created_at: string;
  metadata: Record<string, unknown>;
};

export default function CasePage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [caseData, setCaseData] = useState<CaseRecord | null>(null);
  const [checks, setChecks] = useState<Check[]>([]);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function reload() {
    const [caseResult, checksResult, docsResult, timelineResult] = await Promise.all([
      jsonFetch<CaseRecord>(`/api/v1/cases/${id}`),
      jsonFetch<Check[]>(`/api/v1/cases/${id}/checks`),
      jsonFetch<DocumentRecord[]>(`/api/v1/cases/${id}/documents`),
      jsonFetch<TimelineEvent[]>(`/api/v1/cases/${id}/timeline`),
    ]);
    setCaseData(caseResult);
    setChecks(checksResult);
    setDocuments(docsResult);
    setTimeline(timelineResult);
  }

  useEffect(() => {
    reload().catch((error: Error) => setMessage(error.message));
  }, [id]);

  const summary = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const check of checks) counts[check.status] = (counts[check.status] || 0) + 1;
    return counts;
  }, [checks]);

  async function upload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = event.currentTarget.elements.namedItem("document") as HTMLInputElement;
    if (!input.files?.[0]) return;
    const form = new FormData();
    form.set("file", input.files[0]);
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(`/api/v1/cases/${id}/documents`, { method: "POST", body: form });
      if (!response.ok) throw new Error("Document upload failed");
      await reload();
      event.currentTarget.reset();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function analyze() {
    setBusy(true);
    setMessage("");
    try {
      await jsonFetch(`/api/v1/cases/${id}/analyze`, { method: "POST" });
      await reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Analysis failed");
    } finally {
      setBusy(false);
    }
  }

  if (!caseData) return <main className="shell"><p>{message || "Loading case…"}</p></main>;

  return (
    <main className="shell">
      <header className="topbar">
        <a href="/" className="brand">Dalil<span>DZ</span></a>
        <div className="top-actions">
          <a href="/api/v1/health" target="_blank">API health</a>
          <a href="https://github.com/dinogx99/DalilDZ" target="_blank">GitHub</a>
        </div>
      </header>

      <section className="case-heading">
        <div>
          <p className="eyebrow">VERIFICATION CASE</p>
          <h1>{caseData.name}</h1>
          <p className="muted mono">Case {caseData.id}</p>
        </div>
        <div className="case-actions">
          <button onClick={analyze} disabled={busy}>{busy ? "Processing…" : "Run analysis"}</button>
          <a className="button secondary" href={`/api/v1/cases/${id}/report.html`} target="_blank">Printable report</a>
          <a className="button secondary" href={`/api/v1/cases/${id}/report.csv`}>CSV export</a>
        </div>
      </section>

      {message && <div className="message">{message}</div>}

      <section className="grid-2">
        <article className="panel">
          <h2>Submitted identity</h2>
          <dl className="claim-list">
            {Object.entries(caseData.claims).map(([field, value]) => (
              <div key={field}><dt>{field}</dt><dd>{value}</dd></div>
            ))}
          </dl>
        </article>

        <article className="panel">
          <h2>Add evidence document</h2>
          <p className="muted">PDF, JPG, PNG or WebP. MIME is verified from file bytes, not from the extension.</p>
          <form onSubmit={upload} className="upload-form">
            <input type="file" name="document" accept=".pdf,.jpg,.jpeg,.png,.webp" required />
            <button disabled={busy}>Upload</button>
          </form>
        </article>
      </section>

      <section className="summary-grid">
        {Object.entries(summary).map(([status, count]) => (
          <article className="summary-card" key={status}>
            <StatusBadge value={status} />
            <strong>{count}</strong>
          </article>
        ))}
        {!Object.keys(summary).length && <article className="summary-card"><span>No analysis yet</span><strong>0</strong></article>}
      </section>

      <section className="panel wide">
        <div className="section-head">
          <div><p className="eyebrow">AUDITABLE OUTPUT</p><h2>Verification checks</h2></div>
          <span className="muted">{checks.length} findings</span>
        </div>
        <EvidenceTable checks={checks} />
      </section>

      <section className="grid-2">
        <article className="panel">
          <h2>Documents</h2>
          <div className="stack">
            {documents.map((doc) => (
              <div className="document-row" key={doc.id}>
                <div><strong>{doc.filename}</strong><p>{doc.document_type} · {doc.extraction_method}</p></div>
                <code>{doc.sha256.slice(0, 12)}…</code>
              </div>
            ))}
            {!documents.length && <p className="muted">No documents uploaded.</p>}
          </div>
        </article>

        <article className="panel">
          <h2>Timeline</h2>
          <div className="stack">
            {timeline.slice(0, 12).map((event) => (
              <div className="timeline-row" key={event.id}>
                <span>{event.action}</span>
                <time>{new Date(event.created_at).toLocaleString()}</time>
              </div>
            ))}
            {!timeline.length && <p className="muted">No audit events yet.</p>}
          </div>
        </article>
      </section>
    </main>
  );
}
