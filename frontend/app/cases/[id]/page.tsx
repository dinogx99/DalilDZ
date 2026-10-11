"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { EvidenceTable } from "../../../components/EvidenceTable";
import { useLanguage } from "../../../components/LanguageProvider";
import { StatusBadge } from "../../../components/StatusBadge";
import { TopBar } from "../../../components/TopBar";
import type { AnalysisJob, CaseRecord, Check, DocumentRecord, SourceInfo, TimelineEvent } from "../../../lib/api";
import { jsonFetch, postJson, uploadFile } from "../../../lib/api";

const CLAIM_FIELDS = [
  "legal_name",
  "commercial_name",
  "arabic_name",
  "legal_form",
  "rc",
  "nif",
  "nis",
  "ai",
  "wilaya",
  "address",
  "website",
  "email",
  "phone",
];

type Notice = { kind: "info" | "error"; text: string };

export default function CasePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { t } = useLanguage();
  const id = params.id;
  const [caseData, setCaseData] = useState<CaseRecord | null>(null);
  const [checks, setChecks] = useState<Check[]>([]);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [jobs, setJobs] = useState<AnalysisJob[]>([]);
  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [loadError, setLoadError] = useState("");

  const reload = useCallback(async () => {
    const [caseResult, checksResult, docsResult, timelineResult, jobsResult] = await Promise.all([
      jsonFetch<CaseRecord>(`/api/v1/cases/${id}`),
      jsonFetch<Check[]>(`/api/v1/cases/${id}/checks`),
      jsonFetch<DocumentRecord[]>(`/api/v1/cases/${id}/documents`),
      jsonFetch<TimelineEvent[]>(`/api/v1/cases/${id}/timeline`),
      jsonFetch<AnalysisJob[]>(`/api/v1/cases/${id}/jobs`),
    ]);
    setCaseData(caseResult);
    setChecks(checksResult);
    setDocuments(docsResult);
    setTimeline(timelineResult);
    setJobs(jobsResult);
  }, [id]);

  useEffect(() => {
    reload().catch((error: Error) => setLoadError(error.message));
    jsonFetch<SourceInfo[]>("/api/v1/sources").then(setSources).catch(() => undefined);
  }, [reload]);

  const summary = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const check of checks) counts[check.status] = (counts[check.status] || 0) + 1;
    return counts;
  }, [checks]);

  async function run(action: () => Promise<string | void>) {
    setBusy(true);
    setNotice(null);
    try {
      const text = await action();
      await reload();
      if (text) setNotice({ kind: "info", text });
    } catch (error) {
      setNotice({ kind: "error", text: error instanceof Error ? error.message : String(error) });
    } finally {
      setBusy(false);
    }
  }

  function upload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // Capture the form now: React clears event.currentTarget once the handler yields.
    const form = event.currentTarget;
    const file = (form.elements.namedItem("document") as HTMLInputElement).files?.[0];
    if (!file) return;
    run(async () => {
      const result = await uploadFile<{ claims: unknown[]; ocr_required: boolean }>(`/api/v1/cases/${id}/documents`, file);
      form.reset();
      const ocr = result.ocr_required ? ` · ${t.ocrRequired}` : "";
      return `${t.uploaded}: ${result.claims.length} ${t.claimsExtracted}${ocr}`;
    });
  }

  function addClaim(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    run(async () => {
      await postJson(`/api/v1/cases/${id}/claims`, {
        field: String(data.get("field")),
        value: String(data.get("value") || "").trim(),
      });
      form.reset();
    });
  }

  function addManualEvidence(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const optional = (key: string) => String(data.get(key) || "").trim() || null;
    run(async () => {
      const result = await postJson<{ status: string; explanation: string }>(`/api/v1/cases/${id}/manual-evidence`, {
        field: String(data.get("field")),
        value: String(data.get("value") || "").trim(),
        source_name: String(data.get("source_name") || "").trim(),
        source_url: optional("source_url"),
        note: optional("note"),
      });
      form.reset();
      return `${result.status.replaceAll("_", " ")} — ${result.explanation}`;
    });
  }

  function analyze() {
    run(async () => {
      await jsonFetch(`/api/v1/cases/${id}/analyze`, { method: "POST" });
    });
  }

  function queue() {
    run(async () => {
      await jsonFetch(`/api/v1/cases/${id}/analyze/background`, { method: "POST" });
      return t.queued;
    });
  }

  async function deleteCase() {
    if (!window.confirm(t.confirmDelete)) return;
    setBusy(true);
    try {
      await jsonFetch(`/api/v1/cases/${id}`, { method: "DELETE" });
      router.push("/");
    } catch (error) {
      setNotice({ kind: "error", text: error instanceof Error ? error.message : String(error) });
      setBusy(false);
    }
  }

  if (!caseData) {
    return (
      <main className="shell">
        <TopBar />
        <section className="case-heading">
          <p className={loadError ? "error" : "muted"}>{loadError || t.loading}</p>
        </section>
      </main>
    );
  }

  const hasReport = jobs.some((job) => job.status === "COMPLETED");

  return (
    <main className="shell">
      <TopBar>
        <a href="/" className="muted">{t.back}</a>
      </TopBar>

      <section className="case-heading">
        <div>
          <p className="eyebrow">{t.verificationCase}</p>
          <h1 dir="auto">{caseData.name}</h1>
          <p className="muted small">{t.caseLabel} <span className="mono">{caseData.id}</span></p>
        </div>
        <div className="case-actions">
          <button onClick={analyze} disabled={busy}>{busy ? t.processing : t.runAnalysis}</button>
          <button className="secondary" onClick={queue} disabled={busy}>{t.queueAnalysis}</button>
          {hasReport && (
            <>
              <a className="button secondary" href={`/api/v1/cases/${id}/report.html`} target="_blank" rel="noreferrer">{t.printable}</a>
              <a className="button secondary" href={`/api/v1/cases/${id}/report.csv`}>{t.csvExport}</a>
              <a className="button secondary" href={`/api/v1/cases/${id}/report`} target="_blank" rel="noreferrer">{t.jsonExport}</a>
            </>
          )}
        </div>
      </section>

      {notice && <div className={`notice-wrap ${notice.kind === "error" ? "error" : "message"}`} role="status">{notice.text}</div>}

      <section className="summary-grid">
        {Object.entries(summary).map(([status, count]) => (
          <article className="summary-card" key={status}>
            <StatusBadge value={status} />
            <strong>{count}</strong>
          </article>
        ))}
        {!Object.keys(summary).length && (
          <article className="summary-card"><span className="muted">{t.noAnalysis}</span><strong>0</strong></article>
        )}
      </section>

      <section className="panel wide">
        <div className="section-head">
          <div><p className="eyebrow">{t.auditable}</p><h2>{t.checksTitle}</h2></div>
          <span className="muted">{checks.length} {t.findings}</span>
        </div>
        <EvidenceTable checks={checks} />
      </section>

      <section className="grid-2">
        <article className="panel">
          <h2>{t.submittedIdentity}</h2>
          <dl className="claim-list">
            {Object.entries(caseData.claims).map(([field, value]) => (
              <div key={field}><dt>{field}</dt><dd dir="auto">{value}</dd></div>
            ))}
          </dl>
          <form onSubmit={addClaim} className="inline-form">
            <p className="form-title">{t.addClaim}</p>
            <div className="form-grid">
              <label>
                {t.field}
                <select name="field" defaultValue="nif">
                  {CLAIM_FIELDS.map((field) => <option key={field} value={field}>{field}</option>)}
                </select>
              </label>
              <label>{t.value}<input name="value" required maxLength={2000} /></label>
            </div>
            <button className="secondary" disabled={busy}>{t.save}</button>
          </form>
        </article>

        <article className="panel">
          <h2>{t.addDocument}</h2>
          <p className="muted small">{t.documentHelp}</p>
          <form onSubmit={upload} className="upload-form">
            <input type="file" name="document" accept=".pdf,.jpg,.jpeg,.png,.webp" required />
            <button disabled={busy}>{t.upload}</button>
          </form>

          <h2 className="spaced">{t.manualTitle}</h2>
          <p className="muted small">{t.manualHelp}</p>
          <form onSubmit={addManualEvidence} className="inline-form">
            <div className="form-grid">
              <label>
                {t.field}
                <select name="field" defaultValue="rc">
                  {CLAIM_FIELDS.map((field) => <option key={field} value={field}>{field}</option>)}
                </select>
              </label>
              <label>{t.value}<input name="value" required maxLength={2000} /></label>
            </div>
            <div className="form-grid">
              <label>{t.sourceName}<input name="source_name" required maxLength={200} placeholder="CNRC / Sidjilcom" /></label>
              <label>{t.sourceUrl}<input name="source_url" type="url" maxLength={2000} placeholder="https://" /></label>
            </div>
            <label>{t.note}<input name="note" maxLength={4000} /></label>
            <button disabled={busy}>{t.recordEvidence}</button>
          </form>
        </article>
      </section>

      <section className="grid-2">
        <article className="panel">
          <h2>{t.documents}</h2>
          <div className="stack">
            {documents.map((doc) => (
              <div className="document-row" key={doc.id}>
                <div>
                  <strong>{doc.filename}</strong>
                  <p>{doc.document_type} · {doc.extraction_method}{doc.ocr_required ? ` · ${t.ocrRequired}` : ""}</p>
                </div>
                <code title={doc.sha256}>{doc.sha256.slice(0, 12)}…</code>
              </div>
            ))}
            {!documents.length && <p className="muted">{t.noDocuments}</p>}
          </div>
        </article>

        <article className="panel">
          <h2>{t.analyses}</h2>
          <div className="stack">
            {jobs.slice(0, 8).map((job) => (
              <div className="timeline-row" key={job.id}>
                <span>
                  <StatusBadge value={job.status} /> <code className="small">{job.id.slice(0, 8)}</code>
                  {job.error_message && <span className="error-text"> {job.error_message}</span>}
                </span>
                <time>{new Date(job.created_at).toLocaleString()}</time>
              </div>
            ))}
            {!jobs.length && <p className="muted">{t.noAnalyses}</p>}
          </div>
        </article>
      </section>

      <section className="grid-2">
        <article className="panel">
          <h2>{t.sources}</h2>
          <div className="stack">
            {sources.map((source) => (
              <div className="document-row" key={source.id}>
                <div>
                  <strong>{source.name}</strong>
                  <p>{source.limitations}</p>
                </div>
                <StatusBadge value={source.health} />
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <h2>{t.timeline}</h2>
          <div className="stack">
            {timeline.slice(0, 12).map((event) => (
              <div className="timeline-row" key={event.id}>
                <span className="mono small">{event.action}</span>
                <time>{new Date(event.created_at).toLocaleString()}</time>
              </div>
            ))}
            {!timeline.length && <p className="muted">{t.noTimeline}</p>}
          </div>
        </article>
      </section>

      <section className="danger-zone">
        <p className="muted small">{t.disclaimer}</p>
        <button className="danger" onClick={deleteCase} disabled={busy}>{t.deleteCase}</button>
      </section>
    </main>
  );
}
